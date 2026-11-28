import json

from odoo import http
from odoo.http import content_disposition, request


class VoiceSearchController(http.Controller):
    # All routes run as the logged-in user: menus, access rights and record rules apply.

    @http.route("/mst_ai_voice_search/config", type="jsonrpc", auth="user")
    def config(self):
        return request.env["mst.voice.search.engine"].get_client_config()

    @http.route("/mst_ai_voice_search/query", type="jsonrpc", auth="user")
    def query(self, text="", current_app_id=None, lang=None):
        try:
            current_app_id = int(current_app_id) if current_app_id else None
        except (TypeError, ValueError):
            current_app_id = None
        return request.env["mst.voice.search.engine"].process_query(text, current_app_id, lang)

    @http.route("/mst_ai_voice_search/execute", type="jsonrpc", auth="user")
    def execute(self, operation=None, lang=None):
        # Only reached after the user confirmed; the operation is fully re-checked server side.
        return request.env["mst.voice.search.engine"].execute_operation(operation, lang or "")

    @http.route("/mst_ai_voice_search/create_from_form", type="jsonrpc", auth="user")
    def create_from_form(self, model=None, values=None, lines=None, lang=None):
        return request.env["mst.voice.search.engine"].create_from_form(model, values or {}, lines or [], lang)

    @http.route("/mst_ai_voice_search/field_search", type="jsonrpc", auth="user")
    def field_search(self, model=None, field=None, term=""):
        return request.env["mst.voice.search.engine"].field_search(model, field, term)

    @http.route("/mst_ai_voice_search/export", type="http", auth="user", methods=["POST"], csrf=True)
    def export(self, model=None, domain="[]", lang=None, **kwargs):
        try:
            domain = json.loads(domain or "[]")
        except ValueError:
            domain = []
        content, filename = request.env["mst.voice.search.engine"].export_file(model, domain, lang)
        return request.make_response(content, headers=[
            ("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("Content-Disposition", content_disposition(filename)),
        ])
