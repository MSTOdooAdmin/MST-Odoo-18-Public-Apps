# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models
from odoo.http import request

from .geo_utils import (
    browser_location_from_session,
    client_ip,
    geoip_values,
)

_logger = logging.getLogger(__name__)


class LoginFailedHistory(models.Model):
    _name = "login.failed.history"
    _description = "Failed Login History"
    _order = "attempt_time desc, id desc"

    login = fields.Char(string="Login", readonly=True, index=True)
    attempt_time = fields.Datetime(
        string="Attempt Time",
        readonly=True,
        default=fields.Datetime.now,
        index=True,
    )
    ip_address = fields.Char(string="IP Address", readonly=True)
    browser = fields.Char(string="Browser", readonly=True)
    operating_system = fields.Char(string="Operating System", readonly=True)
    user_agent = fields.Text(string="User Agent", readonly=True)
    country = fields.Char(string="Country", readonly=True)
    region = fields.Char(string="Region", readonly=True)
    city = fields.Char(string="City", readonly=True)
    latitude = fields.Char(string="Latitude", readonly=True)
    longitude = fields.Char(string="Longitude", readonly=True)
    full_location = fields.Char(string="Location", readonly=True)
    map_url = fields.Char(string="Map URL", compute="_compute_map_url", store=True)
    reason = fields.Char(string="Reason", readonly=True)
    location_source = fields.Selection(
        [
            ("browser", "Browser Location"),
            ("ip", "IP Geo Location"),
        ],
        string="Location Source",
        readonly=True,
    )

    def _compute_display_name(self):
        for record in self:
            login_name = record.login or "Unknown Login"
            if record.attempt_time:
                attempt_time = fields.Datetime.context_timestamp(
                    record,
                    record.attempt_time,
                ).strftime("%d-%m-%Y %I:%M %p")
                record.display_name = f"{login_name} - Failed Login - {attempt_time}"
            else:
                record.display_name = f"{login_name} - Failed Login"

    @api.depends("latitude", "longitude")
    def _compute_map_url(self):
        for record in self:
            record.map_url = False
            if record.latitude and record.longitude:
                record.map_url = (
                    f"https://www.google.com/maps?q={record.latitude},{record.longitude}"
                )

    @api.model
    def _get_request_details(self):
        values = {
            "ip_address": "",
            "browser": "",
            "operating_system": "",
            "user_agent": "",
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
        except Exception:
            _logger.debug("Unable to collect failed-login request details", exc_info=True)
        return values

    @api.model
    def _get_request_geo_location(self):
        if not request:
            return geoip_values(None)

        try:
            return geoip_values(request.geoip)
        except Exception:
            _logger.debug("Odoo GeoIP lookup unavailable for failed login", exc_info=True)
            return geoip_values(None)

    @api.model
    def _get_session_browser_location(self):
        if not request or not request.session:
            return browser_location_from_session(None)
        return browser_location_from_session(request.session)

    @api.model
    def create_failed_login_record_from_values(
        self,
        login="",
        reason="Invalid login credentials",
        request_values=None,
    ):
        request_values = dict(request_values or {})
        latitude = request_values.get("latitude") or request_values.get("geo_latitude")
        longitude = request_values.get("longitude") or request_values.get("geo_longitude")
        has_browser_location = bool(
            request_values.get("latitude") and request_values.get("longitude")
        )

        country = (
            request_values.get("browser_country") if has_browser_location else ""
        ) or request_values.get("country", "")
        region = (
            request_values.get("browser_region") if has_browser_location else ""
        ) or request_values.get("region", "")
        city = (
            request_values.get("browser_city") if has_browser_location else ""
        ) or request_values.get("city", "")
        full_location = (
            request_values.get("browser_full_location") if has_browser_location else ""
        ) or request_values.get("full_location", "")

        if not full_location:
            full_location = ", ".join(
                value for value in [city, region, country] if value
            )

        location_source = False
        if has_browser_location:
            location_source = "browser"
        elif latitude and longitude:
            location_source = "ip"

        return self.sudo().create({
            "login": login,
            "attempt_time": fields.Datetime.now(),
            "ip_address": request_values.get("ip_address"),
            "browser": request_values.get("browser"),
            "operating_system": request_values.get("operating_system"),
            "user_agent": request_values.get("user_agent"),
            "country": country,
            "region": region,
            "city": city,
            "latitude": str(latitude or ""),
            "longitude": str(longitude or ""),
            "full_location": full_location,
            "location_source": location_source,
            "reason": reason,
        })

    @api.model
    def create_failed_login_record(self, login="", reason="Invalid login credentials"):
        request_values = self._get_request_details()
        request_values.update(self._get_request_geo_location())
        request_values.update(self._get_session_browser_location())
        return self.create_failed_login_record_from_values(
            login=login,
            reason=reason,
            request_values=request_values,
        )

    def action_open_map(self):
        self.ensure_one()
        if not self.latitude or not self.longitude:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": f"https://www.google.com/maps?q={self.latitude},{self.longitude}",
            "target": "new",
        }
