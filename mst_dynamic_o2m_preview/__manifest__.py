{
    "name": "Dynamic One2Many Preview",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "summary": "Show One2Many records preview in list view",
    "description": """
        Dynamic One2Many Preview Widget for Odoo 19.
        Shows selected one2many line fields inside a compact table preview.
    """,
    "author": "Mind Spark Technologies",
    "depends": [
        "web",
        "sale",
    ],
    "assets": {
        "web.assets_backend": [
            "mst_dynamic_o2m_preview/static/src/js/dynamic_one2many_preview.js",
            "mst_dynamic_o2m_preview/static/src/xml/dynamic_one2many_preview.xml",
            "mst_dynamic_o2m_preview/static/src/css/dynamic_one2many_preview.css",
        ],
    },
    "data": [
        "views/sale_order_view.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}