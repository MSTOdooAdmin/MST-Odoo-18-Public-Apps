# -*- coding: utf-8 -*-
{
    "name": "Sales Order Summary Report (QWeb PDF)",
    "summary": "Professional Sales Order PDF Report with Clean Layout in Odoo",

    "description": """
Sales Order Summary Report
=========================

Overview
--------
Enhance your Odoo sales process with a professional and well-structured 
Sales Order PDF report. This module provides a clean, printable, and 
business-ready sales order format with improved layout and readability.

Features
--------
- Professional Sales Order PDF (QWeb)
- Clean and structured report layout
- Customer details with full address
- Product table with quantity, rate, and subtotal
- Automatic totals and tax calculations
- Amount in words support
- Company branding (logo, address, contact details)
- Footer with signature and seal section
- Optimized for A4 printing
- Easy customization

Benefits
--------
- Improves document presentation
- Saves time with automated calculations
- Enhances customer communication
- Ensures professional reporting standards
- Reduces manual formatting effort

Use Cases
---------
- Sales teams
- Trading companies
- Manufacturing companies
- SMEs using Odoo ERP
- Businesses requiring professional quotations and sales orders

Technical Details
-----------------
- Report Type: QWeb PDF
- Compatible with Odoo 18 Community & Enterprise
- Uses standard Odoo reporting framework

Keywords
--------
odoo sales order report
odoo sale report pdf
sales order summary report odoo
odoo qweb sales report
odoo quotation report
odoo sales print format
sales order template odoo
odoo pdf report customization
odoo 18 sales report
customer sales order report
""",

    "author": "Mind Spark Technologies",
    "website": "https://mindsparktechnologies.com",
    "maintainer": "Mind Spark Technologies",

    "category": "Sales",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",

    "depends": [
        "sale_management",
        "mail",
    ],

    "data": [
        "views/sale_order_report_qweb.xml",
        "views/sale_order_qweb_header.xml",
        "views/reports.xml",
        # "views/res_company_inherit_view.xml",
    ],

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": False,
    "auto_install": False,
}