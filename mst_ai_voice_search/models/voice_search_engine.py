import difflib
import io
import json
import logging
import re
from collections import defaultdict
from datetime import timedelta

import pytz
import requests
from dateutil import parser as date_parser
from lxml import etree

from markupsafe import Markup, escape

import contextvars

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.orm.commands import Command
from odoo.orm.domains import Domain

from odoo.tools.translate import get_translation

from . import voice_search_i18n
from . import voice_search_parser as parser

# Language of the replies of the current request (set from the voice panel's language)
_REPLY_LANG = contextvars.ContextVar("mst_ai_voice_search_reply_lang", default="en_US")
LANGUAGE_NAMES = {"en": "English", "ta": "Tamil (தமிழ்)"}


def _(source, *args, **kwargs):
    """Reply text in the language selected in the voice panel.

    Tamil comes from the module's built-in translations, so it works even when Tamil
    is not installed in Odoo; other languages use Odoo's translations; English as is.
    """
    params = args or kwargs
    lang = _REPLY_LANG.get() or "en_US"
    short = lang.replace("-", "_").split("_")[0]
    text = voice_search_i18n.TRANSLATIONS.get(short, {}).get(source)
    if text is None and lang != "en_US" and short != "en":
        try:
            return get_translation("mst_ai_voice_search", lang, source, params)
        except Exception:  # noqa: BLE001 - a missing translation must never break a reply
            text = None
    text = source if text is None else text
    return text % params if params else text

_logger = logging.getLogger(__name__)

PARAM = "mst_ai_voice_search.%s"
MAX_QUERY_LENGTH = 500
AI_TIMEOUT = 20
# Fields shown under each result, in order of preference (only if they exist and are readable)
DETAIL_FIELDS = [
    "partner_id", "amount_total", "expected_revenue", "list_price", "state", "stage_id",
    "date_order", "invoice_date", "date_deadline", "scheduled_date", "email", "phone",
    "user_id", "invoice_user_id", "project_id",
]
ORDER_RE = re.compile(r"^\s*([a-z_][a-z0-9_]*)(?:\s+(asc|desc))?\s*$", re.I)

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ISO_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$")
LIST_ACTIONS = ("filter", "group", "export", "import")
VIEW_TYPES = ("list", "form", "kanban", "calendar", "pivot", "graph", "activity", "map", "gantt", "cohort", "hierarchy")
DEFAULT_VIEW_TYPES = ("list", "form", "kanban", "pivot", "graph")  # Odoo can generate these for any model
# Main date field of a model when the user says only "this month", "last week"...
DEFAULT_DATE_FIELDS = ("date_order", "invoice_date", "date", "scheduled_date", "date_deadline",
                       "date_planned", "date_start", "start", "create_date")
DATE_FIELD_ALIASES = {
    "created": ["create_date"], "creation date": ["create_date"], "updated": ["write_date"],
    "modified": ["write_date"], "order date": ["date_order"], "invoice date": ["invoice_date"],
    "due date": ["invoice_date_due", "date_deadline"], "delivery date": ["commitment_date", "scheduled_date", "date_deadline"],
    "deadline": ["date_deadline"], "expiry date": ["validity_date"], "expiration date": ["validity_date"],
    "scheduled date": ["scheduled_date"], "confirmation date": ["date_approve", "date_order"],
    "payment date": ["date"], "accounting date": ["date"], "date": list(DEFAULT_DATE_FIELDS),
}
SEARCH_TYPES = ("char", "text", "html", "selection", "many2one", "date", "datetime", "boolean",
                "integer", "float", "monetary")
GROUP_TYPES = ("many2one", "selection", "char", "date", "datetime", "boolean", "integer")
EXPORT_LIMIT = 10000
VOICE_LANGUAGES = {
    "auto": [],
    "en-IN": [("en-IN", "English")],
    "en-US": [("en-US", "English")],
    "ta-IN": [("ta-IN", "தமிழ்")],
    "en-IN,ta-IN": [("en-IN", "English"), ("ta-IN", "தமிழ்")],
}
WRITE_ACTIONS = ("create", "write", "delete", "archive", "unarchive", "duplicate")
ACTION_ACCESS = {"create": "create", "write": "write", "delete": "unlink",
                 "archive": "write", "unarchive": "write", "duplicate": "create"}
MODE_ALLOWS = {
    "read": set(),
    "write": {"create", "write", "archive", "unarchive", "duplicate", "message"},
    "all": {"create", "write", "delete", "archive", "unarchive", "duplicate", "message"},
}
WRITABLE_TYPES = ("char", "text", "html", "integer", "float", "monetary", "boolean",
                  "date", "datetime", "selection", "many2one")
TRUE_WORDS = {"yes", "true", "on", "active", "enabled", "1", "y"}
FALSE_WORDS = {"no", "false", "off", "inactive", "disabled", "0", "n"}
# Spoken field names -> technical names, tried in order (first writable one wins)
FIELD_ALIASES = {
    "phone": ["phone", "mobile"], "phone number": ["phone", "mobile"], "mobile": ["mobile", "phone"],
    "email": ["email"], "mail": ["email"], "website": ["website"],
    "price": ["list_price", "price_unit"], "sales price": ["list_price"], "sale price": ["list_price"],
    "cost": ["standard_price"], "customer": ["partner_id"], "vendor": ["partner_id"],
    "partner": ["partner_id"], "contact": ["partner_id"], "salesperson": ["user_id"],
    "responsible": ["user_id"], "user": ["user_id"], "reference": ["client_order_ref", "ref", "default_code"],
    "internal reference": ["default_code"], "date": ["date_order", "date", "invoice_date"],
    "deadline": ["date_deadline", "validity_date"], "expiration": ["validity_date"],
    "expected revenue": ["expected_revenue"], "revenue": ["expected_revenue"],
    "note": ["note", "description", "comment"], "notes": ["note", "description", "comment"],
    "description": ["description", "description_sale", "note"], "street": ["street"],
    "city": ["city"], "zip": ["zip"], "country": ["country_id"], "barcode": ["barcode"],
    "job": ["function"], "job position": ["function"], "tax id": ["vat"], "gst": ["vat"], "vat": ["vat"],
    "state": ["state"], "status": ["state"], "stage": ["stage_id"], "category": ["categ_id", "category_id"],
    "company": ["company_id"], "tag": ["tag_ids", "category_id"], "type": ["type", "move_type"],
    # one-to-many / many-to-many relations ("how many members in k channel")
    "members": ["channel_member_ids", "member_ids", "channel_partner_ids", "partner_ids"],
    "member": ["channel_member_ids", "member_ids", "channel_partner_ids"],
    "participants": ["channel_member_ids", "partner_ids", "attendee_ids"],
    "contacts": ["child_ids"], "addresses": ["child_ids"], "children": ["child_ids"],
    "orders": ["sale_order_ids", "order_ids", "purchase_order_ids"], "sales orders": ["sale_order_ids"],
    "sale orders": ["sale_order_ids"], "quotations": ["sale_order_ids"], "invoices": ["invoice_ids"],
    "lines": ["order_line", "line_ids", "invoice_line_ids", "move_ids"], "order lines": ["order_line"],
    "tags": ["category_id", "tag_ids"], "followers": ["message_partner_ids"], "users": ["user_ids"],
    "products": ["product_ids", "product_variant_ids"], "variants": ["product_variant_ids"],
    "employees": ["employee_ids"], "messages": ["message_ids"], "sub channels": ["sub_channel_ids"],
    "attachments": ["attachment_ids"], "tasks": ["task_ids"], "bank accounts": ["bank_ids"],
}
X2MANY_SKIP = ("message_follower_ids", "website_message_ids", "activity_ids", "rating_ids")
CONDITION_JOINERS_RE = re.compile(r"^\s*(?:is|are|=|==|equals?|equal\s+to|:|as|of)\s+", re.I)


