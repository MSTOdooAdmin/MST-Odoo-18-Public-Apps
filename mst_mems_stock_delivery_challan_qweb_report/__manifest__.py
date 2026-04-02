# -*- coding: utf-8 -*-
{
    "name": "Delivery Challan Pdf Report ",
    "summary": "Professional Delivery Challan Report with Seal and Signature",
    "description": """
        Delivery Challan QWeb Report for Odoo
        ===========================================

        This module provides a fully customized Tax-compliant Delivery Challan
        report for Odoo 18 using QWeb. It enhances the default stock delivery
        document with a professional layout, company seal, signature.

        Keywords:
        - Odoo Delivery Challan
        - Delivery Challan Report Odoo 18
        - Stock Picking Report Customization
        - Odoo QWeb Report Customization
        - Challan Format India Odoo

        Key Features:
        - Compliant Delivery Challan format
        - Company Seal & Signature integration
        - Clean and professional QWeb layout
        - Amount in words support
        - Multi-copy format (Original / Duplicate / Triplicate)
        - Compatible with Odoo 18 Community & Enterprise

        Use Cases:
        - Businesses requiring Tax delivery challan print
        - Manufacturing & trading companies
        - Logistics and supply chain operations
        - Standardized challan reporting across organization

        Fully compatible with Odoo 18.
    """,

    "author": "Mind Spark Technologies",
    "website": "https://mindsparktechnologies.com/odoo/",
    "maintainer": "Mind Spark Technologies",
    "category": "Inventory",
    "version": "18.0.1.0",
    "license": "LGPL-3",

    "depends": ["base", "stock", "sale", "web"],

    "data": [
        "views/reports.xml",
        "views/delivery_challan_qweb_header.xml",
        "views/edelivery_challan_report_qweb.xml",
        "views/rescompany_inherit_view.xml",
    ],

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": True,
    "auto_install": False,
}