# -*- coding: utf-8 -*-
import json
import logging
import re
from datetime import date

import requests

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_VERSION = "2023-06-01"
GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
REQUEST_TIMEOUT = 30

# Logical operators allowed inside an Odoo domain (polish notation).
DOMAIN_OPERATORS = {"&", "|", "!"}

# Short keywords a user can type right after "ai:" to force a specific
# provider *family* for that one query, e.g. "ai:claude sale orders this month".
# Several active providers of different families (and/or several custom
# providers of the same family with different names) can coexist; whichever
# one is not overridden by a hint falls back to the highest-priority
# (lowest sequence) active provider.
PROVIDER_ALIASES = {
    "gpt": "openai",
    "chatgpt": "openai",
    "openai": "openai",
    "claude": "claude",
    "anthropic": "claude",
    "gemini": "gemini",
    "google": "gemini",
}


class AIService(models.AbstractModel):
    _name = "ai.service"
    _description = "AI Service"

    # ------------------------------------------------------------------
    # Provider / metadata helpers
    # ------------------------------------------------------------------
    def get_active_provider(self, hint=None):
        """Return the provider to use for this call.

        If `hint` is given (a word the user typed right after "ai:", e.g.
        "claude", "gemini", "gpt", or the exact Name of one of their
        configured providers), try to resolve it to a specific *active*
        provider. Otherwise fall back to the highest-priority
        (lowest sequence) active provider, exactly as before.
        """
        Provider = self.env["ai.provider"]
        if hint:
            hint_norm = hint.strip().lower()
            family = PROVIDER_ALIASES.get(hint_norm)
            if family:
                provider = Provider.search(
                    [("active", "=", True), ("provider", "=", family)],
                    order="sequence, id",
                    limit=1,
                )
            else:
                provider = Provider.search(
                    [("active", "=", True), ("name", "=ilike", hint_norm)],
                    order="sequence, id",
                    limit=1,
                )
            if provider:
                return provider
            active_names = Provider.search([("active", "=", True)]).mapped("name")
            raise UserError(
                _(
                    "No active AI provider matches '%(hint)s'.\n"
                    "Active providers: %(names)s"
                )
                % {
                    "hint": hint,
                    "names": ", ".join(active_names) or _("(none configured)"),
                }
            )

        provider = Provider.search(
            [("active", "=", True)], order="sequence, id", limit=1
        )
        if not provider:
            raise UserError(
                _(
                    "No active AI provider is configured.\n"
                    "Go to AI Search > Providers and create one."
                )
            )
        return provider

    def get_model_fields(self, model_name):
        """Return a compact field description the model can reason about."""
        if model_name not in self.env:
            raise UserError(_("Unknown model: %s") % model_name)

        fields_data = self.env[model_name].fields_get(
            attributes=["string", "type", "relation", "selection"]
        )
        result = []
        for fname, finfo in fields_data.items():
            entry = {
                "name": fname,
                "type": finfo.get("type"),
                "label": finfo.get("string"),
            }
            if finfo.get("relation"):
                entry["relation"] = finfo["relation"]
            if finfo.get("selection"):
                entry["selection"] = [s[0] for s in finfo["selection"]]
            result.append(entry)
        return result

    # ------------------------------------------------------------------
    # Prompt
    # ------------------------------------------------------------------
    def build_prompt(self, model_name, user_query):
        fields_data = self.get_model_fields(model_name)
        today = date.today().isoformat()
        return f"""You are an Odoo 18 search assistant. Convert the user request \
into a valid Odoo search specification for the model below.

Today's date is {today}. Use it to resolve relative dates such as \
"this month", "last 3 months", "this year".

Model: {model_name}

Available fields (name, type, label, optional relation/selection):
{json.dumps(fields_data, ensure_ascii=False)}

Rules:
- Only use field names that exist in the list above.
- A domain is a JSON list of triplets [field, operator, value]. Combine \
multiple conditions with the prefix operators "&" (and) and "|" (or), exactly \
like Odoo expects. Example: ["&", ["state", "=", "done"], ["amount", ">", 100]].
- Allowed operators: =, !=, >, >=, <, <=, like, ilike, in, not in, child_of.
- For dates use ISO strings, e.g. "2026-06-01".
- group_by is a list of field names (technical names) or empty.
- Do NOT invent fields. If a requested field does not exist, omit that condition.
- Return STRICT JSON only, no markdown, no commentary.

User request: {user_query}

Return JSON in exactly this shape:
{{"domain": [], "group_by": [], "explanation": "short human readable summary"}}"""

    # ------------------------------------------------------------------
    # Provider calls
    # ------------------------------------------------------------------
    def _call_provider(self, provider, system_prompt, user_query):
        if provider.provider == "openai":
            return self._call_openai(provider, system_prompt, user_query)
        if provider.provider == "claude":
            return self._call_claude(provider, system_prompt, user_query)
        if provider.provider == "gemini":
            return self._call_gemini(provider, system_prompt, user_query)
        if provider.provider == "openai_compatible":
            return self._call_openai_compatible(provider, system_prompt, user_query)
        raise UserError(_("Unsupported provider: %s") % provider.provider)

    def _call_openai(self, provider, system_prompt, user_query):
        headers = {
            "Authorization": "Bearer %s" % provider.api_key.strip(),
            "Content-Type": "application/json",
        }
        payload = {
            "model": provider.model_name or "gpt-4o",
            "temperature": provider.temperature,
            "max_tokens": provider.max_tokens or 1024,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
        }
        resp = requests.post(
            OPENAI_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code != 200:
            raise UserError(
                _("OpenAI error (%s): %s") % (resp.status_code, resp.text[:500])
            )
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    def _call_claude(self, provider, system_prompt, user_query):
        headers = {
            "x-api-key": provider.api_key.strip(),
            "anthropic-version": CLAUDE_VERSION,
            "content-type": "application/json",
        }
        payload = {
            "model": provider.model_name or "claude-sonnet-4-5",
            "max_tokens": provider.max_tokens or 1024,
            "temperature": provider.temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_query}],
        }
        resp = requests.post(
            CLAUDE_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code != 200:
            raise UserError(
                _("Claude error (%s): %s") % (resp.status_code, resp.text[:500])
            )
        data = resp.json()
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        return "".join(parts)

    def _call_gemini(self, provider, system_prompt, user_query):
        model = provider.model_name or "gemini-2.5-flash"
        url = GEMINI_URL_TEMPLATE.format(model=model)
        headers = {
            "x-goog-api-key": provider.api_key.strip(),
            "Content-Type": "application/json",
        }
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_query}]}],
            "generationConfig": {
                "temperature": provider.temperature,
                "maxOutputTokens": provider.max_tokens or 1024,
            },
        }
        resp = requests.post(
            url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code != 200:
            raise UserError(
                _("Gemini error (%s): %s") % (resp.status_code, resp.text[:500])
            )
        data = resp.json()
        try:
            candidates = data.get("candidates") or []
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts)
        except (IndexError, AttributeError) as exc:
            raise UserError(
                _("Unexpected Gemini response:\n%s") % json.dumps(data)[:500]
            ) from exc

    def _call_openai_compatible(self, provider, system_prompt, user_query):
        """Any service that mirrors the OpenAI /chat/completions schema:
        DeepSeek, xAI Grok, Mistral, Groq, OpenRouter, local Ollama, etc."""
        url = (provider.base_url or "").strip()
        if not url:
            raise UserError(
                _("Set 'API Base URL' on this provider (the chat-completions "
                  "endpoint of the service).")
            )
        headers = {
            "Authorization": "Bearer %s" % provider.api_key.strip(),
            "Content-Type": "application/json",
        }
        payload = {
            "model": provider.model_name or "gpt-4o",
            "temperature": provider.temperature,
            "max_tokens": provider.max_tokens or 1024,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
            ],
        }
        resp = requests.post(
            url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
        )
        if resp.status_code != 200:
            raise UserError(
                _("Provider error (%s): %s") % (resp.status_code, resp.text[:500])
            )
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise UserError(
                _("Unexpected response shape:\n%s") % json.dumps(data)[:500]
            ) from exc

    # ------------------------------------------------------------------
    # Parsing & validation
    # ------------------------------------------------------------------
    def _extract_json(self, text):
        if not text:
            raise UserError(_("Empty response from AI provider."))
        text = text.strip()
        # Strip ```json ... ``` fences if present.
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text).strip()
            if text.endswith("```"):
                text = text[:-3].strip()
        # Keep the outermost JSON object.
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
        try:
            return json.loads(text)
        except (ValueError, TypeError) as exc:
            raise UserError(
                _("AI returned invalid JSON:\n%s") % text[:500]
            ) from exc

    def _validate_domain(self, model_name, domain):
        """Drop anything that is not a safe, known leaf or logical operator."""
        if not isinstance(domain, list):
            return []
        valid_fields = self.env[model_name].fields_get().keys()
        cleaned = []
        for item in domain:
            if isinstance(item, str):
                if item in DOMAIN_OPERATORS:
                    cleaned.append(item)
                continue
            if isinstance(item, (list, tuple)) and len(item) == 3:
                field = item[0]
                if not isinstance(field, str):
                    continue
                base = field.split(".")[0]  # allow dotted paths like partner_id.name
                if base in valid_fields:
                    cleaned.append((field, item[1], item[2]))
        return cleaned

    def _validate_groupby(self, model_name, group_by):
        if not isinstance(group_by, list):
            return []
        valid_fields = self.env[model_name].fields_get().keys()
        result = []
        for gb in group_by:
            if not isinstance(gb, str):
                continue
            base = gb.split(":")[0]  # allow date intervals like create_date:month
            if base in valid_fields:
                result.append(gb)
        return result

    def _split_provider_hint(self, user_query):
        """If the query starts with a recognised provider hint token
        ("gpt", "claude", "gemini", ... or the exact name of a configured
        provider) followed by whitespace, peel it off and return
        (hint, rest_of_query). Otherwise return (None, user_query) unchanged
        so normal queries are never affected.
        """
        if not user_query:
            return None, user_query
        parts = user_query.strip().split(None, 1)
        if not parts:
            return None, user_query
        first = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        if first in PROVIDER_ALIASES:
            return first, rest
        provider_names = {
            n.lower()
            for n in self.env["ai.provider"].search([("active", "=", True)]).mapped("name")
        }
        if first in provider_names:
            return first, rest
        return None, user_query

    # ------------------------------------------------------------------
    # Public entry point used by the controller
    # ------------------------------------------------------------------
    def process_query(self, model_name, user_query, provider_hint=None):
        if provider_hint:
            # Hint was already separated by the caller (e.g. controller
            # received it as its own parameter) -> query text is untouched.
            hint = provider_hint
            effective_query = user_query
        else:
            # Try to peel a hint token off the front of the raw text,
            # e.g. "claude sale orders this month" -> ("claude", "sale ...").
            hint, effective_query = self._split_provider_hint(user_query)
            if hint is None:
                effective_query = user_query

        provider = self.get_active_provider(hint)
        system_prompt = self.build_prompt(model_name, effective_query)
        raw = self._call_provider(provider, system_prompt, effective_query)
        parsed = self._extract_json(raw)

        domain = self._validate_domain(model_name, parsed.get("domain", []))
        group_by = self._validate_groupby(model_name, parsed.get("group_by", []))
        explanation = parsed.get("explanation") or _("AI filter applied.")

        return {
            "success": True,
            "domain": domain,
            "group_by": group_by,
            "explanation": explanation,
            "raw": raw,
            "provider_name": provider.name,
            "provider_type": provider.provider,
        }
