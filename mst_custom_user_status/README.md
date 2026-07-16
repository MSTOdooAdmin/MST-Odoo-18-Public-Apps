# User Presence Status for Odoo 18

Advanced user presence management inside the **native Odoo 18 user profile menu**, allowing users to manually control their availability with **Online**, **Away**, **Do Not Disturb**, **In a Meeting**, and **Offline** status.

Normal Odoo messaging, Discuss, chat, and notifications continue to work exactly as before. Users simply choose their preferred status from the profile menu.

---

# Features

- Online status
- Away status
- Do Not Disturb status
- In a Meeting status
- Offline status
- User profile menu integration
- Native Odoo avatar presence indicator
- Real-time presence synchronization
- Live updates using Odoo Bus
- Automatic idle detection
- Auto switch to Away after inactivity
- Automatic return to Online on user activity
- Manual status always has priority
- Persistent user presence state
- Desktop notification suppression
- Notification sound suppression
- No view customization required
- Works with existing Odoo presence system
- Fully compatible with Odoo 18

---

# Installation

1. Copy the **mst_custom_user_status** module into your custom addons directory.

2. Restart the Odoo server.

3. Upgrade the Apps List.

4. Install the module.

---

# Using User Presence Status

After installation,

Click your **User Avatar** in the top-right corner.

A new **Presence Status** section is available.

Select any of the available statuses.

---

## Available Presence States

- Online
- Away
- Do Not Disturb
- In a Meeting
- Offline

The selected status is immediately synchronized and displayed to other users throughout Odoo.

---

# Automatic Idle Detection

When the selected status is **Online**,

- After 5 minutes of keyboard or mouse inactivity, the status automatically changes to **Away**.

- As soon as user activity is detected, the status automatically returns to **Online**.

This automatic behavior only applies when the status is **Online**.

If the user manually selects:

- Away
- Do Not Disturb
- In a Meeting
- Offline

those statuses are never overridden by the idle detector.

---

# Do Not Disturb Mode

When **Do Not Disturb** is active,

- Desktop notifications are suppressed.

- Notification sounds are muted.

- Incoming Discuss messages do not interrupt the user.

This helps employees focus during important work or meetings.

---

# Presence Visibility

The selected presence status is automatically displayed wherever Odoo already shows user avatars, including:

- Discuss
- Chat Windows
- Discuss Members
- Employee Avatars
- Contacts
- Kanban Views
- List Views
- Activity Views
- Assigned Users
- Followers
- Mail Thread

No additional view customization is required.

---

# Live Synchronization

Presence changes are synchronized instantly using the Odoo Bus service.

Users currently online immediately see updated presence indicators without refreshing the page.

If a live update cannot be delivered, the correct status is displayed automatically after the next page refresh.

---

# Supported Applications

- Discuss
- Employees
- Contacts
- CRM
- Sales
- Purchase
- Inventory
- Accounting
- Manufacturing
- Projects
- Helpdesk
- Calendar
- Knowledge
- Documents
- Custom Modules


# Module Structure

```
mst_custom_user_status/

├── __manifest__.py
├── models/
├── static/
│   └── src/
│       └── user_status/
│           ├── presence_state.js
│           ├── avatar_dot.js
│           ├── idle_detector.js
│           ├── user_status_menu.js
│           ├── notification_suppressor.js
│           └── presence_status.css
├── security/
├── views/
└── README.md
```

---

# Compatibility

- Odoo 18 Community
- Odoo 18 Enterprise

---

# Benefits

- Improve team communication
- Display real-time employee availability
- Reduce unnecessary interruptions
- Enhance workplace collaboration
- Lightweight implementation
- Native Odoo integration
- No impact on existing Discuss functionality

---

# Author

**Mind Spark Technologies**

Website

https://www.mindsparktechnologies.com