# -*- coding: utf-8 -*-
{
    "name": "Purchase Order Summary Report (QWeb PDF)",
    "summary": "Professional Purchase Order PDF Report with Clean Layout in Odoo",

    "description": """
        Purchase Order Summary Report
        =============================
        
        Overview
        --------
        Enhance your Odoo purchasing process with a professional and well-structured 
        Purchase Order PDF report. This module provides a clean, printable, and 
        business-ready purchase order format with improved layout and readability.
        
        Features
        --------
        - Professional Purchase Order PDF (QWeb)
        - Clean and structured report layout
        - Vendor details with full address
        - Product table with quantity, rate, and subtotal
        - Automatic totals and tax calculations
        - Amount in words support
        - Company branding (logo, address, contact details)
        - Footer with user, date, and page numbers
        - Optimized for A4 printing
        - Easy customization
        
        Benefits
        --------
        - Improves document presentation
        - Saves time with automated calculations
        - Enhances vendor communication
        - Ensures professional reporting standards
        - Reduces manual formatting effort
        
        Use Cases
        ---------
        - Businesses generating purchase orders
        - Procurement teams
        - Manufacturing and trading companies
        - Companies needing professional PDF reports
        
        Technical Details
        -----------------
        - Report Type: QWeb PDF
        - Compatible with Odoo 18 Community & Enterprise
        - Uses standard Odoo reporting framework
        
        Keywords
        --------
        odoo purchase order report
        odoo po report pdf
        purchase order summary report odoo
        odoo qweb purchase report
        odoo procurement report
        odoo purchase print format
        purchase order template odoo
        odoo pdf report customization
        odoo 18 purchase report
        vendor purchase order report
    """,

    "author": "Mind Spark Technologies",
    "website": "https://mindsparktechnologies.com/odoo/",
    "maintainer": "Mind Spark Technologies",

    "category": "Purchases",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",

    "depends": [
        "purchase",
        "mail",
    ],

    "data": [
        "views/epurchase_order_report_qweb.xml",
        "views/purchase_order_qweb_header.xml",
        "views/reports.xml",
        "views/res_company_inherit_view.xml",

    ],

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": False,
    "auto_install": False,
}