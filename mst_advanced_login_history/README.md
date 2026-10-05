# Login History for Odoo 20

## Overview

This Odoo 20 module provides administrator-only security auditing for user logins and business-record activity. It tracks successful authenticated sessions, failed password login attempts, native session revocation, logout time, duration, IP address, browser, operating system, location information, and configured model activity.

The Odoo 20 migration keeps the native authentication, MFA/passkey, HTTP session, and logout pipeline intact. Custom login history is registered only after Odoo has fully authenticated the HTTP session.

## Main Features

- Odoo 20 login session history
- Failed interactive password-login audit
- Logout time and session duration
- Odoo 20 native `res.session` revocation integration
- Browser, operating system, IP and user-agent information
- Browser geolocation when permission is granted
- Native Odoo GeoIP fallback when available
- Login History Dashboard with desktop and mobile layouts
- Total logins, successful logins, failed attempts and active-user KPIs
- Recent authentication activity and location panel
- Create / modify / delete activity audit logs
- Field-level old and new value tracking
- Configurable model-specific audit logging
- Direct navigation back to related records
- Administrator smart buttons on the user form
- Administrator action to revoke other active sessions
- Administrator-only security menus and audit data

## Odoo 20 Migration Improvements

- Version updated to `20.0.1.1.0`
- Successful login registration moved to Odoo 20 `_after_session_login()` so MFA/passkey authentication can finish first
- Failed-login audit persistence isolated from Odoo's authentication transaction
- Deprecated JSON route usage replaced with `jsonrpc`
- Native Odoo 20 `res.session` records used for active-session KPIs and session revocation
- Successful login rows are bound to Odoo's final post-authentication rotated session identifier
- Expired native sessions are reconciled automatically with login-history status
- Native logout route extended instead of replacing the Odoo logout workflow
- Login-page location script moved to `web.assets_frontend_minimal`, which is loaded by the Odoo 20 login layout
- Native `request.geoip` used as the first IP-based location source
- Browser coordinates can be reverse-geocoded to City / Region / Country when IP GeoIP is unavailable (for example localhost/LAN testing)
- Technical fields hidden from normal lists and moved to detail sections
- Redundant dashboard KPI removed
- Advanced Logs and root menu restricted to administrators
- Obsolete commented view code, compiled files and unused helper code removed
- Responsive dashboard improved for desktop, tablet and mobile

## Menus

**Login History**

- Dashboard
- Login Logs
- Failed Login Logs
- Advanced Audit Logs
- Model Audit Logs
- Configuration → Model Audit Configuration

## User Form

Administrators can open a user and use:

- **Login Logs** smart button
- **Audit Logs** smart button
- **Revoke Sessions** action

For safety, Odoo's identity-check workflow is used before session revocation. When an administrator revokes their own devices, the current session is preserved in line with Odoo's native behavior.

## Location Tracking

Browser coordinates are captured only when the browser grants geolocation permission and the page runs in a secure context (HTTPS, or localhost during development). When browser coordinates are unavailable, the module uses Odoo's configured GeoIP support when available.

## Security

Audit menus and audit models are restricted to the Odoo **Settings / Administrator** group (`base.group_system`). Login and activity records are read-only from the normal UI. Internal code writes audit records with elevated rights only where required.

## Dependencies

- `base`
- `web`

## Installation / Upgrade

1. Copy `mst_advanced_login_history` into an Odoo 20 addons path.
2. Restart Odoo.
3. Update the Apps list.
4. Install the module, or upgrade it if migrating an existing database.
5. Clear/rebuild web assets if a browser still serves old JavaScript or SCSS.

Example upgrade command:

```bash
python odoo-bin -c odoo.conf -d YOUR_DATABASE -u mst_advanced_login_history --stop-after-init
```

## Compatibility

- Odoo 20 Community
- Odoo 20 Enterprise
- Desktop and mobile Odoo web client

## Author

Mind Spark Technologies  
https://mindsparktechnologies.com


## Odoo 20 Owl 3 compatibility

- Dashboard uses Owl 3 `proxy` state.
- Component template context uses `this.` references.
- Dashboard templates use `t-out`.
