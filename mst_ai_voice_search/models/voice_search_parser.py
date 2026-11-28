"""Keyword (no-AI) understanding of a voice/text request.

Pure Python, no database access: it works on a *catalog* built from the
current user's visible menus and accessible models, so it is fully testable.

Returned intent (same shape as the AI parser):
    {"action": "navigate", "menu_id": int}
    {"action": "search"|"count", "model": str, "domain": list,
     "limit": int, "order": str|None}
    {"action": "unknown"}
"""
import difflib
import re

NAVIGATE_RE = re.compile(
    r"^\s*(where\s+(is|are|can\s+i\s+find|do\s+i\s+find)|open|go\s+to|goto|navigate\s+to|navigate|"
    r"take\s+me\s+to|bring\s+me\s+to|show\s+me\s+the\s+menu|menu|launch)\b",
    re.I,
)
COUNT_RE = re.compile(r"\b(how\s+many|count|number\s+of|total\s+number)\b", re.I)
LAST_RE = re.compile(r"\b(last|latest|recent|newest)\b(?:\s+(\d{1,2}))?", re.I)
TOP_RE = re.compile(r"\b(top|first)\s+(\d{1,2})\b", re.I)
TERM_RE = re.compile(
    r"\b(?:named|called|name\s+is|with\s+name|containing|contains|matching|like|for|about|of|from)\s+"
    r"[\"']?(.+?)[\"']?\s*$",
    re.I,
)
MY_RE = re.compile(r"\b(my|mine|assigned\s+to\s+me)\b", re.I)

FILLER = {
    "show", "me", "list", "find", "search", "get", "display", "give", "all", "the", "a", "an",
    "please", "can", "you", "i", "want", "to", "see", "what", "are", "is", "there", "do", "we",
    "have", "of", "in", "my", "mine", "how", "many", "count", "number", "total", "last", "latest",
    "recent", "newest", "top", "first", "records", "record", "data", "and", "with", "which",
    "where", "open", "go", "menu", "take", "navigate", "launch", "find", "bring", "us",
}

# Spoken words -> technical models (used only when that model is in the user's catalog)
SYNONYMS = {
    "customer": "res.partner", "customers": "res.partner", "contact": "res.partner",
    "contacts": "res.partner", "partner": "res.partner", "partners": "res.partner",
    "vendor": "res.partner", "vendors": "res.partner", "supplier": "res.partner",
    "suppliers": "res.partner", "company": "res.partner", "companies": "res.partner",
    "invoice": "account.move", "invoices": "account.move", "bill": "account.move",
    "bills": "account.move",
    "quotation": "sale.order", "quotations": "sale.order", "sale": "sale.order",
    "sales": "sale.order", "order": "sale.order", "orders": "sale.order",
    "lead": "crm.lead", "leads": "crm.lead", "opportunity": "crm.lead",
    "opportunities": "crm.lead", "pipeline": "crm.lead",
    "product": "product.template", "products": "product.template",
    "task": "project.task", "tasks": "project.task", "project": "project.project",
    "projects": "project.project",
    "employee": "hr.employee", "employees": "hr.employee", "staff": "hr.employee",
    "purchase": "purchase.order", "purchases": "purchase.order", "rfq": "purchase.order",
    "rfqs": "purchase.order",
    "transfer": "stock.picking", "transfers": "stock.picking", "delivery": "stock.picking",
    "deliveries": "stock.picking", "receipt": "stock.picking", "receipts": "stock.picking",
    "user": "res.users", "users": "res.users",
    "payment": "account.payment", "payments": "account.payment",
    "ticket": "helpdesk.ticket", "tickets": "helpdesk.ticket",
    "meeting": "calendar.event", "meetings": "calendar.event",
    "channel": "discuss.channel", "channels": "discuss.channel",
}
# Multi-word phrases win over single words ("purchase orders" is not "sale.order")
PHRASES = {
    "purchase order": "purchase.order", "purchase orders": "purchase.order",
    "sales order": "sale.order", "sales orders": "sale.order", "sale order": "sale.order",
    "vendor bill": "account.move", "vendor bills": "account.move",
    "credit note": "account.move", "credit notes": "account.move",
}


