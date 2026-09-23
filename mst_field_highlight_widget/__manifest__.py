{
    "name": "Field Highlight Widget",
    "summary": "Developer-only field highlight widget controlled from XML options",
    "version": "19.0.1.0.0",
    "description": """
        Field Highlight Widget
        ======================
        A lightweight developer tool that highlights important fields in Odoo views,
        configured directly from the view XML through widget options.
        
        Key Features
        ------------
        * Highlight any supported field in Form, List and Kanban views
        * Configure colours and highlight style from XML ``options``
        * No Python models, menus or configuration screens: nothing to set up for end users
        * Works with standard and custom models through view inheritance
        * Lightweight OWL frontend widget loaded in the backend assets only
        * Compatible with Odoo 19 Community and Enterprise
        
        Usage
        -----
        Add the widget to a field in your view XML and set its highlight options::
        
            <field name="your_field" widget="field_highlight" options="{...}"/>
        
        Intended For
        ------------
        Developers and functional consultants who want to draw attention to key
        fields, such as status, amounts, deadlines or warnings, without writing
        custom CSS or JavaScript for each view.
    """,
    "category": "Tools",
    'website': 'https://mindsparktechnologies.com',
    'maintainer': 'MindSpark Technologies',
    'author': 'MindSpark Technologies',
    "license": "LGPL-3",
    "depends": ["web"],
    "data": [],
    "assets": {
        "web.assets_backend": [
            "mst_field_highlight_widget/static/src/js/field_highlight_widget.js",
            "mst_field_highlight_widget/static/src/xml/field_highlight_widget.xml",
            "mst_field_highlight_widget/static/src/scss/field_highlight_widget.scss",
        ],
    },
    "images": [
        "static/description/banner.jpg",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
