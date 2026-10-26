# Dynamic Odoo Branding — Odoo 19

## Update 19.0.1.3.2

Replace the module folder, restart Odoo, and upgrade Dynamic Odoo Branding in Apps.

In Settings → Dynamic Branding:

- **Powered By Text** defaults to `Powered by`.
- **Powered By Display Name** is optional. Enter `Mind Spark Technologies` to display `Powered by Mind Spark Technologies` with the default text.
- Existing custom Powered By Text is preserved. If it already contains your company name, leave Display Name empty or reset the text to `Powered by` before adding the name.
- Blank text falls back to `Powered by` on login, website/portal and newly generated emails. Existing emails are unchanged.
- **Show Manage Databases** shows/hides the link beneath the login form in standard and Website layouts. Click Save and reload the login page to apply.

These settings apply to the current database. The database selector/manager before a database is selected is outside this module's database-specific setting. The checkbox does not override server database-manager restrictions such as `list_db = False`, and hiding the link does not disable the route.

Browser title, URL prefix validation and routing, and other existing functionality are unchanged. Dynamic Brand Name is used for the browser title and is not automatically added to footer text.

## Favicon (19.0.1.4.0)

Settings → Dynamic Branding → **Favicon**: upload a small square image (PNG, ICO, SVG,
JPG, GIF or WebP, up to 1 MB).

* Backend and login page: your favicon.
* Websites still using Odoo's default favicon: your favicon.
* Websites with their own favicon (Website → Configuration → Settings): they keep it,
  and the Dynamic Branding settings show a warning naming those websites.

Clear the field and save to go back to Odoo's icon.