def normalize(text):
    text = (text or "").lower().strip()
    text = re.sub(r"[?!.,;:]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _words(text):
    return [w for w in normalize(text).split() if w not in FILLER and len(w) > 1]


def _singular(word):
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def _similarity(query_words, target):
    """0..1 score between the spoken words and a menu path / model label."""
    target_words = [_singular(w) for w in normalize(target).replace("/", " ").split()]
    query_words = [_singular(w) for w in query_words]
    if not query_words or not target_words:
        return 0.0
    hits = 0.0
    for q in query_words:
        best = max(difflib.SequenceMatcher(None, q, t).ratio() for t in target_words)
        if best >= 0.82:
            hits += best
    coverage = hits / len(query_words)
    # prefer menus whose last part (the actual screen) is what was said
    leaf = [_singular(w) for w in normalize(target.split("/")[-1]).split()]
    leaf_bonus = 0.15 if any(q in leaf for q in query_words) else 0.0
    # exact match of the screen name ("Purchase Orders") beats a partial one
    exact_bonus = 0.1 if leaf == query_words else 0.0
    return min(coverage, 1.0) + leaf_bonus + exact_bonus


def match_menu(text, catalog, current_app_id=None):
    words = _words(NAVIGATE_RE.sub("", normalize(text)))
    best, best_score = None, 0.0
    for menu in catalog["menus"]:
        # menus without an action (folders such as "Discuss / Configuration") are matched
        # too: the engine then lists their sub-menus
        # shorter paths win ties ("Sales / Orders" over "Sales / Reporting / Orders")
        score = _similarity(words, menu["path"]) - 0.01 * menu["path"].count("/")
        # a real screen beats a folder that matches just as well
        if not menu.get("has_action"):
            score -= 0.05
        # how well the request names THIS menu: share of the menu's own words that were said,
        # and share of the request that is this menu's name ("users and companies" is the
        # folder "Users & Companies", not its sub-menu "Users")
        leaf = {_singular(w) for w in re.findall(r"\w+", normalize(menu["path"].split("/")[-1]))
                if w not in FILLER and len(w) > 1}
        said = {_singular(w) for w in words}
        if leaf and said:
            score += 0.2 * len(leaf & said) / len(leaf) + 0.2 * len(leaf & said) / len(said)
        # same name in several apps ("Customers"): prefer the app the user is in
        if current_app_id and menu.get("app_id") == current_app_id:
            score += 0.05
        if score > best_score:
            best, best_score = menu, score
    return best if best_score >= 0.5 else None


def match_model(text, catalog):
    ntext = normalize(text)
    models = catalog["models"]
    for phrase, model in PHRASES.items():
        if re.search(r"\b%s\b" % re.escape(phrase), ntext) and model in models:
            return model
    for word in ntext.split():
        model = SYNONYMS.get(word)
        if model and model in models:
            return model
    words = _words(ntext)
    best, best_score = None, 0.0
    for model, info in models.items():
        names = [info["label"]] + info.get("menu_names", [])
        score = max(_similarity(words, n) for n in names)
        if score > best_score:
            best, best_score = model, score
    return best if best_score >= 0.5 else None


def _model_words(model, info):
    words = set(normalize(info["label"]).split())
    for name in info.get("menu_names", []):
        words |= set(normalize(name).split())
    words |= {w for w, m in SYNONYMS.items() if m == model}
    for phrase, m in PHRASES.items():
        if m == model:
            words |= set(phrase.split())
    return words


def _search_term(text, model, info):
    """Text after 'named', 'called', 'for'... minus the model's own words.
    Also a reference right after the record type: "find sales order S00012"."""
    m = TERM_RE.search(normalize(text))
    if not m:
        ref = re.search(r"\b([a-z]{0,6}[/\-]?\d[\w/\-]*)\s*$", (text or "").strip().lower())
        if ref and not re.fullmatch(r"\d{1,2}", ref.group(1)):
            return ref.group(1)
        return None
    model_words = _model_words(model, info)
    state_words = set()
    for value, label in info.get("states") or []:
        state_words |= set(normalize(label).split()) | {normalize(value)}
    words = [w for w in m.group(1).split()
             if w not in model_words and w not in FILLER and w not in state_words]
    return " ".join(words).strip() or None


def _state_filter(text, model, info):
    ntext = " %s " % normalize(text)
    model_words = {_singular(w) for w in _model_words(model, info)}
    for value, label in info.get("states") or []:
        # a status named like the model itself ("Purchase Order", "Sales Order",
        # "Quotation") is the record type, not a filter
        if {_singular(w) for w in normalize(label).split()} <= model_words:
            continue
        for candidate in {normalize(label), normalize(value).replace("_", " ")}:
            if candidate and " %s " % candidate in ntext:
                return value
    return None


def keyword_parse(text, catalog, max_results=10, current_app_id=None):
    ntext = normalize(text)
    if not ntext:
        return {"action": "unknown"}

    # Tamil (or Tamil + English) -> English keywords, then the usual rules
    text = translate_tamil(text)
    message = parse_message(text)  # before anything else: the body may contain any words
    if message:
        return message
    text = expand_abbreviations(text)          # "tdy sale orders" -> "today sale orders"
    text, context_model = split_context(text, catalog)   # "In channels, ..." -> model hint
    related = parse_related(text, catalog, context_model)
    if related:
        # if the relation is not a field of the record, the engine uses the normal answer
        related["fallback"] = _keyword_parse(text, catalog, max_results, current_app_id, context_model)
        return related
    text, view_type = extract_view_type(text)
    text, date_condition = extract_date_condition(text)
    result = _keyword_parse(text, catalog, max_results, current_app_id, context_model)
    if date_condition and result.get("action") in ("search", "count", "filter", "export", "group"):
        result.setdefault("conditions", [])
        result["conditions"] = list(result["conditions"]) + [date_condition]
    if view_type and result.get("action") in ("navigate", "search", "count", "filter", "group", "unknown"):
        result["view_type"] = view_type
        if result["action"] in ("search", "count"):
            # "show sales orders in kanban" = open the list screen in that view
            result["action"] = "filter"
            result.setdefault("conditions", [])
    return result


def _keyword_parse(text, catalog, max_results=10, current_app_id=None, context_model=None):
    ntext = normalize(text)
    spec = parse_list_action(text, catalog) or parse_action(text, catalog)  # names/values keep their case
    if spec:
        return spec

    if NAVIGATE_RE.search(ntext):
        menu = match_menu(ntext, catalog, current_app_id)
        record = parse_open_record(text, catalog, context_model)
        if record:
            # "open k channel": open that record if it exists, else the menu
            return dict(record, action="navigate", menu_id=menu["id"] if menu else False)
        if menu:
            return {"action": "navigate", "menu_id": menu["id"]}

    model = match_model(ntext, catalog)
    if not model:
        # a bare menu name ("inventory", "sales reporting") -> open that menu
        menu = match_menu(ntext, catalog, current_app_id)
        if menu:
            return {"action": "navigate", "menu_id": menu["id"]}
        return {"action": "unknown"}

    info = catalog["models"][model]
    domain = []
    state = _state_filter(ntext, model, info)
    if state:
        domain.append(["state", "=", state])
    if MY_RE.search(ntext) and info.get("user_field"):
        domain.append([info["user_field"], "=", catalog["uid"]])
    term = _search_term(ntext, model, info)
    if term:
        domain.append(["display_name", "ilike", term])

    limit, order = max_results, None
    last = LAST_RE.search(ntext)
    top = TOP_RE.search(ntext)
    if last:
        order = "id desc"
        if last.group(2):
            limit = max(1, min(int(last.group(2)), max_results))
    elif top:
        limit = max(1, min(int(top.group(2)), max_results))

    action = "count" if COUNT_RE.search(ntext) else "search"
    return {"action": action, "model": model, "domain": domain, "limit": limit, "order": order}


# ----------------------------------------------------------------------
# Voice actions: create / edit / delete / archive / unarchive / duplicate
# ----------------------------------------------------------------------
WORD_NUMBERS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "fifteen": 15, "twenty": 20, "fifty": 50, "hundred": 100,
}
_PLEASE = r"^(?:please\s+|can\s+you\s+|could\s+you\s+|i\s+want\s+to\s+|kindly\s+)?"
ACTION_PATTERNS = [
    # "make customer X inactive" / "set X as active" (verb at start, state at end)
    ("archive", re.compile(_PLEASE + r"(?:make|set|mark)\b.*\b(?:inactive|archived)$", re.I)),
    ("unarchive", re.compile(_PLEASE + r"(?:make|set|mark)\b.*\b(?:active|unarchived)$", re.I)),
    ("archive", re.compile(_PLEASE + r"(?:archive|deactivate|disable|inactivate)\b", re.I)),
    ("unarchive", re.compile(_PLEASE + r"(?:unarchive|restore|reactivate|activate|enable)\b", re.I)),
    ("delete", re.compile(_PLEASE + r"(?:delete|remove|erase)\b", re.I)),
    ("duplicate", re.compile(_PLEASE + r"(?:duplicate|copy|clone)\b", re.I)),
    ("create", re.compile(_PLEASE + r"(?:create|add|make|register|new|open\s+a\s+new|open\s+new|start\s+a\s+new)\b", re.I)),
    ("write", re.compile(_PLEASE + r"(?:rename|change|set|update|edit|modify)\b", re.I)),
]
LEADING_VERB_RE = re.compile(
    _PLEASE + r"(?:make|set|mark|archive|deactivate|disable|inactivate|unarchive|restore|reactivate|activate|"
    r"enable|delete|remove|erase|duplicate|copy|clone|create|add|register|open\s+a\s+new|open\s+new|"
    r"start\s+a\s+new|new|rename|change|update|edit|modify)\b\s*",
    re.I,
)
TRAILING_STATE_RE = re.compile(r"\s*\b(?:as\s+)?(?:inactive|active|archived|unarchived)$", re.I)
RECORD_FILLER_RE = re.compile(r"^(?:a|an|the|new|record|number|no|named|called|with\s+name|for|of|#)\b\s*", re.I)


