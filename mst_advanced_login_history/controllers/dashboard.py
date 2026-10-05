# -*- coding: utf-8 -*-

from odoo import fields, http
from odoo.exceptions import AccessError
from odoo.http import request


class AdvancedLoginHistoryDashboardController(http.Controller):

    def _format_datetime(self, value):
        if not value:
            return ""
        return fields.Datetime.context_timestamp(request.env.user, value).strftime(
            "%b %d, %Y %I:%M %p"
        )

    def _format_duration(self, duration):
        if not duration:
            return "-"
        total_minutes = int(round(duration * 60))
        hours, minutes = divmod(total_minutes, 60)
        if hours and minutes:
            return f"{hours}h {minutes}m"
        if hours:
            return f"{hours}h"
        return f"{minutes}m"

    def _browser_name(self, record):
        browser = record.browser or "-"
        browser_lower = browser.lower()
        for key, name in {
            "chrome": "Chrome",
            "chromium": "Chrome",
            "firefox": "Firefox",
            "edge": "Edge",
            "safari": "Safari",
            "opera": "Opera",
        }.items():
            if key in browser_lower:
                return name
        return browser

    def _os_name(self, record):
        os_name = record.operating_system or ""
        os_lower = os_name.lower()
        for key, name in {
            "windows": "Windows",
            "ubuntu": "Linux",
            "linux": "Linux",
            "android": "Android",
            "iphone": "iOS",
            "ipad": "iOS",
            "ios": "iOS",
            "mac": "macOS",
        }.items():
            if key in os_lower:
                return name
        return os_name

    def _browser_icon(self, browser):
        browser = (browser or "").lower()
        if "chrome" in browser or "chromium" in browser:
            return "fa-chrome"
        if "firefox" in browser:
            return "fa-firefox"
        if "edge" in browser:
            return "fa-edge"
        if "safari" in browser:
            return "fa-safari"
        if "opera" in browser:
            return "fa-opera"
        return "fa-globe"

    def _os_icon(self, operating_system):
        os_name = (operating_system or "").lower()
        if "windows" in os_name:
            return "fa-windows"
        if "linux" in os_name or "ubuntu" in os_name:
            return "fa-linux"
        if "android" in os_name:
            return "fa-android"
        if any(value in os_name for value in ["mac", "ios", "iphone", "ipad"]):
            return "fa-apple"
        return "fa-desktop"

    def _browser_icon_url(self, browser):
        browser = (browser or "").lower()
        base = "/mst_advanced_login_history/static/src/img/icons"
        if "chrome" in browser or "chromium" in browser:
            return f"{base}/chrome.svg"
        if "firefox" in browser:
            return f"{base}/firefox.svg"
        if "edge" in browser:
            return f"{base}/edge.svg"
        if "safari" in browser:
            return f"{base}/safari.svg"
        if "opera" in browser:
            return f"{base}/opera.svg"
        return f"{base}/globe.svg"

    def _os_icon_url(self, operating_system):
        os_name = (operating_system or "").lower()
        base = "/mst_advanced_login_history/static/src/img/icons"
        if "windows" in os_name:
            return f"{base}/windows.svg"
        if "linux" in os_name or "ubuntu" in os_name:
            return f"{base}/linux.svg"
        if "android" in os_name:
            return f"{base}/android.svg"
        if any(value in os_name for value in ["mac", "ios", "iphone", "ipad"]):
            return f"{base}/apple.svg"
        return f"{base}/desktop.svg"

    def _country_flag(self, country):
        return {
            "India": "🇮🇳",
            "United States": "🇺🇸",
            "United States of America": "🇺🇸",
            "United Kingdom": "🇬🇧",
            "United Arab Emirates": "🇦🇪",
            "Canada": "🇨🇦",
            "Australia": "🇦🇺",
            "Germany": "🇩🇪",
            "France": "🇫🇷",
            "Singapore": "🇸🇬",
            "Malaysia": "🇲🇾",
            "Sri Lanka": "🇱🇰",
            "China": "🇨🇳",
            "Japan": "🇯🇵",
            "South Korea": "🇰🇷",
            "Brazil": "🇧🇷",
            "Mexico": "🇲🇽",
            "South Africa": "🇿🇦",
            "Saudi Arabia": "🇸🇦",
            "Qatar": "🇶🇦",
            "Oman": "🇴🇲",
            "Kuwait": "🇰🇼",
        }.get((country or "").strip(), "🌍")

    def _split_location_parts(self, city="", region="", country="", full_location=""):
        city = (city or "").strip()
        region = (region or "").strip()
        country = (country or "").strip()
        full_location = (full_location or "").strip()

        if full_location and (not city or not country):
            parts = [item.strip() for item in full_location.split(",") if item.strip()]
            if not city and parts:
                city = parts[0]
            if not country and len(parts) >= 2:
                country = parts[-1]
            elif not country and len(parts) == 1:
                country = parts[0]
            if not region and len(parts) >= 3:
                region = ", ".join(parts[1:-1])
            elif not region and len(parts) == 2:
                region = parts[1]

        location_line = ", ".join(item for item in [city, country] if item)
        location_full = ", ".join(item for item in [city, region, country] if item)
        if not location_line:
            location_line = location_full or full_location or "-"
        if not location_full:
            location_full = location_line or "-"

        return {
            "city": city or "-",
            "region": region or "-",
            "country": country or "-",
            "location_line": location_line or "-",
            "location_full": location_full or "-",
        }

    def _prepare_login_row(self, record, active_session_ids=None):
        active_session_ids = active_session_ids or set()
        is_active = bool(record.session_id and record.session_id in active_session_ids)
        browser_name = self._browser_name(record)
        os_name = self._os_name(record)
        location_parts = self._split_location_parts(
            city=record.city,
            region=record.region,
            country=record.country,
            full_location=record.full_location,
        )
        return {
            "id": f"login_{record.id}",
            "res_model": "login.history",
            "res_id": record.id,
            "user": record.user_id.name or "-",
            "email": record.user_id.login or "",
            "login_time": self._format_datetime(record.login_time),
            "raw_date": record.login_time,
            "status": "Successful Login" if is_active else "Logout",
            "status_class": "success" if is_active else "logout",
            "status_icon": "fa-check-circle" if is_active else "fa-sign-out",
            "ip_address": record.ip_address or "-",
            "location": location_parts["location_full"],
            "location_line": location_parts["location_line"],
            "city": location_parts["city"],
            "region": location_parts["region"],
            "country": location_parts["country"],
            "country_flag": self._country_flag(location_parts["country"]),
            "browser_name": browser_name,
            "os_name": os_name,
            "browser_icon": self._browser_icon(record.browser),
            "os_icon": self._os_icon(record.operating_system),
            "browser_icon_url": self._browser_icon_url(record.browser),
            "os_icon_url": self._os_icon_url(record.operating_system),
            "browser_label": browser_name[:1].upper() if browser_name and browser_name != "-" else "?",
            "os_label": os_name[:1].upper() if os_name and os_name != "-" else "?",
            "browser_device": " / ".join(value for value in [browser_name, os_name] if value) or "-",
            "session_duration": self._format_duration(record.duration),
            "latitude": record.latitude or "",
            "longitude": record.longitude or "",
        }

    def _prepare_failed_row(self, record):
        browser_name = self._browser_name(record)
        os_name = self._os_name(record)
        location_parts = self._split_location_parts(
            city=record.city,
            region=record.region,
            country=record.country,
            full_location=record.full_location,
        )
        return {
            "id": f"failed_{record.id}",
            "res_model": "login.failed.history",
            "res_id": record.id,
            "user": record.login or "Unknown User",
            "email": record.login or "",
            "login_time": self._format_datetime(record.attempt_time),
            "raw_date": record.attempt_time,
            "status": "Failed Login",
            "status_class": "failed",
            "status_icon": "fa-exclamation-triangle",
            "ip_address": record.ip_address or "-",
            "location": location_parts["location_full"],
            "location_line": location_parts["location_line"],
            "city": location_parts["city"],
            "region": location_parts["region"],
            "country": location_parts["country"],
            "country_flag": self._country_flag(location_parts["country"]),
            "browser_name": browser_name,
            "os_name": os_name,
            "browser_icon": self._browser_icon(record.browser),
            "os_icon": self._os_icon(record.operating_system),
            "browser_icon_url": self._browser_icon_url(record.browser),
            "os_icon_url": self._os_icon_url(record.operating_system),
            "browser_label": browser_name[:1].upper() if browser_name and browser_name != "-" else "?",
            "os_label": os_name[:1].upper() if os_name and os_name != "-" else "?",
            "browser_device": " / ".join(value for value in [browser_name, os_name] if value) or "-",
            "session_duration": "-",
            "latitude": record.latitude or "",
            "longitude": record.longitude or "",
        }

    def _latest_location(self, rows):
        for row in rows:
            if row.get("latitude") and row.get("longitude"):
                latitude = row["latitude"]
                longitude = row["longitude"]
                location_parts = self._split_location_parts(
                    city=row.get("city"),
                    region=row.get("region"),
                    country=row.get("country"),
                    full_location=row.get("location"),
                )
                return {
                    "location": location_parts["location_full"],
                    "location_line": location_parts["location_line"],
                    "city": location_parts["city"],
                    "region": location_parts["region"],
                    "country": location_parts["country"],
                    "country_flag": self._country_flag(location_parts["country"]),
                    "ip_address": row.get("ip_address") or "-",
                    "browser_name": row.get("browser_name") or "-",
                    "os_name": row.get("os_name") or "",
                    "browser_icon": row.get("browser_icon") or "fa-globe",
                    "os_icon": row.get("os_icon") or "fa-desktop",
                    "browser_icon_url": row.get("browser_icon_url") or "/mst_advanced_login_history/static/src/img/icons/globe.svg",
                    "os_icon_url": row.get("os_icon_url") or "/mst_advanced_login_history/static/src/img/icons/desktop.svg",
                    "browser_label": row.get("browser_label") or "?",
                    "os_label": row.get("os_label") or "?",
                    "login_time": row.get("login_time") or "-",
                    "map_embed_url": (
                        f"https://maps.google.com/maps?q={latitude},{longitude}&z=12&output=embed"
                    ),
                    "open_url": f"https://www.google.com/maps?q={latitude},{longitude}",
                }
        return {
            "location": "-",
            "location_line": "-",
            "city": "-",
            "region": "-",
            "country": "-",
            "country_flag": "🌍",
            "ip_address": "-",
            "browser_name": "-",
            "os_name": "",
            "browser_icon": "fa-globe",
            "os_icon": "fa-desktop",
            "browser_icon_url": "/mst_advanced_login_history/static/src/img/icons/globe.svg",
            "os_icon_url": "/mst_advanced_login_history/static/src/img/icons/desktop.svg",
            "browser_label": "?",
            "os_label": "?",
            "login_time": "-",
            "map_embed_url": "",
            "open_url": "",
        }

    @http.route(
        "/mst_advanced_login_history/dashboard_data",
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def get_dashboard_data(self):
        if not request.env.user.has_group("base.group_system"):
            raise AccessError("Only administrators can view the audit dashboard.")

        login_history = request.env["login.history"].sudo()
        failed_history = request.env["login.failed.history"].sudo()

        native_sessions = request.env["res.session"].sudo().search([])
        active_session_ids = set(native_sessions.mapped("session_identifier"))

        login_records = login_history.search([], order="login_time desc", limit=30)
        failed_records = failed_history.search([], order="attempt_time desc", limit=30)

        rows = [
            self._prepare_login_row(record, active_session_ids=active_session_ids)
            for record in login_records
        ]
        rows += [self._prepare_failed_row(record) for record in failed_records]
        rows = sorted(
            rows,
            key=lambda row: row.get("raw_date") or fields.Datetime.now(),
            reverse=True,
        )[:20]

        active_domain = (
            [("session_id", "in", list(active_session_ids))]
            if active_session_ids
            else [("id", "=", 0)]
        )
        active_records = login_history.search(active_domain)
        # Same users for the tile count and the list opened by the tile
        active_user_ids = active_records.mapped("user_id").ids
        active_users = len(active_user_ids)

        location = self._latest_location(rows)
        for row in rows:
            row.pop("raw_date", None)

        successful_count = login_history.search_count([])
        failed_count = failed_history.search_count([])
        geolocated_count = (
            login_history.search_count([
                "|", ("city", "!=", False), ("country", "!=", False),
            ])
            + failed_history.search_count([
                "|", ("city", "!=", False), ("country", "!=", False),
            ])
        )

        return {
            "cards": [
                {
                    "title": "Total Logins",
                    "value": successful_count,
                    "icon": "👥",
                    "class": "primary",
                    "subtitle": "All recorded login sessions",
                    "model": "login.history",
                    "domain": [],
                },
                {
                    "title": "Successful",
                    "value": successful_count,
                    "icon": "✓",
                    "class": "success",
                    "subtitle": "Successful login sessions",
                    "model": "login.history",
                    "domain": [],
                },
                {
                    "title": "Failed Attempts",
                    "value": failed_count,
                    "icon": "!",
                    "class": "danger",
                    "subtitle": "Invalid authentication attempts",
                    "model": "login.failed.history",
                    "domain": [],
                },
                {
                    "title": "Active Users",
                    "value": active_users,
                    "icon": "⏺",
                    "class": "purple",
                    "subtitle": "Users with live sessions",
                    # Open the users themselves (not their login log lines)
                    "model": "res.users",
                    "domain": [["id", "in", active_user_ids]] if active_user_ids else [["id", "=", 0]],
                },
            ],
            "rows": rows,
            "location": location,
            "recent_activity": rows[:5],
            "summary": {
                "geolocated_count": geolocated_count,
                "latest_city": location.get("city") or "-",
                "latest_country": location.get("country") or "-",
            },
        }
