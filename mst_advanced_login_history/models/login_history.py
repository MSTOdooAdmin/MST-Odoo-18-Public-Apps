# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import api, fields, models
from odoo.http import request
from odoo.http.session import STORED_SESSION_BYTES

from .geo_utils import (
    browser_location_from_session,
    client_ip,
    geoip_values,
    store_browser_location_in_session,
)

_logger = logging.getLogger(__name__)


class LoginHistory(models.Model):
    _name = "login.history"
    _description = "Login History"
    _order = "login_time desc, id desc"

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        ondelete="cascade",
        index=True,
    )
    login_time = fields.Datetime(string="Login Time", readonly=True, index=True)
    logout_time = fields.Datetime(string="Logout Time", readonly=True)
    duration = fields.Float(
        string="Duration (Hours)",
        compute="_compute_duration",
        store=True,
    )
    ip_address = fields.Char(string="IP Address", readonly=True)
    browser = fields.Char(string="Browser", readonly=True)
    operating_system = fields.Char(string="Operating System", readonly=True)
    user_agent = fields.Text(string="User Agent", readonly=True)
    session_id = fields.Char(
        string="Session Identifier",
        readonly=True,
        index=True,
        help="Stable Odoo session identifier used to correlate login and logout events.",
    )
    country = fields.Char(string="Country", readonly=True)
    region = fields.Char(string="Region", readonly=True)
    city = fields.Char(string="City", readonly=True)
    latitude = fields.Char(string="Latitude", readonly=True)
    longitude = fields.Char(string="Longitude", readonly=True)
    full_location = fields.Char(string="Location", readonly=True)
    map_url = fields.Char(string="Map URL", compute="_compute_map_url", store=True)
    location_source = fields.Selection(
        [
            ("browser", "Browser Location"),
            ("ip", "IP Geo Location"),
        ],
        string="Location Source",
        readonly=True,
    )
    status = fields.Selection(
        [
            ("active", "Active"),
            ("logout", "Logged Out"),
        ],
        string="Status",
        default="active",
        readonly=True,
        index=True,
    )

    def _compute_display_name(self):
        for record in self:
            user_name = record.user_id.name or "Unknown User"
            if record.login_time:
                login_time = fields.Datetime.context_timestamp(
                    record,
                    record.login_time,
                ).strftime("%d-%m-%Y %I:%M %p")
                record.display_name = f"{user_name} - {login_time}"
            else:
                record.display_name = user_name

    @api.depends("login_time", "logout_time")
    def _compute_duration(self):
        for record in self:
            record.duration = 0.0
            if record.login_time and record.logout_time:
                delta = record.logout_time - record.login_time
                record.duration = round(delta.total_seconds() / 3600, 4)

    @api.depends("latitude", "longitude")
    def _compute_map_url(self):
        for record in self:
            record.map_url = False
            if record.latitude and record.longitude:
                record.map_url = (
                    f"https://www.google.com/maps?q={record.latitude},{record.longitude}"
                )

    @api.model
    def _normalize_session_id(self, session_id):
        return (session_id or "")[:STORED_SESSION_BYTES]

    @api.model
    def _get_request_details(self):
        values = {
            "ip_address": "",
            "browser": "",
            "operating_system": "",
            "user_agent": "",
            "session_id": "",
        }
        if not request:
            return values

        try:
            http_request = request.httprequest
            user_agent = http_request.user_agent
            values.update({
                "ip_address": client_ip(http_request),
                "user_agent": user_agent.string or http_request.headers.get("User-Agent", ""),
                "browser": user_agent.browser or "",
                "operating_system": user_agent.platform or "",
            })
            if request.session:
                values["session_id"] = self._normalize_session_id(request.session.sid)
        except Exception:
            _logger.debug("Unable to collect login request details", exc_info=True)

        return values

    @api.model
    def _get_request_geo_location(self):
        if not request:
            return geoip_values(None)

        try:
            return geoip_values(request.geoip)
        except Exception:
            _logger.debug("Odoo GeoIP lookup unavailable", exc_info=True)
            return geoip_values(None)

    @api.model
    def _get_session_browser_location(self):
        if not request or not request.session:
            return browser_location_from_session(None)
        return browser_location_from_session(request.session)

    @api.model
    def _prepare_location_values(self, request_values):
        browser_latitude = request_values.get("latitude")
        browser_longitude = request_values.get("longitude")
        has_browser_location = bool(browser_latitude and browser_longitude)

        country = (
            request_values.get("browser_country")
            if has_browser_location
            else ""
        ) or request_values.get("country", "")
        region = (
            request_values.get("browser_region")
            if has_browser_location
            else ""
        ) or request_values.get("region", "")
        city = (
            request_values.get("browser_city")
            if has_browser_location
            else ""
        ) or request_values.get("city", "")
        full_location = (
            request_values.get("browser_full_location")
            if has_browser_location
            else ""
        ) or request_values.get("full_location", "")

        if has_browser_location:
            latitude = str(browser_latitude)
            longitude = str(browser_longitude)
            location_source = "browser"
        else:
            latitude = str(request_values.get("geo_latitude", "") or "")
            longitude = str(request_values.get("geo_longitude", "") or "")
            location_source = "ip" if latitude and longitude else False

        if not full_location:
            full_location = ", ".join(
                value for value in [city, region, country] if value
            )

        return {
            "country": country,
            "region": region,
            "city": city,
            "latitude": latitude,
            "longitude": longitude,
            "full_location": full_location,
            "location_source": location_source,
        }

    @api.model
    def create_login_record_from_values(self, user, request_values, login_time=None):
        if not user or not user.exists():
            return False

        request_values = dict(request_values or {})
        request_values["session_id"] = self._normalize_session_id(
            request_values.get("session_id")
        )
        location_values = self._prepare_location_values(request_values)

        if request_values["session_id"]:
            existing = self.sudo().search([
                ("user_id", "=", user.id),
                ("session_id", "=", request_values["session_id"]),
                ("status", "=", "active"),
            ], order="login_time desc", limit=1)
            if existing:
                return existing

        return self.sudo().create({
            "user_id": user.id,
            "login_time": login_time or fields.Datetime.now(),
            "logout_time": False,
            "ip_address": request_values.get("ip_address"),
            "browser": request_values.get("browser"),
            "operating_system": request_values.get("operating_system"),
            "user_agent": request_values.get("user_agent"),
            "session_id": request_values.get("session_id"),
            "country": location_values.get("country"),
            "region": location_values.get("region"),
            "city": location_values.get("city"),
            "latitude": location_values.get("latitude"),
            "longitude": location_values.get("longitude"),
            "full_location": location_values.get("full_location"),
            "location_source": location_values.get("location_source"),
            "status": "active",
        })

    @api.model
    def mark_login_pending(self, user):
        """Remember a completed authentication without storing the pre-rotation SID.

        Odoo 20 hard-rotates the HTTP session after authentication. The audit row
        is therefore bound to the final SID on the next authenticated request.
        """
        if not request or not request.session or not user or not user.exists():
            return False
        request.session["mst_audit_pending_user_id"] = user.id
        request.session["mst_audit_pending_login_time"] = fields.Datetime.to_string(
            fields.Datetime.now()
        )
        return True

    @api.model
    def register_current_session(self, user=None):
        """Create/repair the login record using the final rotated Odoo 20 SID."""
        if not request or not request.session or not request.session.uid:
            return False

        user = user or self.env["res.users"].sudo().browse(request.session.uid)
        if not user or not user.exists() or user.id != request.session.uid:
            return False

        request_values = self._get_request_details()
        request_values.update(self._get_request_geo_location())
        request_values.update(self._get_session_browser_location())

        login_time = False
        pending_user_id = request.session.get("mst_audit_pending_user_id")
        pending_login_time = request.session.get("mst_audit_pending_login_time")
        if pending_user_id == user.id and pending_login_time:
            login_time = fields.Datetime.to_datetime(pending_login_time)

        record = self.create_login_record_from_values(
            user,
            request_values,
            login_time=login_time,
        )

        request.session.pop("mst_audit_pending_user_id", None)
        request.session.pop("mst_audit_pending_login_time", None)
        return record

    @api.model
    def create_login_record(self, user):
        """Compatibility helper: register against the current final session."""
        return self.register_current_session(user=user)

    @api.model
    def update_browser_location(self, latitude=False, longitude=False):
        if not request or not request.session or not request.session.uid:
            return True

        if not store_browser_location_in_session(
            request.session,
            self.env,
            latitude,
            longitude,
        ):
            return False

        session_id = self._normalize_session_id(request.session.sid)
        domain = [
            ("user_id", "=", request.session.uid),
            ("status", "=", "active"),
        ]
        if session_id:
            domain.append(("session_id", "=", session_id))

        record = self.sudo().search(domain, order="login_time desc", limit=1)
        if record:
            browser_values = self._get_session_browser_location()
            geo_values = self._get_request_geo_location()
            city = browser_values.get("browser_city") or geo_values.get("city") or record.city
            region = browser_values.get("browser_region") or geo_values.get("region") or record.region
            country = browser_values.get("browser_country") or geo_values.get("country") or record.country
            full_location = (
                browser_values.get("browser_full_location")
                or geo_values.get("full_location")
                or ", ".join(value for value in [city, region, country] if value)
                or record.full_location
            )
            record.write({
                "latitude": browser_values.get("latitude") or record.latitude,
                "longitude": browser_values.get("longitude") or record.longitude,
                "country": country,
                "region": region,
                "city": city,
                "full_location": full_location,
                "location_source": "browser",
            })
        return True

    @api.model
    def logout_user_record(self, user_id=False, session_id=False):
        session_id = self._normalize_session_id(session_id)
        domain = [("status", "=", "active")]
        if session_id:
            domain.append(("session_id", "=", session_id))
        elif user_id:
            domain.append(("user_id", "=", user_id))
        else:
            return True

        record = self.sudo().search(domain, order="login_time desc", limit=1)
        if record:
            record.write({
                "logout_time": fields.Datetime.now(),
                "status": "logout",
            })
        return True


    @api.autovacuum
    def _sync_expired_native_sessions(self):
        """Close audit rows whose Odoo 20 native session no longer exists.

        Native Odoo inactivity cleanup marks expired ``res.session`` records as
        revoked without calling our explicit revocation override. A short grace
        period prevents a just-created login audit row from being closed before
        Odoo has written its first device/session trace.
        """
        cutoff = fields.Datetime.now() - timedelta(minutes=10)
        histories = self.sudo().search([
            ("status", "=", "active"),
            ("session_id", "!=", False),
            ("login_time", "<", cutoff),
        ])
        if not histories:
            return

        native_session_ids = set(
            self.env["res.session"].sudo().search([
                ("session_identifier", "in", histories.mapped("session_id")),
            ]).mapped("session_identifier")
        )
        stale_histories = histories.filtered(
            lambda history: history.session_id not in native_session_ids
        )
        if stale_histories:
            stale_histories.write({
                "logout_time": fields.Datetime.now(),
                "status": "logout",
            })

    def action_open_map(self):
        self.ensure_one()
        if not self.latitude or not self.longitude:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": f"https://www.google.com/maps?q={self.latitude},{self.longitude}",
            "target": "new",
        }
