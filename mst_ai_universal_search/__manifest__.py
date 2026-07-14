# -*- coding: utf-8 -*-
{
    "name": "AI Universal Search",

    "summary": """
        AI-powered natural language search using OpenAI ChatGPT and Claude AI.
    """,

    "description": """
        AI Universal Search
        ======================================

        AI Universal Search enables users to search Odoo records using
        natural language directly from the standard Odoo search bar.

        Simply type your search query with the prefix "ai:" and the module
        intelligently converts your request into an Odoo search domain using
        OpenAI ChatGPT or Anthropic Claude AI.

        The module integrates seamlessly with the native Odoo search,
        allowing users to search records without manually creating filters
        or advanced search domains.

        Keywords
        ============
        • AI Search
        • OpenAI ChatGPT
        • Claude AI
        • Anthropic Claude
        • Natural Language Search
        • Smart Search
        • Odoo AI
        • AI Assistant
        • AI Domain Generator
        • Odoo Search Bar
        • Intelligent Search
        • Search Automation
        • HR AI Search
        • CRM AI Search

        Key Features
        ============
        ✔ Natural language search using "ai:" prefix
        ✔ Powered by OpenAI ChatGPT
        ✔ Powered by Anthropic Claude AI
        ✔ Works in all Odoo list views
        ✔ Intelligent Odoo domain generation
        ✔ Automatic filter generation
        ✔ AI-powered search suggestions
        ✔ Search History Management
        ✔ Easy AI Provider Configuration
        ✔ Secure API Key Management
        ✔ Fast and responsive search
        ✔ Native Odoo search bar integration
        ✔ No changes to existing Odoo search functionality
        ✔ Supports multiple business modules
        ✔ Fully compatible with Odoo 18

        Supported Applications
        ======================
        ✔ Employees
        ✔ Attendance
        ✔ Leave
        ✔ Payroll
        ✔ Recruitment
        ✔ CRM
        ✔ Sales
        ✔ Purchase
        ✔ Inventory
        ✔ Accounting
        ✔ Manufacturing
        ✔ Projects
        ✔ Helpdesk
        ✔ Contacts
        ✔ Custom Modules

        Example Queries
        ===============
        • ai: employees who joined this month
        • ai: attendance below 80%
        • ai: sales orders above 100000
        • ai: overdue customer invoices
        • ai: products with low stock
        • ai: purchase orders pending approval
        • ai: leave requests awaiting manager approval
        • ai: customers from Chennai
        • ai: projects completed this month
        • ai: group employees by department

        Workflow
        ========
        • Configure OpenAI and/or Claude API Key
        • Open any Odoo list view
        • Type a query beginning with "ai:"
        • AI converts the request into an Odoo domain
        • Records are filtered automatically
        • Search history is saved
        • Continue using all native Odoo search features

    """,

    "author": "Mind Spark Technologies",
    "website": "https://www.mindsparktechnologies.com",
    "maintainer": "Mind Spark Technologies",

    "category": "Tools",
    "version": "18.0.5.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "web",
        "mail",
    ],

    "data": [
        "security/ir.model.access.csv",
        "views/ai_provider_views.xml",
        "views/ai_search_history_views.xml",
        "views/menu_views.xml",
    ],

    "assets": {
        "web.assets_backend": [
            "mst_ai_universal_search/static/src/js/search_bar_patch.js",
            "mst_ai_universal_search/static/src/scss/ai_search.scss",
        ],
    },

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": False,
    "auto_install": False,
}