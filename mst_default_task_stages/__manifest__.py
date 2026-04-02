# -*- coding: utf-8 -*-
{
    "name": "Project Task Default Stages",
    "summary": "Odoo Project Workflow Automation with Default Task Stages",
    "description": """
        Project Default Task Stages
        ==========================
        
        This module provides Odoo project workflow automation by enabling
        default task stages configuration. It helps standardize task stages,
        improve project efficiency, and simplify project management in Odoo 18.
        
            Keywords:
            - Odoo project workflow
            - Default task stages Odoo
            - Project workflow automation Odoo
            - Task stage configuration Odoo
            
            Key Features:
            - Configure default task stages
            - Automate project workflow
            - Improve task pipeline visibility
                
        Use Cases
        =========
        
        • Standardize task workflow across projects  
        • Improve project tracking and stage visibility  
        • Reduce manual configuration when creating new projects  
        
        Compatible with Odoo Community & Enterprise Edition.
    """,

    "author": "Mind Spark Technologies",
    "website": "https://mindsparktechnologies.com/odoo/",
    "maintainer": "Mind Spark Technologies",
    "category": "Project",
    "version": "18.0.1.0",
    "license": "LGPL-3",
    "depends": ["project","mail","base"],
    "data": [
        "views/task_master_extended.xml",
    ],
    "images": [
        "static/description/banner.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}