def _model_spans(model, info):
    """Every phrase that can name this model, longest first."""
    names = {normalize(info["label"])}
    names |= {normalize(n) for n in info.get("menu_names", [])}
    names |= {w for w, m in SYNONYMS.items() if m == model}
    names |= {p for p, m in PHRASES.items() if m == model}
    return sorted((n for n in names if n), key=len, reverse=True)


def find_model_span(text, catalog):
    """Return (model, start, end) of the model words inside ``text`` (case-insensitive)."""
    low = text.lower()
    best = None
    for model, info in catalog["models"].items():
        for name in _model_spans(model, info):
            for variant in {name, name + "s", name[:-1] if name.endswith("s") else name}:
                m = re.search(r"\b%s\b" % re.escape(variant), low)
                if m and (best is None or (m.start(), -(m.end() - m.start())) < (best[1], -(best[2] - best[1]))):
                    best = (model, m.start(), m.end())
    return best


def _clean_record_term(term):
    """Strip leading filler words, keeping the user's own case and punctuation."""
    term = (term or "").strip(" ,")
    previous = None
    while previous != term:
        previous = term
        term = RECORD_FILLER_RE.sub("", term).strip(" ,")
    return term or None


def _parse_lines(text):
    """'5 desks and 2 office chairs' -> [(5, 'desks'), (2, 'office chairs')]"""
    lines = []
    for chunk in re.split(r"\s*(?:,|\band\b|\bplus\b)\s*", text, flags=re.I):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = re.match(r"^(\d+(?:\.\d+)?|%s)\s+(?:units?\s+of\s+|pieces?\s+of\s+|x\s+|of\s+)?(.+)$"
                     % "|".join(WORD_NUMBERS), chunk, re.I)
        if m:
            qty = WORD_NUMBERS.get(m.group(1).lower()) or float(m.group(1))
            lines.append((qty, m.group(2).strip()))
        else:
            lines.append((1, chunk))
    return [(qty, name) for qty, name in lines if name]


