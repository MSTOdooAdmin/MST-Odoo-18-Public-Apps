# -*- coding: utf-8 -*-

import json
import logging

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.session import Session as WebSession

from ..models.geo_utils import store_browser_location_in_session, valid_coordinates

_logger = logging.getLogger(__name__)



class LoginHistoryController(http.Controller):

    @http.route(
        "/mst_advanced_login_history/register_session",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        readonly=False,
    )
    def register_session(self):
        request.env["login.history"].sudo().register_current_session()
        return True

    @http.route(
        "/mst_advanced_login_history/register_frontend_session",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
        readonly=False,
    )
    def register_frontend_session(self, **kwargs):
        request.env["login.history"].sudo().register_current_session()
        return request.make_response(
            "success",
            headers=[("Content-Type", "text/plain; charset=utf-8")],
        )

    @http.route(
        "/mst_advanced_login_history/save_guest_location",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=True,
    )
    def save_guest_location(self, **kwargs):
        """Best-effort browser coordinates captured before authentication."""
        try:
            payload = {}
            if request.httprequest.data:
                payload = json.loads(request.httprequest.data.decode("utf-8"))

            latitude, longitude = valid_coordinates(
                payload.get("latitude"),
                payload.get("longitude"),
            )
            if latitude is not False and longitude is not False:
                store_browser_location_in_session(
                    request.session,
                    request.env,
                    latitude,
                    longitude,
                    city=payload.get("city"),
                    region=payload.get("region"),
                    country=payload.get("country"),
                    full_location=payload.get("full_location"),
                )
        except Exception:
            _logger.debug("Unable to cache guest browser location", exc_info=True)

        return request.make_response(
            "success",
            headers=[("Content-Type", "text/plain; charset=utf-8")],
        )

    @http.route(
        "/mst_advanced_login_history/update_location",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        readonly=False,
    )
    def update_location(self, latitude=None, longitude=None, city=None, region=None, country=None, full_location=None):
        """Attach browser coordinates to the current authenticated session."""
        latitude, longitude = valid_coordinates(latitude, longitude)
        if latitude is False or longitude is False:
            return False

        store_browser_location_in_session(
            request.session,
            request.env,
            latitude,
            longitude,
            city=city,
            region=region,
            country=country,
            full_location=full_location,
        )

        login_history = request.env["login.history"].sudo()
        login_history.register_current_session()
        login_history.update_browser_location(
            latitude=latitude,
            longitude=longitude,
        )
        return True


class LoginHistorySessionController(WebSession):
    """Extend Odoo's native logout route without replacing its session pipeline."""

    @http.route(readonly=False)
    def logout(self, redirect="/odoo"):
        try:
            user_id = request.session.uid
            session_id = request.session.sid
            if user_id:
                request.env["login.history"].sudo().logout_user_record(
                    user_id=user_id,
                    session_id=session_id,
                )
        except Exception:
            _logger.exception("Unable to update login history during logout")

        return super().logout(redirect=redirect)
