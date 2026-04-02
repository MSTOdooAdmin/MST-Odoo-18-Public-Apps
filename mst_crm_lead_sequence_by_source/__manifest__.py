{
    "name": "CRM Lead Sequence Number Generation by Source",
    "version": "18.0.1.0",
    "category": "CRM",
    "summary": "Generate CRM lead sequence numbers based on Lead Source (UTM Source).",
    "description": """ 
        CRM Lead Sequence by Source
        ==========================
    
        This module generates a unique sequence number for CRM Leads based on the selected Lead Source (UTM Source).
        
        Key Features
        ------------
        - Adds a configurable "Lead Prefix" field on UTM Source (example: FB-, GG-, INSTA-).
        - Automatically creates and manages a dedicated sequence per Lead Source.
        - Assigns the correct sequence number while creating a lead.
        - If Lead Source is not set, fallback sequence is used (crm.lead).
        
        Use Case
        --------
        Perfect for tracking lead numbers separately for each marketing channel like Facebook, Google Ads, Instagram, Referral, etc.
        
        Notes
        -----
        - Sequence prefix updates automatically if Lead Prefix is changed in UTM Source.
        - Multi-company compatible (sequence is shared across companies by default).
        
        Support
        -------
        For customizations or enhancements, contact the Mind Spark Technologies.

        """,
    "author": "Mind Spark Technologies",
    "website": "https://mindsparktechnologies.com/odoo/",
    "license": "LGPL-3",
    "depends": ["crm", "utm"],
    "data": [
        "views/utm_source_views.xml",
        "views/crm_lead_views.xml"
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": False,
    }