def _rfind_ci(text, sep):
    return text.lower().rfind(sep)


def parse_action(text, catalog):
    """Return a raw action spec, or None if ``text`` is not an action command.

    Detection is case-insensitive; names and values keep the user's own case
    and punctuation ("Office Desk", "info@deco.com").
    """
    orig = re.sub(r"\s+", " ", (text or "").strip()).rstrip("?! ")
    if orig.endswith(".") and not re.search(r"\.\w+\.$", orig):
        orig = orig[:-1]
    action = next((name for name, pattern in ACTION_PATTERNS if pattern.search(orig)), None)
    if not action:
        return None
    first_word = orig.split(" ", 1)[0].lower()
    rest = LEADING_VERB_RE.sub("", orig, count=1).strip()
    if action in ("archive", "unarchive"):
        rest = TRAILING_STATE_RE.sub("", rest).strip()

    if action == "write":
        is_rename = first_word == "rename"
        sep = " to " if " to " in rest.lower() else (" as " if " as " in rest.lower() else None)
        if not sep:
            return {"action": "write", "error": "missing_value"}
        cut = _rfind_ci(rest, sep)
        left, value = rest[:cut], rest[cut + len(sep):]
        field_text = None
        of_at = left.lower().find(" of ")
        if not is_rename and of_at >= 0:
            field_text, left = _clean_record_term(left[:of_at]), left[of_at + 4:]
        span = find_model_span(left, catalog)
        if not span:
            return {"action": "write", "error": "no_model"}
        model, start, end = span
        if field_text is None and not is_rename and start > 0:
            field_text = _clean_record_term(left[:start])
        return {
            "action": "write",
            "model": model,
            "target": _clean_record_term(left[end:]),
            "field": "__name__" if is_rename else field_text,
            "value": value.strip(),
        }

    span = find_model_span(rest, catalog)
    if not span:
        return {"action": action, "error": "no_model"}
    model, start, end = span
    after = rest[end:].strip()

    if action == "create":
        lines = []
        with_at = (" %s " % after).lower().find(" with ")
        if with_at >= 0:
            padded = " %s " % after
            after, lines = padded[:with_at].strip(), _parse_lines(padded[with_at + 6:].strip())
        return {"action": "create", "model": model, "name": _clean_record_term(after), "lines": lines}

    return {"action": action, "model": model, "record": _clean_record_term(after) or _clean_record_term(rest[:start])}


# ----------------------------------------------------------------------
# Tamil -> English keywords (keyword mode; AI mode understands Tamil itself)
# ----------------------------------------------------------------------
TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")
TAMIL_WORDS = {
    # verbs
    "திற": "open", "திறக்க": "open", "திறந்து": "open", "திறக்கவும்": "open", "செல்": "go to", "போ": "go to",
    "காட்டு": "show", "காட்டவும்": "show", "காண்பி": "show", "காண்பிக்கவும்": "show", "பட்டியலிடு": "list",
    "தேடு": "search", "தேடவும்": "search", "கண்டுபிடி": "find",
    "எத்தனை": "how many", "எண்ணிக்கை": "count",
    "உருவாக்கு": "create", "உருவாக்கவும்": "create", "சேர்": "add", "சேர்க்கவும்": "add",
    "நீக்கு": "delete", "நீக்கவும்": "delete", "அழி": "delete",
    "நகலெடு": "duplicate", "நகல்": "duplicate", "காப்பகப்படுத்து": "archive", "மீட்டெடு": "restore",
    "திருத்து": "edit", "மாற்று": "change",
    "வடிகட்டு": "filter", "வடிகட்டவும்": "filter", "குழுவாக்கு": "group", "குழுவாக": "group",
    "ஏற்றுமதி": "export", "பதிவிறக்கு": "download", "இறக்குமதி": "import", "பதிவேற்று": "upload",
    # records
    "வாடிக்கையாளர்": "customers", "தொடர்பு": "contacts", "பொருள்": "products", "பொருட்": "products",
    "தயாரிப்பு": "products", "விலைப்பட்டியல்": "invoices", "பில்": "bills", "விற்பனை": "sales",
    "ஆணை": "orders", "ஆர்டர்": "orders", "கொள்முதல்": "purchase", "பணியாளர்": "employees",
    "ஊழியர்": "employees", "பயனர்": "users", "நிறுவனம்": "companies",
    # modifiers
    "புதிய": "new", "பெயர்": "named", "பெயருடன்": "named", "என்ற": "named",
    "எனது": "my", "என்னுடைய": "my", "கடைசி": "last", "சமீபத்திய": "latest",
    "மூலம்": "by", "வாரியாக": "by", "நாடு": "country", "நகரம்": "city", "நிலை": "state",
    "மற்றும்": "and", "உடன்": "with",
    # answers
    "ஆம்": "yes", "சரி": "ok", "இல்லை": "no", "வேண்டாம்": "cancel",
}
TAMIL_SUFFIXES = ("களை", "கள்", "களின்", "யை", "வை", "க்கு", "ுக்கு", "இல்", "ில்", "ின்", "ஐ", "ை")
LEADING_VERBS = {"open", "go to", "show", "list", "search", "find", "how many", "count", "create", "add",
                 "delete", "duplicate", "archive", "restore", "edit", "change", "filter", "group",
                 "export", "download", "import", "upload"}


