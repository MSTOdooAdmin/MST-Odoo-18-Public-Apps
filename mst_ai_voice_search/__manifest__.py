{
    "name": "AI Voice Search",
    "summary": "Ask Odoo by voice: open menus, find, create, edit, archive, duplicate or delete records",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "MindSpark Technologies",
    "maintainer": "MindSpark Technologies",
    "website": "https://mindsparktechnologies.com",
    "license": "LGPL-3",
    "description": """
AI Voice Search
===============
A floating microphone on every backend screen. Speak or type a request:

* "Open invoices" / "Where is quotations" -> opens that menu
* "Show customers named Azure" / "Last 5 sales orders" -> lists matching records
* "How many draft quotations" -> answers with the count
* "Create sales order for Azure Interior with 5 desks", "Set phone of customer
  Azure Interior to 98765", "Rename product Desk to Office Desk", "Archive /
  restore / duplicate / delete ..." -> shown for confirmation, then done

* "Filter contacts where city is Chennai", "Group contacts by country",
  "Export customers" (Excel), "Import products" -> list, grouped list, file, import screen
* "Go to sales orders kanban view", "Show contacts in list" -> opens that view type
* "Go to Discuss configuration" (a menu with sub-menus) -> lists its screens to pick
* "Filter sales orders this month", "Invoices between 1 Oct and 10 Oct", "Contacts created
  yesterday" -> date filters on the right date field, in the user's time zone
* "Send message to Mitchell Admin saying the meeting is at 5" -> Discuss direct message
* "In channels, how many members in k channel", "List contacts of company Azure" -> related
  records of one record; "Open k channel", "Open customer Azure" -> opens that record
* Short forms: "tdy sale orders", "yday invoices", "this mnth"
* Replies follow the language selected in the voice panel: switching English / தமிழ்
  changes the replies, chat, spoken answers and panel wording immediately (Tamil works
  even when Tamil is not installed in Odoo)
* English and Tamil voice input (switch in the panel); replies in English by default
* "Create contact" -> the required fields are listed first, then the record is created

Every change is confirmed first (button or by saying "yes") and can be limited
in Settings (search only / changes / everything including delete).

Requests are understood with OpenAI or Google Gemini (optional, API key in
Settings) and with built-in keyword matching when no AI is configured or the AI
is unavailable. Every search runs as the logged-in user, read-only, so Odoo
access rights and record rules always apply.
    """,
    "depends": ["web", "base_import"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "mst_ai_voice_search/static/src/voice_search/voice_search.js",
            "mst_ai_voice_search/static/src/voice_search/voice_search.xml",
            "mst_ai_voice_search/static/src/voice_search/voice_search.scss",
        ],
    },
    'images': ['static/description/banner.png'],
    "installable": True,
    "application": False,
}