class VoiceSearchEngine(models.AbstractModel):
    _name = "mst.voice.search.engine"
    _description = "AI Voice Search Engine"

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------
    @api.model
    def _get_setting(self, key, default=False):
        return self.env["ir.config_parameter"].sudo().get_param(PARAM % key, default)

    @api.model
    def _max_results(self):
        try:
            value = int(self._get_setting("max_results", 10))
        except (TypeError, ValueError):
            value = 10
        return max(1, min(value, 50))

    @api.model
    def _reply_lang(self, panel_lang=None):
        """Reply language: the voice panel's language (default), English, or the user's Odoo language."""
        mode = self._get_setting("reply_language", "panel")
        if mode == "user":
            return self.env.user.lang or "en_US"
        if mode == "en":
            return "en_US"
        code = (panel_lang or "").replace("-", "_")
        return "ta_IN" if code.startswith("ta") else "en_US"

    @api.model
    def _with_reply_lang(self, panel_lang=None):
        """Set the reply language for this request; Odoo labels follow it when that language is installed."""
        lang = self._reply_lang(panel_lang)
        _REPLY_LANG.set(lang)
        installed = lang == "en_US" or bool(self.env["res.lang"]._get_data(code=lang))
        return self.with_context(lang=lang if installed else "en_US")

    @api.model
    def _reply_language_name(self):
        lang = _REPLY_LANG.get() or "en_US"
        return LANGUAGE_NAMES.get(lang.split("_")[0], lang)

    @api.model
    def _voice_languages(self):
        langs = VOICE_LANGUAGES.get(self._get_setting("voice_languages", "en-IN,ta-IN"), [])
        if not langs:
            code = (self.env.user.lang or "en_US").replace("_", "-")
            langs = [(code, code)]
        return [{"code": code, "label": label} for code, label in langs]

    @api.model
    def _action_mode(self):
        mode = self._get_setting("action_mode", "all")
        return mode if mode in MODE_ALLOWS else "all"

    @api.model
    def get_client_config(self):
        """Small config for the browser (no secrets)."""
        provider = self._get_setting("ai_provider", "none")
        return {
            "speak_replies": self._get_setting("speak_replies", "False") == "True",
            "ai_enabled": provider in ("openai", "gemini") and bool(self._get_setting("ai_api_key")),
            "action_mode": self._action_mode(),
            "languages": self._voice_languages(),
            "reply_mode": self._get_setting("reply_language", "panel"),
            "reply_lang": self._reply_lang().replace("_", "-"),
            "silence_ms": max(1, min(int(self._get_setting("silence_seconds", 3) or 3), 10)) * 1000,
        }

    # ------------------------------------------------------------------
    # Catalog: what this user can see and open
    # ------------------------------------------------------------------
    @api.model
    def _get_catalog(self):
        """Menus and models the current user can open.

        Mirrors ir.ui.menu.load_menus() (what the web client loads): same
        blacklist, same visibility, and menus whose parent menu is hidden are
        dropped, so every menu returned here exists in the browser too.
        """
        Menu = self.env["ir.ui.menu"]
        menus = Menu.search_fetch(
            [("id", "not in", Menu._load_menus_blacklist())], ["name", "parent_id", "action"]
        )._filter_visible_menus()
        children = defaultdict(list)
        for menu in menus:
            children[menu.parent_id.id].append(menu)
        app_of = {}

        def _walk(app_id, menu):
            app_of[menu.id] = app_id
            for child in children[menu.id]:
                _walk(app_id, child)

        for root in children[False]:
            _walk(root.id, root)

        access = self.env["ir.model.access"]
        catalog = {"uid": self.env.uid, "menus": [], "models": {}}
        for menu in menus.filtered(lambda m: m.id in app_of):
            action = menu.action
            res_model = False
            if action and action._name == "ir.actions.act_window":
                res_model = action.sudo().res_model
            view_modes = []
            if res_model:
                view_modes = [v.strip() for v in (action.sudo().view_mode or "").split(",") if v.strip()]
            catalog["menus"].append({
                "id": menu.id,
                "path": menu.complete_name or menu.name,
                "has_action": bool(action),
                "action_id": action.id if action else False,
                "app_id": app_of[menu.id],
                "parent_id": menu.parent_id.id,
                "model": res_model,
                "view_modes": view_modes,
            })
            if not res_model or res_model not in self.env:
                continue
            if not access.check(res_model, "read", raise_exception=False):
                continue
            info = catalog["models"].get(res_model)
            if not info:
                info = catalog["models"][res_model] = self._model_info(res_model)
            if menu.name not in info["menu_names"]:
                info["menu_names"].append(menu.name)
        # An app without its own action (e.g. "Contacts" in some databases) opens its first
        # screen when clicked in Odoo: give it that action, like the web client does.
        by_parent = defaultdict(list)
        for menu in catalog["menus"]:
            by_parent[menu["parent_id"]].append(menu)

        def _first_screen(menu):
            for child in by_parent[menu["id"]]:
                if child["has_action"]:
                    return child
                found = _first_screen(child)
                if found:
                    return found
            return None

        for app in by_parent[False]:
            if not app["has_action"]:
                first = _first_screen(app)
                if first:
                    app.update(has_action=True, action_id=first["action_id"], model=first["model"],
                               view_modes=first["view_modes"])
        return catalog

    @api.model
    def _model_info(self, model_name):
        Model = self.env[model_name]
        label = self.env["ir.model"]._get(model_name).name or model_name
        states = []
        state_field = Model._fields.get("state")
        if state_field and state_field.type == "selection":
            try:
                states = [(str(v), str(l)) for v, l in state_field._description_selection(self.env)]
            except Exception:  # selection callables of other modules must never break search
                states = []
        user_field = next(
            (f for f in ("user_id", "invoice_user_id") if f in Model._fields
             and Model._fields[f].type == "many2one" and Model._fields[f].comodel_name == "res.users"),
            None,
        )
        return {"label": label, "menu_names": [], "states": states, "user_field": user_field}

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    @api.model
    def process_query(self, text, current_app_id=None, lang=None):
        self = self._with_reply_lang(lang)  # noqa: PLW0642 - replies/labels in the reply language
        text = (text or "").strip()[:MAX_QUERY_LENGTH]
        if not text:
            return {"type": "error", "message": _("I didn't catch anything. Try again or type your request.")}

        catalog = self._get_catalog()
        intent, source = None, "keywords"
        if self.get_client_config()["ai_enabled"]:
            try:
                intent = self._clean_intent(self._ai_parse(text, catalog, current_app_id), catalog)
                source = "ai" if intent else source
            except Exception as error:  # network, quota, invalid JSON... fall back silently
                _logger.warning("AI voice search failed, using keyword matching: %s", error)
                intent = None
        if not intent:
            intent = self._clean_intent(
                parser.keyword_parse(text, catalog, self._max_results(), current_app_id), catalog
            )

        if intent and intent["action"] == "related":
            result = self._related(intent, catalog)
        elif intent and intent["action"] == "message":
            result = self._prepare_message(intent)
        elif intent and intent["action"] in LIST_ACTIONS:
            result = self._list_action(intent, catalog)
        elif intent and intent["action"] == "create" and not intent.get("error"):
            result = self._create_form(intent, catalog)
        elif intent and intent["action"] in WRITE_ACTIONS:
            result = self._prepare_operation(intent, catalog)
        else:
            result = self._execute(intent, catalog)
        result.update({"query": text, "source": source if intent else "keywords"})
        return result

    # ------------------------------------------------------------------
    # Validation: never trust the AI (or the parser) blindly
    # ------------------------------------------------------------------
    @api.model
    def _clean_intent(self, intent, catalog):
        if not isinstance(intent, dict):
            return None
        action = intent.get("action")
        view_type = intent.get("view_type") if intent.get("view_type") in VIEW_TYPES else None
        if action == "navigate":
            menu_ids = {m["id"] for m in catalog["menus"]}
            try:
                menu_id = int(intent.get("menu_id") or 0)
            except (TypeError, ValueError):
                menu_id = 0
            record_model = intent.get("record_model") if intent.get("record_model") in catalog["models"] else None
            record = intent.get("record") if isinstance(intent.get("record"), str) and record_model else None
            if menu_id not in menu_ids and not record:
                return None
            return {"action": "navigate", "menu_id": menu_id if menu_id in menu_ids else False,
                    "reply": intent.get("reply"), "view_type": view_type,
                    "record_model": record_model, "record": record}
        if action in ("search", "count"):
            model = intent.get("model")
            if model not in catalog["models"]:
                return None
            domain = intent.get("domain") or []
            if not isinstance(domain, list):
                return None
            try:
                Domain(domain).validate(self.env[model])
            except Exception:
                return None
            try:
                limit = int(intent.get("limit") or self._max_results())
            except (TypeError, ValueError):
                limit = self._max_results()
            return {
                "action": action,
                "model": model,
                "domain": domain,
                "conditions": [c for c in (intent.get("conditions") or []) if isinstance(c, str)][:4],
                "limit": max(1, min(limit, self._max_results())),
                "order": self._clean_order(model, intent.get("order")),
                "reply": intent.get("reply") if isinstance(intent.get("reply"), str) else None,
            }
        if action == "related":
            if intent.get("model") not in catalog["models"] or not isinstance(intent.get("record"), str) \
                    or not isinstance(intent.get("relation"), str) or intent.get("mode") not in ("count", "list"):
                return None
            fallback = intent.get("fallback")
            return {"action": "related", "mode": intent["mode"], "model": intent["model"],
                    "record": intent["record"].strip(), "relation": intent["relation"].strip(),
                    "fallback": self._clean_intent(fallback, catalog) if isinstance(fallback, dict) else None}
        if action == "message":
            if intent.get("error"):
                return {"action": "message", "error": intent["error"]}
            recipient, body = intent.get("recipient"), intent.get("body")
            if not isinstance(recipient, str) or not isinstance(body, str) or not body.strip():
                return None
            return {"action": "message", "recipient": recipient.strip(), "body": body.strip()[:2000]}
        if action in LIST_ACTIONS:
            if intent.get("error"):
                return {"action": action, "error": intent["error"]}
            if intent.get("model") not in catalog["models"]:
                return None
            domain = intent.get("domain") or []
            if not isinstance(domain, list):
                return None
            try:
                Domain(domain).validate(self.env[intent["model"]])
            except Exception:
                return None
            conditions = intent.get("conditions") or []
            return {
                "action": action,
                "model": intent["model"],
                "domain": domain,
                "conditions": [c for c in conditions if isinstance(c, str)][:6],
                "group_field": intent.get("group_field") if isinstance(intent.get("group_field"), str) else None,
                "view_type": view_type,
            }
        if action in WRITE_ACTIONS:
            # Detailed checks (record, fields, values, rights) happen in _prepare_operation
            if intent.get("error"):
                return {"action": action, "error": intent["error"]}
            if intent.get("model") not in catalog["models"]:
                return None
            return dict(intent)
        if action == "unknown":
            return {"action": "unknown", "reply": intent.get("reply") if isinstance(intent.get("reply"), str) else None}
        return None

    @api.model
    def _menu_choices(self, folder, catalog):
        """A menu without a screen (e.g. Discuss / Configuration): list the screens under it."""
        children = defaultdict(list)
        for menu in catalog["menus"]:
            children[menu["parent_id"]].append(menu)
        found, todo = [], list(children[folder["id"]])
        while todo and len(found) < 15:
            menu = todo.pop(0)
            if menu["has_action"]:
                found.append(menu)
            todo.extend(children[menu["id"]])
        folder_path = folder["path"].replace("/", " / ")
        if not found:
            return {"type": "answer", "message": _("%s has no screens you can open.", folder_path)}
        prefix = folder["path"] + "/"
        return {
            "type": "menu_choices",
            "menu_path": folder_path,
            "message": _("%s has these screens. Which one?", folder_path),
            "choices": [{
                "menu_id": m["id"],
                "action_id": m["action_id"],
                "name": (m["path"][len(prefix):] if m["path"].startswith(prefix) else m["path"]).replace("/", " / "),
            } for m in found],
        }

    @api.model
    def _view_available(self, model, view_type):
        if view_type in DEFAULT_VIEW_TYPES:
            return True
        return bool(self.env["ir.ui.view"].sudo().search_count([("model", "=", model), ("type", "=", view_type)], limit=1))

    @api.model
    def _navigate_view(self, menu, view_type, reply=None):
        """Open a menu in a given view type (kanban, list, pivot...)."""
        path = menu["path"].replace("/", " / ")
        if view_type in menu["view_modes"]:
            return {"type": "navigate", "menu_id": menu["id"], "action_id": menu["action_id"], "menu_path": path,
                    "view_type": view_type, "message": reply or _("Opening %(menu)s in %(view)s view.", menu=path, view=view_type)}
        model = menu.get("model")
        if model and self._view_available(model, view_type):
            views = [[False, view_type]] + [[False, v] for v in ("list", "form") if v != view_type]
            return {"type": "action", "action": {
                "type": "ir.actions.act_window", "res_model": model, "name": menu["path"].split("/")[-1],
                "views": views, "target": "current"},
                "message": _("%(menu)s doesn't have a %(view)s view on its screen, so I opened its records in %(view)s view.",
                             menu=path, view=view_type)}
        available = ", ".join(menu["view_modes"]) or _("none")
        return {"type": "answer", "message": _("%(menu)s has no %(view)s view. Available views: %(available)s.",
                                               menu=path, view=view_type, available=available)}

    @api.model
    def _expand_name_search(self, model, domain):
        """A spoken name also matches the record's customer / partner: "sales orders of Deco
        Addict" must find orders whose customer is Deco Addict, not only orders named so."""
        Model = self.env[model]
        partner = Model._fields.get("partner_id")
        if not partner or partner.type != "many2one" or "partner_id" not in Model.check_field_access_rights("read", None):
            return domain
        out = []
        for leaf in domain:
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and leaf[0] == "display_name" and leaf[1] == "ilike":
                out += ["|", list(leaf), ["partner_id", "ilike", leaf[2]]]
            else:
                out.append(leaf)
        return out

    @api.model
    def _clean_order(self, model, order):
        if not order or not isinstance(order, str):
            return None
        match = ORDER_RE.match(order)
        if not match:
            return None
        field = self.env[model]._fields.get(match.group(1))
        if not field or not field.store:
            return None
        return "%s %s" % (field.name, (match.group(2) or "asc").lower())

    # ------------------------------------------------------------------
    # Execution (read-only, as the current user)
    # ------------------------------------------------------------------
    @api.model
    def _execute(self, intent, catalog):
        if not intent or intent["action"] == "unknown":
            return {
                "type": "answer",
                "message": (intent or {}).get("reply") or _(
                    "I couldn't match that to a menu or records. Try \"open invoices\", "
                    "\"show customers named Azure\" or \"how many draft quotations\"."
                ),
            }

        if intent["action"] == "navigate":
            if intent.get("record"):
                opened = self._open_record(intent["record_model"], intent["record"], catalog)
                if opened or not intent.get("menu_id"):
                    return opened or {"type": "answer", "message": _(
                        "No %(label)s named “%(name)s” was found.",
                        label=catalog["models"][intent["record_model"]]["label"], name=intent["record"])}
            menu = next(m for m in catalog["menus"] if m["id"] == intent["menu_id"])
            if not menu["has_action"]:
                return self._menu_choices(menu, catalog)
            if intent.get("view_type"):
                return self._navigate_view(menu, intent["view_type"], intent.get("reply"))
            return {
                "type": "navigate",
                "menu_id": menu["id"],
                "action_id": menu["action_id"],
                "menu_path": menu["path"].replace("/", " / "),
                "message": intent.get("reply") or _("Opening %s", menu["path"].replace("/", " / ")),
            }

        model = intent["model"]
        Model = self.env[model]
        label = catalog["models"][model]["label"]
        intent = dict(intent, domain=self._expand_name_search(model, list(intent["domain"])))
        try:
            for condition in intent.get("conditions") or []:
                leaves, _text = self._condition_domain(model, condition)
                intent["domain"].extend(leaves)
        except ValueError as error:
            return {"type": "error", "message": str(error)}
        try:
            total = Model.search_count(intent["domain"])
            records = Model.browse()
            if intent["action"] == "search" and total:
                records = Model.search(intent["domain"], limit=intent["limit"], order=intent["order"])
        except AccessError:
            return {"type": "error", "message": _("You don't have access to these %s records.", label)}
        except (UserError, ValueError) as error:
            _logger.info("Voice search query rejected: %s", error)
            return {"type": "error", "message": _("I couldn't run that search. Try rephrasing it.")}

        list_action = {
            "type": "ir.actions.act_window",
            "name": label,
            "res_model": model,
            "domain": intent["domain"],
            "views": [[False, "list"], [False, "form"]],
            "target": "current",
        }
        if intent["action"] == "count":
            return {
                "type": "count",
                "model": model,
                "count": total,
                "message": intent.get("reply") or _("%(label)s: %(count)s found.", label=label, count=total),
                "list_action": list_action if total else False,
            }

        rows = self._format_records(records)
        if not total:
            message = _("No %s records match that request.", label)
        elif total > len(rows):
            message = _("%(label)s: %(total)s found, showing %(shown)s.", label=label, total=total, shown=len(rows))
        else:
            message = _("%(label)s: %(total)s found.", label=label, total=total)
        return {
            "type": "records",
            "model": model,
            "count": total,
            "records": rows,
            "message": intent.get("reply") or message,
            "list_action": list_action if total else False,
        }

    @api.model
    def _format_records(self, records):
        if not records:
            return []
        Model = records.browse()
        candidates = [f for f in DETAIL_FIELDS if f in Model._fields]
        readable = set(Model.check_field_access_rights("read", None))
        detail_fields = [f for f in candidates if f in readable][:3]
        values = records.read(detail_fields) if detail_fields else [{"id": r.id} for r in records]
        by_id = {v["id"]: v for v in values}
        rows = []
        for record in records:
            details = []
            for name in detail_fields:
                text = self._format_value(Model._fields[name], by_id[record.id].get(name), record)
                if text:
                    details.append({"label": Model._fields[name]._description_string(self.env), "value": text})
            rows.append({"id": record.id, "name": record.display_name, "details": details})
        return rows

    @api.model
    def _format_value(self, field, value, record):
        if value in (False, None, ""):
            return ""
        if field.type == "many2one":
            return value[1] if isinstance(value, (list, tuple)) else str(value)
        if field.type == "selection":
            selection = dict(field._description_selection(self.env))
            return str(selection.get(value, value))
        if field.type == "monetary":
            currency_field = field.get_currency_field(record) if hasattr(field, "get_currency_field") else None
            currency = record[currency_field] if currency_field and currency_field in record._fields else False
            return self._format_amount(value, currency)
        if field.type == "float":
            return "%.2f" % value
        if field.type == "date":
            return fields.Date.to_string(value)
        if field.type == "datetime":
            return fields.Datetime.to_string(fields.Datetime.context_timestamp(record, value))[:16]
        return str(value)

    @api.model
    def _format_amount(self, amount, currency):
        if not currency:
            return "%.2f" % amount
        formatted = "%.*f" % (currency.decimal_places, amount)
        return "%s %s" % (currency.symbol, formatted) if currency.position == "before" else "%s %s" % (formatted, currency.symbol)

    # ------------------------------------------------------------------
    # AI parsing (OpenAI / Gemini) -> intent JSON
    # ------------------------------------------------------------------
    @api.model
    def _ai_prompt(self, text, catalog, current_app_id=None):
        # Field details only for the few models most likely meant (keeps the prompt small)
        likely = []
        guess = parser.match_model(text, catalog)
        if guess:
            likely.append(guess)
        words = set(parser.normalize(text).split())
        for model, info in catalog["models"].items():
            names = parser.normalize(" ".join([info["label"]] + info["menu_names"])).split()
            if model not in likely and words & set(names):
                likely.append(model)
        model_lines = []
        for model, info in catalog["models"].items():
            line = {"model": model, "label": info["label"], "menus": info["menu_names"][:4]}
            if model in likely[:5]:
                Model = self.env[model]
                line["fields"] = {
                    name: [field.type, field._description_string(self.env)] for name, field in Model._fields.items()
                    if field.store and field.type in ("char", "text", "selection", "many2one", "date",
                                                      "datetime", "integer", "float", "monetary", "boolean")
                    and not name.startswith("message_") and name not in ("id", "write_uid", "create_uid")
                }
                if info["states"]:
                    line["states"] = info["states"]
                if info["user_field"]:
                    line["user_field"] = info["user_field"]
            model_lines.append(line)
        menus = [{"id": m["id"], "path": m["path"], **({"views": m["view_modes"]} if m["view_modes"] else {}),
                  **({} if m["has_action"] else {"folder": True})} for m in catalog["menus"]][:450]
        current_app = next((m["path"] for m in catalog["menus"] if m["id"] == current_app_id), None)
        system = (
            "You turn a user's spoken request about their Odoo database into ONE JSON object. "
            "Use ONLY the menus and models listed. Never invent ids, models or fields.\n"
            "Return exactly one of:\n"
            '{"action":"navigate","menu_id":<id from menus>,"view_type":null|"kanban"|"list"|"form"|"calendar"|"pivot"|"graph"|"activity","reply":"<short sentence>"}\n'
            '(a "folder" menu has sub-menus: navigating to it lists them)\n'
            '{"action":"search","model":"<model>","domain":[[field,operator,value],...],'
            '"limit":<1-%(max)s>,"order":"<field> asc|desc" or null,"reply":"<short sentence>"}\n'
            '{"action":"count","model":"<model>","domain":[...],"reply":"<short sentence>"}\n'
            '{"action":"create","model":"<model>","values":{"<field>":<value>},'
            '"lines":[{"product":"<product name>","quantity":<number>}],"reply":"<short sentence>"}\n'
            '{"action":"write","model":"<model>","record":"<name or reference>","values":{"<field>":<value>},"reply":"..."}\n'
            '{"action":"delete"|"archive"|"unarchive"|"duplicate","model":"<model>","record":"<name or reference>","reply":"..."}\n'
            '{"action":"filter","model":"<model>","domain":[...],"view_type":null|"kanban"|...,"reply":"..."}  (open the records filtered, optionally in a view type)\n'
            '{"action":"group","model":"<model>","group_field":"<field name>","domain":[...],"reply":"..."}\n'
            '{"action":"export","model":"<model>","domain":[...],"reply":"..."}  (download Excel)\n'
            '{"action":"import","model":"<model>","reply":"..."}  (open the import screen)\n'
            '{"action":"message","recipient":"<colleague name>","body":"<message text>","reply":"..."}  (Discuss chat)\n'
            '{"action":"related","mode":"count"|"list","model":"<model>","record":"<record name>","relation":"<field label, e.g. members>","reply":"..."}  (records linked to ONE record)\n'
            '{"action":"navigate","record_model":"<model>","record":"<record name>","reply":"..."}  (open one record, e.g. a channel)\n'
            '{"action":"unknown","reply":"<short helpful sentence>"}\n'
            "Date filters: use the model's date fields with >= and <= (dates 'YYYY-MM-DD'), e.g. this month = first "
            "to last day of the current month. "
            "For create, values may be partial: the user is shown a form for the required fields. "
            "For create/write values: many2one fields take the related record's NAME (e.g. "
            "\"partner_id\":\"Azure Interior\"), selection fields a listed value, dates \"YYYY-MM-DD\". "
            "'lines' only for models with order lines (sale.order, purchase.order). "
            "'restore'/'activate'/'unarchive' -> unarchive; 'deactivate'/'make inactive' -> archive; "
            "'copy'/'clone' -> duplicate. Nothing is executed without user confirmation.\n"
            "Rules: 'where is', 'open', 'go to' -> navigate (prefer menus of the current app: %(app)s). "
            "'how many' -> count. "
            "Searching by name -> [\"display_name\",\"ilike\",\"<name>\"]. "
            "'my' -> [\"<user_field>\",\"=\",%(uid)s]. 'last/latest' -> order \"id desc\". "
            "Use only operators =, !=, >, >=, <, <=, ilike, in, not in. Dates as \"YYYY-MM-DD\" "
            "(today is %(today)s). The request may be in English, Tamil or a mix of both. "
            "Write \"reply\" ONLY in %(reply_lang)s, whatever language the request uses."
        ) % {"max": self._max_results(), "uid": catalog["uid"], "today": fields.Date.context_today(self),
             "app": current_app or "none",
             "reply_lang": self._reply_language_name()}
        user = json.dumps({"request": text, "menus": menus, "models": model_lines}, ensure_ascii=False)
        return system, user

    @api.model
    def _ai_parse(self, text, catalog, current_app_id=None):
        provider = self._get_setting("ai_provider", "none")
        api_key = self._get_setting("ai_api_key")
        system, user = self._ai_prompt(text, catalog, current_app_id)
        if provider == "openai":
            model = self._get_setting("ai_model") or "gpt-4o-mini"
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": "Bearer %s" % api_key, "Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                },
                timeout=AI_TIMEOUT,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
        elif provider == "gemini":
            model = self._get_setting("ai_model") or "gemini-2.5-flash"
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model,
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
                },
                timeout=AI_TIMEOUT,
            )
            response.raise_for_status()
            content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return None
        return json.loads(content)

    # ------------------------------------------------------------------
    # Voice actions: prepare (needs confirmation) -> execute
    # ------------------------------------------------------------------
    @api.model
    def _action_error(self, message):
        return {"type": "error", "message": message}

    @api.model
    def _check_action_allowed(self, action, model, catalog):
        """Return an error message, or None when the action may go ahead."""
        if action not in MODE_ALLOWS[self._action_mode()]:
            if action == "delete" and self._action_mode() == "write":
                return _("Deleting by voice is turned off in Settings → AI Voice Search.")
            return _("Changes by voice are turned off in Settings → AI Voice Search.")
        if model not in catalog["models"]:
            return _("I can't find that kind of record in your menus.")
        if not self.env["ir.model.access"].check(model, ACTION_ACCESS[action], raise_exception=False):
            return _("You don't have permission to %(action)s %(label)s records.",
                     action=self._action_verb(action), label=catalog["models"][model]["label"])
        if action in ("archive", "unarchive") and not self.env[model]._active_name:
            return _("%s records can't be archived.", catalog["models"][model]["label"])
        return None

    @api.model
    def _action_verb(self, action):
        return {
            "create": _("create"), "write": _("edit"), "delete": _("delete"),
            "archive": _("archive"), "unarchive": _("restore"), "duplicate": _("duplicate"),
        }[action]

    @api.model
    def _writable_fields(self, model):
        """{name: description} of the fields this user may set on ``model``."""
        Model = self.env[model]
        described = Model.fields_get(attributes=["string", "type", "readonly", "relation", "selection", "store"])
        allowed = set(Model.check_field_access_rights("write", None))
        magic = {"id", "create_uid", "create_date", "write_uid", "write_date", "display_name", "__last_update"}
        return {
            name: desc for name, desc in described.items()
            if name in allowed and name not in magic and not desc.get("readonly")
            and desc.get("type") in WRITABLE_TYPES and not name.startswith(("message_", "activity_"))
        }

    @api.model
    def _match_field(self, model, field_text):
        """Spoken field name -> technical name (or None)."""
        if not field_text:
            return None
        fields_ = self._writable_fields(model)
        text = parser.normalize(field_text)
        if text == "__name__":
            rec_name = self.env[model]._rec_name or "name"
            return rec_name if rec_name in fields_ else None
        for name in FIELD_ALIASES.get(text, []):
            if name in fields_:
                return name
        for name, desc in fields_.items():
            if text in (name, name.replace("_", " "), parser.normalize(desc.get("string"))):
                return name
        best, best_score = None, 0.0
        for name, desc in fields_.items():
            score = difflib.SequenceMatcher(None, text, parser.normalize(desc.get("string"))).ratio()
            if score > best_score:
                best, best_score = name, score
        return best if best_score >= 0.85 else None

    @api.model
    def _split_field_from_target(self, model, target):
        """'S00012 customer' -> ('S00012', 'partner_id') when no field was said separately."""
        target = target or ""
        low = parser.normalize(target)
        candidates = [(alias, names) for alias, names in FIELD_ALIASES.items()]
        candidates += [(parser.normalize(d.get("string")), [n]) for n, d in self._writable_fields(model).items()]
        for words, names in sorted(candidates, key=lambda c: len(c[0]), reverse=True):
            if not words:
                continue
            if low.endswith(" " + words) or low.startswith(words + " "):
                field = self._match_field(model, words)
                if field:
                    keep = target[: len(target) - len(words)] if low.endswith(" " + words) else target[len(words):]
                    return keep.strip() or None, field
        return target or None, None

    @api.model
    def _find_records(self, model, term, archived=False):
        """[(id, name)] matching the spoken name/reference, best match first."""
        if not term:
            return []
        Model = self.env[model].with_context(active_test=not archived)
        domain = [(Model._active_name, "=", False)] if archived and Model._active_name else []
        found = Model.name_search(term, domain=domain, operator="ilike", limit=6)
        exact = [r for r in found if parser.normalize(r[1]) == parser.normalize(term)]
        return exact[:1] if len(exact) == 1 else found

    @api.model
    def _convert_value(self, model, field_name, raw):
        """Spoken value -> (stored value, readable text). Raises ValueError with a user message."""
        desc = self._writable_fields(model).get(field_name)
        if not desc:
            raise ValueError(_("That field can't be changed by voice."))
        ftype, label = desc["type"], desc.get("string") or field_name
        text = str(raw).strip() if raw is not None else ""
        if ftype in ("char", "text", "html"):
            return text, text
        if ftype in ("integer", "float", "monetary"):
            number = re.sub(r"[^\d.\-]", "", text.replace(",", ""))
            try:
                value = int(float(number)) if ftype == "integer" else float(number)
            except ValueError:
                raise ValueError(_("“%(value)s” isn't a number for %(field)s.", value=text, field=label))
            return value, str(value)
        if ftype == "boolean":
            low = text.lower()
            if low in TRUE_WORDS or raw is True:
                return True, _("Yes")
            if low in FALSE_WORDS or raw is False:
                return False, _("No")
            raise ValueError(_("Say yes or no for %s.", label))
        if ftype == "selection":
            for value, value_label in desc.get("selection") or []:
                if parser.normalize(text) in (parser.normalize(str(value)), parser.normalize(value_label)):
                    return value, value_label
            raise ValueError(_("“%(value)s” isn't a valid %(field)s.", value=text, field=label))
        if ftype in ("date", "datetime"):
            # Already-stored formats (also used when a confirmed operation is re-checked):
            # ISO must never go through dayfirst parsing, which would swap month and day.
            if ftype == "datetime" and ISO_DATETIME_RE.match(text):
                stamp = fields.Datetime.to_datetime(text[:19])
                return fields.Datetime.to_string(stamp), fields.Datetime.to_string(stamp)[:16]
            low = text.lower()
            today = fields.Date.context_today(self)
            relative = {"today": 0, "tomorrow": 1, "yesterday": -1}
            try:
                if low in relative:
                    day = today + timedelta(days=relative[low])
                elif ISO_DATE_RE.match(text):
                    day = fields.Date.to_date(text[:10])
                else:
                    day = date_parser.parse(text, dayfirst=True, fuzzy=True, default=fields.Datetime.now()).date()
            except (ValueError, OverflowError):
                raise ValueError(_("“%(value)s” isn't a date I understand for %(field)s.", value=text, field=label))
            if ftype == "date":
                return fields.Date.to_string(day), fields.Date.to_string(day)
            local = pytz.timezone(self.env.user.tz or "UTC").localize(fields.Datetime.to_datetime(day).replace(hour=9))
            utc = local.astimezone(pytz.utc).replace(tzinfo=None)
            return fields.Datetime.to_string(utc), fields.Date.to_string(day)
        if ftype == "many2one":
            comodel = desc["relation"]
            if isinstance(raw, int) and not isinstance(raw, bool):
                record = self.env[comodel].browse(raw).exists()
                if record:
                    return record.id, record.display_name
            found = self._find_records(comodel, text)
            if not found:
                raise ValueError(_("No %(field)s named “%(value)s” was found.", field=label, value=text))
            if len(found) > 1:
                raise ValueError(_("Several %(field)s match “%(value)s”: %(names)s. Say the full name.",
                                   field=label, value=text, names=", ".join(n for _i, n in found[:4])))
            return found[0][0], found[0][1]
        raise ValueError(_("That field can't be changed by voice."))

    @api.model
    def _order_line_info(self, model):
        """(lines field, line model, quantity field) for order-like models, else None."""
        Model = self.env[model]
        line_field = Model._fields.get("order_line")
        if not line_field or line_field.type != "one2many":
            return None
        Line = self.env[line_field.comodel_name]
        qty_field = next((f for f in ("product_uom_qty", "product_qty", "quantity") if f in Line._fields), None)
        if "product_id" not in Line._fields or not qty_field:
            return None
        return "order_line", line_field.comodel_name, qty_field

    @api.model
    def _prepare_create(self, intent, catalog):
        model = intent["model"]
        label = catalog["models"][model]["label"]
        values, summary, lines = {}, [], []
        line_info = self._order_line_info(model)
        writable = self._writable_fields(model)
        # AI: explicit field values
        for name, raw in (intent.get("values") or {}).items():
            if name not in writable:
                raise ValueError(_("“%s” can't be set by voice.", name))
            values[name], shown = self._convert_value(model, name, raw)
            summary.append("%s: %s" % (writable[name]["string"], shown))
        # Keyword: "create sales order for <customer>" / "create customer named <name>"
        name_text = intent.get("name")
        if name_text:
            if line_info and "partner_id" in writable and "partner_id" not in values:
                values["partner_id"], shown = self._convert_value(model, "partner_id", name_text)
                summary.append("%s: %s" % (writable["partner_id"]["string"], shown))
            else:
                rec_name = self.env[model]._rec_name or "name"
                if rec_name in writable and rec_name not in values:
                    values[rec_name] = name_text
                    summary.append("%s: %s" % (writable[rec_name]["string"], name_text))
        # Order lines: [(qty, product)] from keywords or [{"product":..,"quantity":..}] from AI
        raw_lines = intent.get("lines") or []
        if raw_lines and not line_info:
            raise ValueError(_("%s records don't have product lines.", label))
        for raw in raw_lines:
            qty, product_text = (raw if isinstance(raw, (list, tuple)) else (raw.get("quantity", 1), raw.get("product")))
            try:
                qty = float(qty)
            except (TypeError, ValueError):
                qty = 1.0
            line_model = line_info[1]
            found = self._find_records(self.env[line_model]._fields["product_id"].comodel_name, str(product_text or ""))
            if not found:
                raise ValueError(_("No product named “%s” was found.", product_text))
            if len(found) > 1:
                raise ValueError(_("Several products match “%(value)s”: %(names)s. Say the full name.",
                                   value=product_text, names=", ".join(n for _i, n in found[:4])))
            lines.append({"product_id": found[0][0], "quantity": max(qty, 0.0) or 1.0})
            summary.append(_("Line: %(qty)s × %(product)s", qty=("%g" % (max(qty, 0.0) or 1.0)), product=found[0][1]))
        return values, lines, summary

    @api.model
    def _prepare_operation(self, intent, catalog):
        action = intent["action"]
        if intent.get("error") == "missing_value":
            return self._action_error(_("Say the new value, e.g. “set phone of customer Azure Interior to 9876543210”."))
        if intent.get("error") == "no_model":
            return self._action_error(_("Which kind of record? e.g. “%s quotation S00012”.", self._action_verb(action)))
        model = intent["model"]
        problem = self._check_action_allowed(action, model, catalog)
        if problem:
            return self._action_error(problem)
        label = catalog["models"][model]["label"]

        if action == "create":
            try:
                values, lines, summary = self._prepare_create(intent, catalog)
            except ValueError as error:
                return self._action_error(str(error))
            operation = {"action": "create", "model": model, "res_id": False, "values": values, "lines": lines}
            return self._confirm(operation, _("Create %s", label), summary)

        # Find the record the user meant
        target = intent.get("record") or intent.get("target")
        field_from_target = None
        if action == "write" and not intent.get("values") and not intent.get("field"):
            target, field_from_target = self._split_field_from_target(model, target)
        if not target:
            return self._action_error(_("Which %s? Say its name or reference.", label))
        found = self._find_records(model, target, archived=(action == "unarchive"))
        if not found:
            return self._action_error(_("No %(label)s named “%(name)s” was found.", label=label, name=target))

        values, summary = {}, []
        if action == "write":
            try:
                if intent.get("values"):
                    for name, raw in intent["values"].items():
                        values[name], shown = self._convert_value(model, name, raw)
                        summary.append("%s → %s" % (self._writable_fields(model)[name]["string"], shown))
                else:
                    field = self._match_field(model, intent.get("field")) if intent.get("field") else field_from_target
                    if not field:
                        return self._action_error(_("I couldn't find the field “%(field)s” on %(label)s.",
                                                    field=intent.get("field") or target, label=label))
                    values[field], shown = self._convert_value(model, field, intent.get("value"))
                    summary.append("%s → %s" % (self._writable_fields(model)[field]["string"], shown))
            except ValueError as error:
                return self._action_error(str(error))
            if not values:
                return self._action_error(_("Say what to change, e.g. “set phone of customer Azure Interior to 98765”."))

        titles = {
            "write": _("Update"), "delete": _("Delete"), "archive": _("Archive"),
            "unarchive": _("Restore"), "duplicate": _("Duplicate"),
        }
        if len(found) > 1:
            return {
                "type": "choose",
                "message": _("Several %s match. Which one?", label),
                "choices": [
                    {"name": name, **self._confirm(
                        {"action": action, "model": model, "res_id": rid, "values": values, "lines": []},
                        "%s %s" % (titles[action], name), summary)}
                    for rid, name in found[:5]
                ],
            }
        rid, name = found[0]
        operation = {"action": action, "model": model, "res_id": rid, "values": values, "lines": []}
        return self._confirm(operation, "%s %s" % (titles[action], name), summary)

    @api.model
    def _confirm(self, operation, title, summary):
        warnings = {
            "delete": _("This permanently deletes the record."),
            "archive": _("The record will be hidden from lists until restored."),
        }
        return {
            "type": "confirm",
            "operation": operation,
            "title": title,
            "summary": summary,
            "danger": operation["action"] == "delete",
            "message": warnings.get(operation["action"]) or _("Please confirm."),
        }

    @api.model
    def execute_operation(self, operation, lang=None):
        """Run a confirmed operation. Everything is checked again: the browser is not trusted."""
        if lang is not None:
            self = self._with_reply_lang(lang)  # noqa: PLW0642
        if not isinstance(operation, dict):
            return self._action_error(_("Nothing to do."))
        action, model = operation.get("action"), operation.get("model")
        if action == "message":
            return self._send_message(operation)
        if action not in WRITE_ACTIONS:
            return self._action_error(_("Nothing to do."))
        catalog = self._get_catalog()
        problem = self._check_action_allowed(action, model, catalog)
        if problem:
            return self._action_error(problem)
        Model = self.env[model]
        label = catalog["models"][model]["label"]

        # Re-validate the values against the user's writable fields
        values = {}
        writable = self._writable_fields(model)
        try:
            for name, value in (operation.get("values") or {}).items():
                if name not in writable:
                    raise ValueError(_("“%s” can't be set by voice.", name))
                if writable[name]["type"] == "many2one":
                    record = self.env[writable[name]["relation"]].browse(int(value)).exists()
                    if not record:
                        raise ValueError(_("A linked record no longer exists."))
                    record.check_access("read")
                    values[name] = record.id
                else:
                    values[name] = self._convert_value(model, name, value)[0]
        except (ValueError, TypeError) as error:
            return self._action_error(str(error))
        except AccessError:
            return self._action_error(_("You don't have access to a linked record."))

        record = Model.browse()
        if action != "create":
            try:
                record = Model.with_context(active_test=False).browse(int(operation.get("res_id"))).exists()
            except (TypeError, ValueError):
                record = Model.browse()
            if not record:
                return self._action_error(_("That %s no longer exists.", label))

        try:
            with self.env.cr.savepoint():
                if action != "create":
                    record.check_access(ACTION_ACCESS[action] if action != "duplicate" else "read")
                if action == "create":
                    vals = dict(values)
                    line_info = self._order_line_info(model)
                    if operation.get("lines"):
                        if not line_info:
                            raise ValidationError(_("%s records don't have product lines.", label))
                        _field, line_model, qty_field = line_info
                        Product = self.env[self.env[line_model]._fields["product_id"].comodel_name]
                        commands = []
                        for line in operation["lines"]:
                            product = Product.browse(int(line.get("product_id"))).exists()
                            if not product:
                                raise ValidationError(_("A product no longer exists."))
                            product.check_access("read")
                            commands.append(Command.create({"product_id": product.id,
                                                            qty_field: float(line.get("quantity") or 1)}))
                        vals["order_line"] = commands
                    new = Model.create(vals)
                    return self._done(_("%(label)s %(name)s created.", label=label, name=new.display_name), new)
                if action == "write":
                    record.write(values)
                    return self._done(_("%s updated.", record.display_name), record, reload=True)
                if action == "delete":
                    name = record.display_name
                    record.unlink()
                    return self._done(_("%s deleted.", name), None, reload=True)
                if action == "archive":
                    record.action_archive()
                    return self._done(_("%s archived.", record.display_name), None, reload=True)
                if action == "unarchive":
                    record.action_unarchive()
                    return self._done(_("%s restored.", record.display_name), record, reload=True)
                if action == "duplicate":
                    copy = record.copy()
                    return self._done(_("Copy created: %s.", copy.display_name), copy)
        except AccessError:
            return self._action_error(_("You don't have permission to %(action)s this %(label)s.",
                                        action=self._action_verb(action), label=label))
        except (UserError, ValidationError) as error:
            return self._action_error(str(error.args[0] if error.args else error))
        except Exception as error:  # database constraints, required fields...
            _logger.warning("Voice action %s on %s failed: %s", action, model, error)
            return self._action_error(_("Odoo couldn't %(action)s this %(label)s. Open it to complete the "
                                        "required information.", action=self._action_verb(action), label=label))
        return self._action_error(_("Nothing to do."))

    @api.model
    def _done(self, message, record, reload=False):
        return {
            "type": "done",
            "message": message,
            "open": {"res_model": record._name, "res_id": record.id} if record else False,
            "reload": reload,
        }

    # ------------------------------------------------------------------
    # Filter / group by / export / import
    # ------------------------------------------------------------------
    @api.model
    def _searchable_fields(self, model, types=SEARCH_TYPES):
        Model = self.env[model]
        described = Model.fields_get(attributes=["string", "type", "store", "searchable", "selection", "relation"])
        readable = set(Model.check_field_access_rights("read", None))
        return {
            name: desc for name, desc in described.items()
            if name in readable and desc.get("type") in types
            and (desc.get("store") or desc.get("searchable")) and not name.startswith(("message_", "activity_"))
        }

    @api.model
    def _match_in_fields(self, fields_, text):
        """Spoken field name -> technical name among ``fields_`` (aliases, labels, fuzzy)."""
        text = parser.normalize(text)
        if not text:
            return None
        for name in FIELD_ALIASES.get(text, []):
            if name in fields_:
                return name
        for name, desc in fields_.items():
            if text in (name, name.replace("_", " "), parser.normalize(desc.get("string"))):
                return name
        best, best_score = None, 0.0
        for name, desc in fields_.items():
            score = difflib.SequenceMatcher(None, text, parser.normalize(desc.get("string"))).ratio()
            if score > best_score:
                best, best_score = name, score
        return best if best_score >= 0.85 else None

    @api.model
    def _date_domain(self, model, condition):
        """'<field words> | <date phrase>' -> (domain leaves, readable text)."""
        field_words, phrase = [part.strip() for part in condition.split("|", 1)]
        date_fields = self._searchable_fields(model, ("date", "datetime"))
        candidates = DATE_FIELD_ALIASES.get(field_words or "date", [])
        field = next((f for f in candidates if f in date_fields), None)
        if not field and field_words:
            field = self._match_in_fields(date_fields, field_words) or self._match_in_fields(date_fields, field_words + " date")
        if not field:
            label = self.env["ir.model"]._get(model).name
            raise ValueError(_("%(label)s records have no %(field)s to filter on.", label=label,
                               field=field_words or _("date")))
        try:
            start, end = parser.date_range(phrase, fields.Date.context_today(self))
        except (ValueError, OverflowError):
            raise ValueError(_("I couldn't understand the date “%s”.", phrase))
        leaves = []
        if date_fields[field]["type"] == "date":
            if start:
                leaves.append([field, ">=", fields.Date.to_string(start)])
            if end:
                leaves.append([field, "<=", fields.Date.to_string(end)])
        else:
            # datetime: the user's local days, stored in UTC
            tz = pytz.timezone(self.env.user.tz or "UTC")

            def _utc(day):
                local = tz.localize(fields.Datetime.to_datetime(day))
                return fields.Datetime.to_string(local.astimezone(pytz.utc).replace(tzinfo=None))
            if start:
                leaves.append([field, ">=", _utc(start)])
            if end:
                leaves.append([field, "<", _utc(end + timedelta(days=1))])
        label = date_fields[field].get("string") or field
        shown = "%s → %s" % (start or "…", end or "…") if start != end else str(start)
        return leaves, "%s: %s (%s)" % (label, phrase, shown)

    @api.model
    def _condition_domain(self, model, condition):
        """'city is Chennai' / 'state posted' / 'customer Azure' -> (domain leaves, readable text)."""
        if "|" in condition:
            return self._date_domain(model, condition)
        fields_ = self._searchable_fields(model)
        words = condition.split()
        # longest spoken field name first: "sales person" before "sales"
        for size in range(min(4, len(words) - 1), 0, -1):
            field = self._match_in_fields(fields_, " ".join(words[:size]))
            if not field:
                continue
            value = CONDITION_JOINERS_RE.sub("", " ".join(words[size:])).strip()
            if not value:
                continue
            desc, label = fields_[field], fields_[field].get("string") or field
            ftype = desc["type"]
            if ftype == "selection":
                for key, key_label in desc.get("selection") or []:
                    if parser.normalize(value) in (parser.normalize(str(key)), parser.normalize(key_label)):
                        return [[field, "=", key]], "%s: %s" % (label, key_label)
                raise ValueError(_("“%(value)s” isn't a valid %(field)s.", value=value, field=label))
            if ftype == "boolean":
                low = value.lower()
                if low not in TRUE_WORDS | FALSE_WORDS:
                    raise ValueError(_("Say yes or no for %s.", label))
                return [[field, "=", low in TRUE_WORDS]], "%s: %s" % (label, value)
            if ftype in ("integer", "float", "monetary"):
                number = re.sub(r"[^\d.\-]", "", value.replace(",", ""))
                try:
                    number = float(number)
                except ValueError:
                    raise ValueError(_("“%(value)s” isn't a number for %(field)s.", value=value, field=label))
                return [[field, "=", int(number) if ftype == "integer" else number]], "%s: %s" % (label, value)
            if ftype in ("date", "datetime"):
                return self._date_domain(model, "%s | %s" % (desc.get("string", field).lower(), value))
            # char / text / html / many2one: contains (many2one matches the related record's name)
            return [[field, "ilike", value]], "%s: %s" % (label, value)
        raise ValueError(_("I couldn't find a field for “%s”.", condition))

    @api.model
    def _convert_value_any(self, model, field, desc, value):
        """Date parsing shared with _convert_value, for any (also read-only) field."""
        low = value.lower()
        today = fields.Date.context_today(self)
        relative = {"today": 0, "tomorrow": 1, "yesterday": -1}
        if low in relative:
            return fields.Date.to_string(today + timedelta(days=relative[low]))
        if ISO_DATE_RE.match(value):
            return value
        try:
            return fields.Date.to_string(date_parser.parse(value, dayfirst=True, fuzzy=True).date())
        except (ValueError, OverflowError):
            raise ValueError(_("“%(value)s” isn't a date I understand for %(field)s.",
                               value=value, field=desc.get("string") or field))

    @api.model
    def _list_action(self, intent, catalog):
        action, model = intent["action"], intent.get("model")
        if intent.get("error") == "no_model":
            return self._action_error(_("Which records? e.g. “%s contacts”.", action))
        if intent.get("error") == "no_field":
            return self._action_error(_("Group by which field? e.g. “group contacts by country”."))
        label = catalog["models"][model]["label"]
        domain = self._expand_name_search(model, list(intent.get("domain") or []))
        readable = []
        try:
            for condition in intent.get("conditions") or []:
                leaves, text = self._condition_domain(model, condition)
                domain.extend(leaves)
                readable.append(text)
        except ValueError as error:
            return self._action_error(str(error))

        view_type = intent.get("view_type")
        if view_type and not self._view_available(model, view_type):
            return self._action_error(_("%(label)s records have no %(view)s view.", label=label, view=view_type))
        views = [[False, view_type]] if view_type else []
        views += [[False, v] for v in ("list", "form") if v != view_type]
        list_action = {
            "type": "ir.actions.act_window",
            "name": label,
            "res_model": model,
            "domain": domain,
            "views": views,
            "target": "current",
            "context": {},
        }
        if action == "import":
            if not self.env["ir.model.access"].check(model, "create", raise_exception=False):
                return self._action_error(_("You don't have permission to import %s records.", label))
            return {
                "type": "action",
                "message": _("Opening the import screen for %s.", label),
                "action": {"type": "ir.actions.client", "tag": "import",
                           "params": {"active_model": model, "context": {}}},
            }
        try:
            count = self.env[model].search_count(domain)
        except (AccessError, UserError, ValueError):
            return self._action_error(_("I couldn't run that search. Try rephrasing it."))
        if action == "group":
            group_field = self._match_in_fields(self._searchable_fields(model, GROUP_TYPES), intent.get("group_field"))
            if not group_field:
                return self._action_error(_("I couldn't find the field “%(field)s” to group %(label)s by.",
                                            field=intent.get("group_field"), label=label))
            group_label = self._searchable_fields(model, GROUP_TYPES)[group_field].get("string")
            list_action["context"] = {"group_by": [group_field]}
            list_action["name"] = _("%(label)s by %(field)s", label=label, field=group_label)
            return {"type": "action", "action": list_action,
                    "message": _("%(label)s grouped by %(field)s (%(count)s records).",
                                 label=label, field=group_label, count=count)}
        if action == "export":
            if not count:
                return self._action_error(_("No %s records match, so there is nothing to export.", label))
            return {"type": "export", "model": model, "domain": domain, "count": min(count, EXPORT_LIMIT),
                    "message": _("Exporting %(count)s %(label)s records to Excel.",
                                 count=min(count, EXPORT_LIMIT), label=label)}
        # filter
        text = ", ".join(readable)
        return {"type": "action", "action": list_action,
                "message": _("%(label)s filtered by %(filters)s: %(count)s found.", label=label,
                             filters=text, count=count) if text else
                _("%(label)s: %(count)s found.", label=label, count=count)}

    @api.model
    def export_file(self, model, domain, lang=None):
        """Excel file of the records, with the columns of the model's list view."""
        self = self._with_reply_lang(lang)  # noqa: PLW0642
        catalog = self._get_catalog()
        if model not in catalog["models"]:
            raise AccessError(_("You can't export these records."))
        domain = domain if isinstance(domain, list) else []
        Domain(domain).validate(self.env[model])
        Model = self.env[model]
        readable = set(Model.check_field_access_rights("read", None))
        columns = []
        try:
            arch = Model.get_views([(False, "list")])["views"]["list"]["arch"]
            for node in etree.fromstring(arch).iter("field"):
                name = node.get("name")
                hidden = node.get("column_invisible") in ("1", "True", "true") or node.get("invisible") in ("1", "True", "true")
                if name in Model._fields and name in readable and not hidden and name not in columns \
                        and Model._fields[name].type not in ("binary", "one2many", "many2many", "html", "json"):
                    columns.append(name)
        except Exception:  # no usable list view: fall back to the record name
            columns = []
        columns = columns[:25] or ["display_name"]
        records = Model.search(domain, limit=EXPORT_LIMIT)
        rows = records.export_data(columns).get("datas", [])

        import xlsxwriter  # noqa: PLC0415 - Odoo dependency, only needed here
        buffer = io.BytesIO()
        book = xlsxwriter.Workbook(buffer, {"in_memory": True})
        sheet = book.add_worksheet(catalog["models"][model]["label"][:31])
        bold = book.add_format({"bold": True, "bg_color": "#EDE7F6"})
        for col, name in enumerate(columns):
            sheet.write(0, col, Model._fields[name]._description_string(self.env) if name in Model._fields else name, bold)
            sheet.set_column(col, col, 22)
        for row_index, row in enumerate(rows, start=1):
            for col, value in enumerate(row):
                sheet.write(row_index, col, value if value not in (False, None) else "")
        book.close()
        filename = "%s.xlsx" % re.sub(r"[^\w\- ]", "", catalog["models"][model]["label"]).strip().replace(" ", "_")
        return buffer.getvalue(), filename or "export.xlsx"

    # ------------------------------------------------------------------
    # Create: show the required fields first, create after the user fills them
    # ------------------------------------------------------------------
    @api.model
    def _auto_filled(self, model, name):
        """True when Odoo fills the field itself: computed (e.g. invoice/delivery address from
        the customer) or related to another field."""
        field = self.env[model]._fields.get(name)
        return bool(field and (field.compute or field.related))

    @api.model
    def _required_fields(self, model):
        """[(name, description)] of the fields the user really has to give: required, no
        default value (e.g. Order Reference "New" -> S00012), not computed and not related."""
        Model = self.env[model]
        described = Model.fields_get(attributes=["string", "type", "required", "readonly", "relation", "selection"])
        required = [n for n, d in described.items() if d.get("required") and not d.get("readonly")
                    and n not in ("id", "create_uid", "write_uid", "create_date", "write_date")
                    and not self._auto_filled(model, n)]
        defaults = Model.default_get(required) if required else {}
        return [(n, described[n]) for n in required if defaults.get(n) in (None, False, "")]

    @api.model
    def _name_must_be_given(self, model, writable):
        """The record name is asked only when nothing fills it (e.g. contacts), never when it has
        a default or is computed (e.g. sales order reference "New")."""
        rec_name = self.env[model]._rec_name or "name"
        if rec_name not in writable or writable[rec_name]["type"] != "char" or self._auto_filled(model, rec_name):
            return None
        default = self.env[model].default_get([rec_name]).get(rec_name)
        return None if default not in (None, False, "") else rec_name

    @api.model
    def _create_form(self, intent, catalog):
        model = intent["model"]
        problem = self._check_action_allowed("create", model, catalog)
        if problem:
            return self._action_error(problem)
        label = catalog["models"][model]["label"]
        try:
            values, lines, _summary = self._prepare_create(intent, catalog)
        except ValueError as error:
            return self._action_error(str(error))
        writable = self._writable_fields(model)
        form_fields, unsupported, seen = [], [], set()

        def _field_entry(name, desc, required):
            value = values.get(name, False)
            display = ""
            if desc["type"] == "many2one" and value:
                display = self.env[desc["relation"]].browse(value).display_name
            elif value not in (False, None):
                display = str(value)
            return {"name": name, "label": desc.get("string") or name, "type": desc["type"],
                    "required": required, "value": value, "display": display,
                    "selection": desc.get("selection") or [], "relation": desc.get("relation") or False}

        for name, desc in self._required_fields(model):
            if name in writable:
                form_fields.append(_field_entry(name, writable[name], True))
                seen.add(name)
            else:
                unsupported.append(desc.get("string") or name)
        # The record's name is asked when nothing fills it (contacts require it through a constraint)
        rec_name = self._name_must_be_given(model, writable)
        if rec_name and rec_name not in seen:
            form_fields.insert(0, _field_entry(rec_name, writable[rec_name], True))
            seen.add(rec_name)
        for name in values:
            if name not in seen and name in writable:
                form_fields.append(_field_entry(name, writable[name], False))
        line_rows = []
        line_info = self._order_line_info(model)
        if lines and line_info:
            Product = self.env[self.env[line_info[1]]._fields["product_id"].comodel_name]
            line_rows = [dict(line, display=Product.browse(line["product_id"]).display_name) for line in lines]
        context = {"default_%s" % name: value for name, value in values.items()}
        return {
            "type": "form",
            "model": model,
            "title": _("Create %s", label),
            "fields": form_fields,
            "lines": line_rows,
            "unsupported": unsupported,
            "message": _("Fill in the required fields, then press Create.") if form_fields
            else _("Press Create to create the %s.", label),
            "open_form_action": {"type": "ir.actions.act_window", "res_model": model, "name": label,
                                 "views": [[False, "form"]], "target": "current", "context": context},
        }

    @api.model
    def create_from_form(self, model, values, lines=None, lang=None):
        """Create the record from the filled form (checked again server side)."""
        self = self._with_reply_lang(lang)  # noqa: PLW0642
        catalog = self._get_catalog()
        problem = self._check_action_allowed("create", model, catalog)
        if problem:
            return self._action_error(problem)
        writable = self._writable_fields(model)
        converted = {}
        try:
            for name, raw in (values or {}).items():
                if raw in (None, False, "") and writable.get(name, {}).get("type") != "boolean":
                    continue
                if name not in writable:
                    raise ValueError(_("“%s” can't be set by voice.", name))
                if writable[name]["type"] == "many2one":
                    record = self.env[writable[name]["relation"]].browse(int(raw)).exists()
                    if not record:
                        raise ValueError(_("Choose a valid %s.", writable[name]["string"]))
                    converted[name] = record.id
                else:
                    converted[name] = self._convert_value(model, name, raw)[0]
        except (ValueError, TypeError) as error:
            return self._action_error(str(error))
        missing = [desc.get("string") or name for name, desc in self._required_fields(model) if name not in converted]
        rec_name = self._name_must_be_given(model, writable)
        if rec_name and not converted.get(rec_name):
            missing.insert(0, writable[rec_name]["string"])
        if missing:
            return self._action_error(_("Please fill in: %s.", ", ".join(missing)))
        operation = {"action": "create", "model": model, "res_id": False, "values": converted,
                     "lines": [{"product_id": line.get("product_id"), "quantity": line.get("quantity")}
                               for line in (lines or []) if isinstance(line, dict)]}
        return self.execute_operation(operation)

    @api.model
    def field_search(self, model, field, term):
        """Suggestions for a many2one field of the create form."""
        catalog = self._get_catalog()
        if model not in catalog["models"]:
            return []
        desc = self._writable_fields(model).get(field)
        if not desc or desc["type"] != "many2one":
            return []
        return [[rid, name] for rid, name in self.env[desc["relation"]].name_search(term or "", limit=8)]

    # ------------------------------------------------------------------
    # Messages to colleagues (Discuss direct chat)
    # ------------------------------------------------------------------
    @api.model
    def _message_recipients(self, name):
        """Active internal users (not the current one) matching the spoken name."""
        Users = self.env["res.users"]
        domain = [("share", "=", False), ("id", "!=", self.env.uid)]
        found = Users.name_search(name, domain=domain, operator="ilike", limit=6)
        exact = [r for r in found if parser.normalize(r[1]) == parser.normalize(name)]
        return exact[:1] if len(exact) == 1 else found

    @api.model
    def _prepare_message(self, intent):
        if "message" not in MODE_ALLOWS[self._action_mode()]:
            return self._action_error(_("Changes by voice are turned off in Settings → AI Voice Search."))
        if "discuss.channel" not in self.env:
            return self._action_error(_("Messages need the Discuss app."))
        if intent.get("error"):
            return self._action_error(_("Say who and what, e.g. “send message to Mitchell Admin saying the meeting is at 5”."))
        found = self._message_recipients(intent["recipient"])
        if not found:
            return self._action_error(_("No user named “%s” was found.", intent["recipient"]))

        def _card(user_id, name):
            return self._confirm({"action": "message", "model": "res.users", "res_id": user_id,
                                  "values": {"body": intent["body"]}, "lines": []},
                                 _("Send message to %s", name), ["“%s”" % intent["body"]])
        if len(found) > 1:
            return {"type": "choose", "message": _("Several users match. Who should get the message?"),
                    "choices": [{"name": name, **_card(uid, name)} for uid, name in found[:5]]}
        return _card(*found[0])

    @api.model
    def _send_message(self, operation):
        """Send the confirmed message in the direct chat between the current user and the recipient."""
        if "message" not in MODE_ALLOWS[self._action_mode()]:
            return self._action_error(_("Changes by voice are turned off in Settings → AI Voice Search."))
        body = ((operation.get("values") or {}).get("body") or "").strip()[:2000]
        try:
            user = self.env["res.users"].browse(int(operation.get("res_id"))).exists()
        except (TypeError, ValueError):
            user = self.env["res.users"]
        if not body or not user or user.share or user == self.env.user or "discuss.channel" not in self.env:
            return self._action_error(_("That message can't be sent."))
        try:
            with self.env.cr.savepoint():
                channel = self.env["discuss.channel"]._get_or_create_chat([user.partner_id.id])
                channel.message_post(body=Markup("<p>%s</p>") % escape(body), message_type="comment",
                                     subtype_xmlid="mail.mt_comment")
        except (AccessError, UserError) as error:
            return self._action_error(str(error.args[0] if error.args else error))
        return {"type": "done", "message": _("Message sent to %s.", user.name), "open": False, "reload": False}

    # ------------------------------------------------------------------
    # Open one record by name ("open k channel") and related records
    # ("how many members in k channel", "list members of k channel")
    # ------------------------------------------------------------------
    @api.model
    def _record_open_action(self, record):
        if record._name == "discuss.channel":
            # channels open in Discuss, like clicking them there
            return {"type": "ir.actions.client", "tag": "mail.action_discuss",
                    "params": {"active_id": "discuss.channel_%s" % record.id}, "name": record.display_name}
        return {"type": "ir.actions.act_window", "res_model": record._name, "res_id": record.id,
                "views": [[False, "form"]], "target": "current", "name": record.display_name}

    @api.model
    def _open_record(self, model, name, catalog):
        """Open the record named ``name``; several matches -> pick list; none -> None."""
        try:
            found = self._find_records(model, name)
        except AccessError:
            return None
        if not found:
            return None
        label = catalog["models"][model]["label"]
        records = self.env[model].browse([rid for rid, _n in found])
        if len(records) == 1:
            return {"type": "action", "action": self._record_open_action(records),
                    "message": _("Opening %(label)s %(name)s.", label=label, name=records.display_name)}
        return {"type": "open_choices", "message": _("Several %s match. Which one?", label),
                "choices": [{"name": r.display_name, "action": self._record_open_action(r)} for r in records[:6]]}

    @api.model
    def _relation_field(self, model, relation):
        """Spoken relation ('members', 'contacts', 'order lines') -> one2many/many2many field."""
        Model = self.env[model]
        readable = set(Model.check_field_access_rights("read", None))
        described = Model.fields_get(attributes=["string", "type", "relation"])
        fields_ = {n: d for n, d in described.items()
                   if d.get("type") in ("one2many", "many2many") and n in readable and n not in X2MANY_SKIP
                   and d.get("relation") in self.env}
        return self._match_in_fields(fields_, relation) or self._match_in_fields(fields_, relation.rstrip("s")), fields_

    @api.model
    def _related(self, intent, catalog):
        model, label = intent["model"], catalog["models"][intent["model"]]["label"]
        field, fields_ = self._relation_field(model, intent["relation"])
        if not field:
            # not a relation of that record ("how many invoices of Azure"): normal answer
            if intent.get("fallback"):
                fallback = intent["fallback"]
                if fallback["action"] in LIST_ACTIONS:
                    return self._list_action(fallback, catalog)
                return self._execute(fallback, catalog)
            return self._action_error(_("%(label)s has no “%(rel)s”.", label=label, rel=intent["relation"]))
        found = self._find_records(model, intent["record"])
        if not found:
            return self._action_error(_("No %(label)s named “%(name)s” was found.", label=label, name=intent["record"]))
        if len(found) > 1:
            return self._action_error(_("Several %(label)s match “%(name)s”: %(names)s. Say the full name.",
                                        label=label, name=intent["record"], names=", ".join(n for _i, n in found[:5])))
        record = self.env[model].browse(found[0][0])
        try:
            related = record[field]
        except AccessError:
            return self._action_error(_("You don't have access to these records."))
        relation_label = fields_[field].get("string") or field
        # members of a channel / attendees: show the people, not the technical member records
        if related._name != "res.partner" and "partner_id" in related._fields \
                and related._fields["partner_id"].comodel_name == "res.partner" and related._name.endswith(".member"):
            related = related.mapped("partner_id")
        list_action = {"type": "ir.actions.act_window", "name": "%s: %s" % (record.display_name, relation_label),
                       "res_model": related._name, "domain": [["id", "in", related.ids]],
                       "views": [[False, "list"], [False, "form"]], "target": "current"} \
            if related and self.env["ir.model.access"].check(related._name, "read", raise_exception=False) else False
        if intent["mode"] == "count":
            return {"type": "count", "model": related._name, "count": len(related), "list_action": list_action,
                    "message": _("%(record)s has %(count)s %(relation)s.", record=record.display_name,
                                 count=len(related), relation=relation_label.lower())}
        rows = self._format_records(related[: self._max_results()])
        return {"type": "records", "model": related._name, "count": len(related), "records": rows,
                "list_action": list_action,
                "message": _("%(relation)s of %(record)s: %(count)s.", relation=relation_label,
                             record=record.display_name, count=len(related)) if related else
                _("%(record)s has no %(relation)s.", record=record.display_name, relation=relation_label.lower())}