def _tamil_word(word):
    if word in TAMIL_WORDS:
        return TAMIL_WORDS[word]
    for suffix in TAMIL_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix) + 1:
            stem = word[: -len(suffix)]
            if stem in TAMIL_WORDS:
                return TAMIL_WORDS[stem]
    return None


def translate_tamil(text):
    """Map Tamil command words to English and move a trailing verb to the front
    (Tamil puts the verb last: "வாடிக்கையாளர்களை காட்டு" -> "show customers").
    Words not in the list (names, references) are kept unchanged."""
    if not text or not TAMIL_RE.search(text):
        return text
    out = []
    for word in text.split():
        english = _tamil_word(word.strip(",.?!"))
        out.append(english if english else word)
    if len(out) > 1 and out[-1] in LEADING_VERBS:
        verb = out.pop()
        if verb == "group":
            # "நாடு வாரியாக வாடிக்கையாளர்களை குழுவாக்கு" -> "group customers by country"
            text_out = " ".join(out)
            m = re.match(r"^(.*?)\bby\b\s*(.*)$", text_out)
            return "group %s by %s" % (m.group(2), m.group(1).strip()) if m else "group " + text_out
        out.insert(0, verb)
    return " ".join(out)


# ----------------------------------------------------------------------
# Filter / group by / export / import
# ----------------------------------------------------------------------
FILTER_RE = re.compile(r"^(?:please\s+)?(?:filter|show\s+only|only\s+show)\b", re.I)
GROUP_RE = re.compile(r"\bgroup(?:ed)?\b", re.I)
EXPORT_RE = re.compile(r"^(?:please\s+)?(?:export|download)\b", re.I)
IMPORT_RE = re.compile(r"^(?:please\s+)?(?:import|upload)\b", re.I)
CONDITION_START_RE = re.compile(r"\b(?:by|where|with|whose|having)\b\s+(.+)$", re.I)


def _base_domain(text, model, info, catalog):
    """State / 'my' / name filters already understood by keyword search."""
    domain = []
    state = _state_filter(text, model, info)
    if state:
        domain.append(["state", "=", state])
    if MY_RE.search(text) and info.get("user_field"):
        domain.append([info["user_field"], "=", catalog["uid"]])
    term = _search_term(text, model, info)
    if term:
        domain.append(["display_name", "ilike", term])
    return domain


def parse_list_action(text, catalog):
    """filter / group / export / import -> raw spec, or None."""
    orig = re.sub(r"\s+", " ", (text or "").strip()).rstrip("?!. ")
    low = orig.lower()

    if IMPORT_RE.search(low):
        span = find_model_span(low, catalog)
        return {"action": "import", "model": span[0]} if span else {"action": "import", "error": "no_model"}

    if EXPORT_RE.search(low):
        span = find_model_span(low, catalog)
        if not span:
            return {"action": "export", "error": "no_model"}
        model = span[0]
        rest = low[span[2]:]
        conditions = []
        cm = CONDITION_START_RE.search(rest)
        if cm:
            conditions = [c.strip() for c in re.split(r"\s+and\s+", orig[span[2]:][cm.start(1):]) if c.strip()]
        # filters can come before the model ("export posted invoices") or after it
        head = low[: span[2]] + " " + (rest if not cm else rest[: cm.start()])
        return {"action": "export", "model": model,
                "domain": _base_domain(normalize(EXPORT_RE.sub("", head)), model, catalog["models"][model], catalog),
                "conditions": conditions}

    if GROUP_RE.search(low) and re.search(r"\bby\b", low):
        # "group sales orders by customer" / "show contacts grouped by country"
        before, _sep, after = low.rpartition(" by ")
        span = find_model_span(before, catalog)
        if not span or not after.strip():
            return {"action": "group", "error": "no_model" if not span else "no_field"}
        return {"action": "group", "model": span[0], "group_field": orig[len(before) + 4:].strip(),
                "domain": _base_domain(normalize(GROUP_RE.sub("", before)), span[0],
                                       catalog["models"][span[0]], catalog)}

    if FILTER_RE.search(low):
        span = find_model_span(low, catalog)
        if not span:
            return {"action": "filter", "error": "no_model"}
        model = span[0]
        rest_orig = orig[span[2]:]
        cm = CONDITION_START_RE.search(rest_orig)
        conditions = []
        head = rest_orig
        if cm:
            head = rest_orig[: cm.start()]
            conditions = [c.strip() for c in re.split(r"\s+and\s+", cm.group(1), flags=re.I) if c.strip()]
        domain = _base_domain(normalize(low[: span[2]] + " " + head.lower()), model, catalog["models"][model], catalog)
        return {"action": "filter", "model": model, "domain": domain, "conditions": conditions}
    return None


