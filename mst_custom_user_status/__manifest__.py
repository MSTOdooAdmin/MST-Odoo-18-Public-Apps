# -*- coding: utf-8 -*-
{
    "name": "User Presence Status",

    "summary": """
        Advanced user presence status with Online, Away, Do Not Disturb,
        Meeting, and Offline states for Odoo.
    """,

    "description": """
        Custom User Presence Status
        ======================================

        Custom User Presence Status enhances the standard Odoo user
        presence system by allowing users to manually control their
        availability directly from the user profile menu.

        Inspired by the modern presence management introduced in newer
        Odoo versions, this module provides additional presence states,
        real-time synchronization, automatic idle detection, and
        notification suppression for uninterrupted work.

        Users can instantly update their availability, making internal
        communication more efficient across Discuss, Chat, Employees,
        and all Odoo applications where user avatars are displayed.

        Keywords
        ============
        • User Presence
        • Online Status
        • Away Status
        • Do Not Disturb
        • Meeting Status
        • Offline Status
        • User Availability
        • Odoo Discuss
        • Live Presence
        • User Activity
        • Smart Presence
        • Employee Availability
        • Internal Communication
        • Team Collaboration
        • Notification Control
        • Odoo User Status
        • Odoo Presence Indicator
        • Odoo Collaboration
        • Productivity
        • Odoo 18

        Key Features
        ============
        ✔ Online status
        ✔ Away status
        ✔ Do Not Disturb status
        ✔ In a Meeting status
        ✔ Offline status
        ✔ User profile menu integration
        ✔ Native Odoo avatar presence indicator
        ✔ Real-time presence synchronization
        ✔ Live status updates using Odoo Bus
        ✔ Automatic idle detection
        ✔ Auto switch to Away after inactivity
        ✔ Automatic return to Online on activity
        ✔ Manual status always takes priority
        ✔ Persistent user presence status
        ✔ Desktop notification suppression
        ✔ Notification sound suppression
        ✔ No view customization required
        ✔ Works with existing Odoo presence system
        ✔ Seamless integration with Discuss
        ✔ Lightweight implementation
        ✔ Fully compatible with Odoo 18

        Supported Applications
        ======================
        ✔ Discuss
        ✔ Chat
        ✔ Employees
        ✔ Contacts
        ✔ Project
        ✔ Helpdesk
        ✔ CRM
        ✔ Sales
        ✔ Purchase
        ✔ Inventory
        ✔ Manufacturing
        ✔ Accounting
        ✔ Calendar
        ✔ Approvals
        ✔ Knowledge
        ✔ Documents
        ✔ Custom Modules

        Available Presence States
        =========================
        • Online
        • Away
        • Do Not Disturb
        • In a Meeting
        • Offline

        Automatic Presence Management
        =============================
        • Automatically switches from Online to Away after 5 minutes
          of keyboard or mouse inactivity.

        • Automatically returns to Online when user activity resumes.

        • Manual status selection always has higher priority than
          automatic presence detection.

        • User-selected statuses are never overridden by the idle timer.

        Notification Management
        =======================
        • Suppresses desktop notifications while Do Not Disturb is active.

        • Mutes notification sounds during Do Not Disturb mode.

        • Prevents interruptions while working or attending meetings.

        Workflow
        ========
        • Install the module.

        • Open the user profile menu from the top-right corner.

        • Select your preferred presence status.

        • Status is instantly visible to other users.

        • Live updates are synchronized across open sessions.

        • Continue using Odoo normally with enhanced presence management.

        Benefits
        ========
        • Improve internal communication.

        • Reduce unnecessary interruptions.

        • Show real-time employee availability.

        • Enhance team collaboration.

        • Better visibility across Discuss and business applications.

        • Increase workplace productivity.

        • Modern user experience similar to Odoo 19.

    """,

    "author": "MindSpark Technologies",
    "website": "https://www.mindsparktechnologies.com",
    "maintainer": "MindSpark Technologies",
    "category": "Discuss",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",

    "depends": [
        "web",
        "mail",
    ],

    "data": [],

    "assets": {
        "web.assets_backend": [
            "mst_custom_user_status/static/src/user_status/presence_state.js",
            "mst_custom_user_status/static/src/user_status/avatar_dot.js",
            "mst_custom_user_status/static/src/user_status/idle_detector.js",
            "mst_custom_user_status/static/src/user_status/user_status_menu.js",
            "mst_custom_user_status/static/src/user_status/notification_suppressor.js",
            "mst_custom_user_status/static/src/user_status/presence_status.css",
        ],
    },

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": False,
    "auto_install": False,
}