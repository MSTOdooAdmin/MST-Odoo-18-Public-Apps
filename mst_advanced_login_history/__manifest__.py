# -*- coding: utf-8 -*-
{
    "name": "Advanced Login History",
    "summary": "Odoo 18 Login History, Logout Tracking, Failed Login, IP, Browser, Device and Location Monitoring",

    "description": """
Advanced Login History
======================

Overview
--------
Advanced Login History is a free Odoo 18 module that helps administrators monitor user access activity with complete login, logout, failed login, browser, device, IP address, and location tracking.

This module improves Odoo security visibility by recording every user session with useful audit details such as login time, logout time, session duration, browser, operating system, IP address, country, city, latitude, longitude, and map location.

It also includes a clean dashboard view to quickly check total logins, successful logins, failed login attempts, active users, recent login activities, and latest login location.

Features
--------
- Track user login history in Odoo
- Track user logout history in Odoo
- Track failed login attempts
- Capture login time and logout time
- Calculate user session duration
- Capture IP address details
- Capture browser information
- Capture operating system and device details
- Track browser-based login location
- Track IP-based geo location
- Store country, region, city, latitude, and longitude
- View login location on Google Maps
- Display country flag in dashboard
- Display browser and operating system icons
- Dashboard for login activity summary
- Recent activity panel for quick monitoring
- Separate menu for login logs
- Separate menu for failed login logs
- Admin-friendly access monitoring
- Fully compatible with Odoo 18

Benefits
--------
- Improves Odoo login security monitoring
- Helps administrators track user access activity
- Identifies failed login attempts and suspicious access
- Maintains clear login and logout audit history
- Provides visibility of IP address, browser, device, and location
- Helps review active user sessions
- Reduces manual checking of server logs
- Supports internal audit and compliance needs
- Improves control over Odoo user access
- Useful for companies with multiple Odoo users
- Free and easy-to-use security tracking module

Use Cases
---------
- Companies that need Odoo user login tracking
- Administrators who want to monitor user access
- Businesses that need failed login attempt tracking
- Organizations that require login audit history
- Teams working with multiple internal Odoo users
- Companies that want to review login location and IP details
- Businesses looking for simple Odoo security monitoring
- Odoo administrators who want dashboard-based login visibility

Installation
------------
1. Copy the module to your Odoo addons directory.
2. Restart the Odoo server.
3. Update the Apps list.
4. Search for Advanced Login History.
5. Install the module from the Apps menu.

Configuration
-------------
- Install the module.
- Open the Advanced Login History menu.
- Go to Dashboard to view login activity summary.
- Go to Login Logs to view successful login and logout records.
- Go to Failed Login Logs to view failed login attempts.
- Allow browser location permission to capture accurate login location.

Usage
-----
- When a user logs in, the module automatically creates a login history record.
- When a user logs out, the module updates the logout time and session duration.
- When login fails, the module records the failed login attempt.
- Administrators can view all login details from the dashboard and log menus.
- Location records can be opened in Google Maps for quick review.

Technical Details
-----------------
- Module Type: Odoo Custom Module
- Compatible with Odoo 18 Community and Enterprise
- Depends on:
  * base
  * web
- Uses browser geolocation API for location tracking
- Uses IP-based geo location fallback
- Uses Odoo backend assets for dashboard view
- Uses Odoo frontend assets for login page location capture
- Includes login history and failed login history models
- Includes dashboard client action for login activity monitoring

Keywords
--------
odoo login history
odoo advanced login history
odoo 18 login history
free odoo login history module
odoo login tracking
odoo logout tracking
odoo failed login tracking
odoo failed login attempts
odoo user login tracking
odoo user activity tracking
odoo login audit
odoo security monitoring
odoo login location tracking
odoo ip address tracking
odoo browser tracking
odoo device tracking
odoo session tracking
odoo map location tracking
odoo login dashboard
odoo login logs
odoo user access history
odoo access monitoring
odoo admin security module
odoo 18 security module
odoo free security module
odoo login logout report
odoo user session history
odoo browser location history
odoo google map login location
odoo community login tracking
odoo enterprise login tracking

Author
------
Mind Spark Technologies

Website
-------
https://mindsparktechnologies.com

Support
-------
For support, contact:
info@mindsparktechnologies.com
""",

    "author": "Mind Spark Technologies",
    "website": "https://mindsparktechnologies.com",
    "maintainer": "Mind Spark Technologies",

    "category": "Administration",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",

    "depends": [
        "base",
        "web",
    ],

    "data": [
        "security/ir.model.access.csv",
        "views/login_history_views.xml",
        "views/login_history_dashboard_menu.xml",
    ],

    "assets": {
        "web.assets_backend": [
            "mst_advanced_login_history/static/src/js/session_tracker.js",
            "mst_advanced_login_history/static/src/js/login_history_dashboard.js",
            "mst_advanced_login_history/static/src/xml/login_history_dashboard.xml",
            "mst_advanced_login_history/static/src/scss/login_history_dashboard.scss",
        ],
        "web.assets_frontend": [
            "mst_advanced_login_history/static/src/js/login_location.js",
        ],
    },

    "images": [
        "static/description/banner.png",
    ],

    "installable": True,
    "application": True,
    "auto_install": False,
}