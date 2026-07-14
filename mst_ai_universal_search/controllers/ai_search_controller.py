# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AISearchController(http.Controller):

    @http.route(
        "/ai/search/domain",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def ai_search_domain(self, model_name=None, query=None, provider_hint=None):
        history = request.env["ai.search.history"].sudo()
        try:
            result = request.env["ai.service"].process_query(
                model_name=model_name,
                user_query=query,
                provider_hint=provider_hint,
            )
            history.create(
                {
                    "query": query or "",
                    "model_name": model_name or "",
                    "provider_used": result.get("provider_name"),
                    "generated_domain": json.dumps(result.get("domain", [])),
                    "generated_groupby": json.dumps(result.get("group_by", [])),
                    "explanation": result.get("explanation"),
                    "status": "success",
                    "response": result.get("raw"),
                }
            )
            return {
                "success": True,
                "domain": result.get("domain", []),
                "group_by": result.get("group_by", []),
                "explanation": result.get("explanation"),
                "provider_name": result.get("provider_name"),
            }
        except Exception as exc:  # noqa: BLE001
            _logger.exception("AI search failed for %s: %s", model_name, query)
            history.create(
                {
                    "query": query or "",
                    "model_name": model_name or "",
                    "status": "failed",
                    "response": str(exc),
                }
            )
            return {"success": False, "error": str(exc)}