# ----------------------------------------------------------------------
# View types: "go to sales orders kanban view", "show contacts in list"
# ----------------------------------------------------------------------
VIEW_ALIASES = {"tree": "list", "chart": "graph", "graphs": "graph", "table": "list", "cards": "kanban"}
# words that can only mean a view type
_ONLY_VIEW = r"kanban|pivot|gantt|cohort"
# words that are also ordinary words: need "view" after, or "in"/"as" before
_MAYBE_VIEW = r"list|tree|form|calendar|graph|chart|activity|map|table|cards"
VIEW_RE = re.compile(
    r"\s*\b(?:(?:in|as|on)\s+(?:a\s+|the\s+)?(?P<a>%(only)s|%(maybe)s)(?:\s+views?)?"
    r"|(?P<b>%(maybe)s)\s+views?"
    r"|(?P<c>%(only)s)(?:\s+views?)?)\b" % {"only": _ONLY_VIEW, "maybe": _MAYBE_VIEW},
    re.I,
)


def extract_view_type(text):
    """Return (text without the view words, view type or None)."""
    m = VIEW_RE.search(text or "")
    if not m:
        return text, None
    word = (m.group("a") or m.group("b") or m.group("c")).lower()
    view = VIEW_ALIASES.get(word, word)
    cleaned = (text[: m.start()] + " " + text[m.end():]).strip()
    return re.sub(r"\s+", " ", cleaned), view


# ----------------------------------------------------------------------
# Dates: "this month", "last 7 days", "between 1 Oct and 10 Oct", "created yesterday"
# ----------------------------------------------------------------------
import calendar as _calendar  # noqa: E402
from datetime import date as _date, timedelta as _timedelta  # noqa: E402

_MONTHS = {m.lower(): i for i, m in enumerate(_calendar.month_name) if m}
_MONTHS.update({m.lower(): i for i, m in enumerate(_calendar.month_abbr) if m})
_MONTHS["sept"] = 9
_MON = r"(?:%s)" % "|".join(sorted((m for m in _MONTHS if m != "may"), key=len, reverse=True) + ["may"])
_DAY = r"(?:\d{1,2})(?:st|nd|rd|th)?"
DATE_TOKEN = (r"(?:\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}|today|yesterday|tomorrow"
              r"|%(d)s\s+(?:of\s+)?%(m)s(?:,?\s+\d{4})?|%(m)s\s+%(d)s(?:,?\s+\d{4})?)" % {"d": _DAY, "m": _MON})
_PERIOD = r"(?:this|last|next|previous|current|past)\s+(?:week|month|quarter|year)"
_ROLLING = r"(?:last|past|previous|next)\s+\d{1,3}\s+(?:days?|weeks?|months?)"
DATE_PHRASE = (r"(?:between|from)\s+%(t)s\s+(?:and|to|till|until)\s+%(t)s"
               r"|(?:before|until|till|after|since)\s+%(t)s"
               r"|%(rolling)s|%(period)s"
               r"|(?:on\s+)?%(t)s"
               r"|(?:in\s+|during\s+)?%(m)s(?:\s+\d{4})?") % {"t": DATE_TOKEN, "m": _MON, "period": _PERIOD,
                                                              "rolling": _ROLLING}
# optional date-field words just before the phrase: "created", "order date", "due date"...
DATE_FIELD_WORDS = r"(?:(?:created|creation|updated|modified|order|invoice|delivery|due|expiry|expiration|deadline|scheduled|confirmation|payment|accounting)\s+)?(?:date\s+|on\s+)?"
DATE_EXTRACT_RE = re.compile(
    r"\b(?P<field>(?:created|updated|modified)\b|(?:(?:creation|order|invoice|delivery|due|expiry|expiration|deadline|scheduled|confirmation|payment|accounting)\s+)?date\b)?"
    r"\s*(?:(?:is|was|of|in|on|for|from|during|by|=)\s+)?"
    r"(?P<phrase>%s)\b" % DATE_PHRASE,
    re.I,
)
_LEAD_CONNECTOR_RE = re.compile(r"\s+(?:by|with|where|whose|having|for|from|of|in|on|dated)\s*$", re.I)


