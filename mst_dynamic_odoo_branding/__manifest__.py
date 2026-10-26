{
    "name": "Dynamic Brand Identity Suite for Odoo",
    "summary": "Show your brand instead of Odoo in the browser tab, the login page and the URL",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "author": "MindSpark Technologies",
    "website": "https://mindsparktechnologies.com",
    "license": "LGPL-3",
    "depends": ["web", "mail"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/web_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # Placed right before Odoo's router: after the module loader (so
            # odoo.define exists) and evaluated before router.js reads the URL.
            ("before", "web/static/src/core/browser/router.js",
             "mst_dynamic_odoo_branding/static/src/js/url_prefix.js"),
            "mst_dynamic_odoo_branding/static/src/js/dynamic_title.js",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
    "application": True,
}