def extract_date_condition(text):
    """Return (text without the date words, "<field words> | <phrase>" or None)."""
    m = DATE_EXTRACT_RE.search(text or "")
    if not m:
        return text, None
    # "may" alone is too common a word: only as "in may" / "may 2026"
    if m.group("phrase").strip().lower() == "may":
        return text, None
    before = _LEAD_CONNECTOR_RE.sub("", text[: m.start()])
    cleaned = re.sub(r"\s+", " ", (before + " " + text[m.end():]).strip())
    return cleaned, "%s | %s" % ((m.group("field") or "").strip().lower(), m.group("phrase").strip().lower())


def _parse_token(token, today):
    token = token.strip().lower()
    rel = {"today": 0, "yesterday": -1, "tomorrow": 1}
    if token in rel:
        return today + _timedelta(days=rel[token])
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", token)
    if m:
        return _date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"^(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})$", token)
    if m:  # day first (India / Europe)
        year = int(m.group(3)) + (2000 if len(m.group(3)) == 2 else 0)
        return _date(year, int(m.group(2)), int(m.group(1)))
    words = re.findall(r"[a-z]+|\d+", token)
    day = month = year = None
    for w in words:
        if w in _MONTHS:
            month = _MONTHS[w]
        elif w.isdigit() and len(w) == 4:
            year = int(w)
        elif w.isdigit():
            day = int(w)
    if month and day:
        return _date(year or today.year, month, day)
    raise ValueError(token)


def _month_bounds(year, month):
    return _date(year, month, 1), _date(year, month, _calendar.monthrange(year, month)[1])


def date_range(phrase, today):
    """'last month' -> (start, end) inclusive; open ends are None. Raises ValueError."""
    p = re.sub(r"\s+", " ", phrase.strip().lower())
    p = re.sub(r"^(?:on|in|during)\s+", "", p)
    m = re.match(r"^(?:between|from) (.+?) (?:and|to|till|until) (.+)$", p)
    if m:
        a, b = _parse_token(m.group(1), today), _parse_token(m.group(2), today)
        return (a, b) if a <= b else (b, a)
    m = re.match(r"^(before|until|till|after|since) (.+)$", p)
    if m:
        d = _parse_token(m.group(2), today)
        return (None, d - _timedelta(days=1)) if m.group(1) == "before" else \
            ((None, d) if m.group(1) in ("until", "till") else
             ((d + _timedelta(days=1), None) if m.group(1) == "after" else (d, None)))
    m = re.match(r"^(last|past|previous|next) (\d{1,3}) (day|week|month)s?$", p)
    if m:
        n = int(m.group(2)) * {"day": 1, "week": 7, "month": 30}[m.group(3)]
        return (today - _timedelta(days=n - 1), today) if m.group(1) != "next" else (today, today + _timedelta(days=n - 1))
    m = re.match(r"^(this|last|next|previous|current|past) (week|month|quarter|year)$", p)
    if m:
        shift = {"last": -1, "previous": -1, "past": -1, "next": 1}.get(m.group(1), 0)
        unit = m.group(2)
        if unit == "week":
            start = today - _timedelta(days=today.weekday()) + _timedelta(weeks=shift)
            return start, start + _timedelta(days=6)
        if unit == "month":
            month_index = today.year * 12 + today.month - 1 + shift
            return _month_bounds(month_index // 12, month_index % 12 + 1)
        if unit == "quarter":
            q = (today.month - 1) // 3 + shift
            year = today.year + q // 4
            q %= 4
            return _date(year, q * 3 + 1, 1), _month_bounds(year, q * 3 + 3)[1]
        return _date(today.year + shift, 1, 1), _date(today.year + shift, 12, 31)
    m = re.match(r"^(%s)(?: (\d{4}))?$" % _MON, p)
    if m and not re.search(r"\d{1,2}(?:st|nd|rd|th)?\s", p):
        return _month_bounds(int(m.group(2) or today.year), _MONTHS[m.group(1)])
    d = _parse_token(p, today)
    return d, d


# ----------------------------------------------------------------------
# Messages: "send message to Mitchell Admin saying the meeting is at 5"
# ----------------------------------------------------------------------
MESSAGE_RES = [
    re.compile(r"^(?:please\s+)?(?:send|write)\s+(?:a\s+)?(?:message|msg|chat|note)\s+to\s+(?P<to>.+?)\s*"
               r"(?:saying|that says|that|telling|:|,|with the message|with message|message)\s+(?P<body>.+)$", re.I),
    re.compile(r"^(?:please\s+)?(?:message|msg|ping|chat\s+with|tell)\s+(?P<to>.+?)\s*(?:saying|that|:|,)\s+(?P<body>.+)$", re.I),
    re.compile(r"^(?:please\s+)?(?:send|write)\s+(?P<body>.+?)\s+to\s+(?P<to>[^ ]+(?:\s+[^ ]+)?)\s+(?:as a message|in chat|on chat)$", re.I),
]


def parse_message(text):
    orig = re.sub(r"\s+", " ", (text or "").strip())
    for pattern in MESSAGE_RES:
        m = pattern.match(orig)
        if m:
            to = re.sub(r"^(?:the\s+user\s+|user\s+|my\s+colleague\s+)", "", m.group("to").strip(" ,:"), flags=re.I)
            body = m.group("body").strip().strip("\"'“”")
            if to and body:
                return {"action": "message", "recipient": to, "body": body}
    if re.match(r"^(?:please\s+)?(?:send|write)\s+(?:a\s+)?(?:message|msg|chat)\b", orig, re.I):
        return {"action": "message", "error": "incomplete"}
    return None


# ----------------------------------------------------------------------
# Short forms: "tdy sale orders", "yday invoices", "this mnth"
# ----------------------------------------------------------------------
ABBREVIATIONS = {
    "tdy": "today", "tday": "today", "2day": "today", "yday": "yesterday", "yest": "yesterday",
    "ystrdy": "yesterday", "tmrw": "tomorrow", "tmr": "tomorrow", "tmrow": "tomorrow", "2morrow": "tomorrow",
    "mnth": "month", "mth": "month", "wk": "week", "yr": "year", "inv": "invoices", "invs": "invoices",
    "po": "purchase orders", "pos": "purchase orders", "qtn": "quotations", "qtns": "quotations",
    "cust": "customers", "custs": "customers", "prod": "products", "prods": "products",
    "msg": "message", "pls": "please", "plz": "please", "chnl": "channel", "chnls": "channels",
}


def expand_abbreviations(text):
    """Only lower-case words: short forms are typed in lower case ("tdy"), while names keep
    their capitals ("Tdy Customer", "Po Ling") and must not be changed."""
    words = (text or "").split()
    return " ".join(ABBREVIATIONS.get(w.strip(",.?!"), w) if w.islower() else w for w in words)


# ----------------------------------------------------------------------
# Related records: "how many members in k channel", "list members of k channel"
# and a leading context: "In channels, how many members in k"
# ----------------------------------------------------------------------
CONTEXT_RE = re.compile(r"^\s*(?:in|inside|within|under|from)\s+(?P<ctx>[^,]+?)\s*,\s*(?P<rest>.+)$", re.I)
REL_COUNT_RE = re.compile(
    r"^(?:how\s+many|count(?:\s+the)?|number\s+of|total\s+number\s+of)\s+(?P<rel>.+?)\s+(?:are\s+|is\s+)?"
    r"(?:in|of|on|inside|for|within)\s+(?:the\s+)?(?P<target>.+?)(?:\s+(?:has|have|contains?|got))?$", re.I)
REL_LIST_RE = re.compile(
    r"^(?:list|show|display|get|give\s+me|who\s+are|which\s+are|what\s+are)(?:\s+(?:me|all|the|of))*\s+"
    r"(?P<rel>.+?)\s+(?:in|of|on|inside|for|from|within)\s+(?:the\s+)?(?P<target>.+)$", re.I)
_RECORD_TRAIL_RE = re.compile(r"^(?:the|a|an|named|called|in|of|on|my)\s+|\s+(?:in|of|on|the|named|called)$", re.I)


def split_context(text, catalog):
    """'In channels, how many members in k' -> ('how many members in k', 'discuss.channel')."""
    m = CONTEXT_RE.match(text or "")
    if not m:
        return text, None
    span = find_model_span(m.group("ctx"), catalog)
    if not span:
        return text, None
    return m.group("rest"), span[0]


def _record_and_model(target, catalog, context_model=None):
    """'k channel' / 'channel k' / 'k' (+ context) -> (model, record name) or (None, None)."""
    span = find_model_span(target, catalog)
    if span:
        model, start, end = span
        record = (target[:start] + " " + target[end:]).strip()
    elif context_model:
        model, record = context_model, target.strip()
    else:
        return None, None
    previous = None
    while previous != record:
        previous = record
        record = _RECORD_TRAIL_RE.sub("", record).strip(" ,")
    return (model, record) if record else (None, None)


def parse_related(text, catalog, context_model=None):
    for mode, pattern in (("count", REL_COUNT_RE), ("list", REL_LIST_RE)):
        m = pattern.match((text or "").strip().rstrip("?!. "))
        if not m:
            continue
        model, record = _record_and_model(m.group("target"), catalog, context_model)
        if model and record:
            return {"action": "related", "mode": mode, "model": model, "record": record,
                    "relation": m.group("rel").strip()}
    return None


def parse_open_record(text, catalog, context_model=None):
    """'open k channel' / 'open k in channel' / 'open channel k' -> record to open (or None)."""
    m = NAVIGATE_RE.search(text or "")
    if not m:
        return None
    rest = (text[: m.start()] + " " + text[m.end():]).strip()
    model, record = _record_and_model(rest, catalog, context_model)
    if not model or not record or len(record) > 80:
        return None
    return {"record_model": model, "record": record}
