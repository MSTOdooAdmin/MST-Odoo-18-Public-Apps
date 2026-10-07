# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class AIProvider(models.Model):
    _name = "ai.provider"
    _description = "AI Provider"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    provider = fields.Selection(
        selection=[
            ("openai", "OpenAI (ChatGPT)"),
            ("claude", "Claude (Anthropic)"),
            ("gemini", "Gemini (Google)"),
            ("openai_compatible", "Other (OpenAI-compatible API)"),
        ],
        required=True,
        default="openai",
    )
    model_name = fields.Char(
        string="Model",
        required=True,
        help="Example: gpt-4o for OpenAI, claude-sonnet-4-5 for Claude, "
        "gemini-2.5-flash for Gemini, deepseek-chat / grok-4 / mistral-large-latest "
        "etc. for an OpenAI-compatible provider. "
        "Check the provider documentation for current model names.",
    )
    base_url = fields.Char(
        string="API Base URL",
        help="Only used when Provider = 'Other (OpenAI-compatible API)'. "
        "The chat-completions endpoint of the service, e.g.:\n"
        "- DeepSeek: https://api.deepseek.com/chat/completions\n"
        "- xAI Grok: https://api.x.ai/v1/chat/completions\n"
        "- Mistral: https://api.mistral.ai/v1/chat/completions\n"
        "- Groq: https://api.groq.com/openai/v1/chat/completions\n"
        "- OpenRouter: https://openrouter.ai/api/v1/chat/completions\n"
        "- Local Ollama: http://localhost:11434/v1/chat/completions",
    )
    api_key = fields.Text(required=True)
    temperature = fields.Float(default=0.1)
    max_tokens = fields.Integer(default=1024)
    active = fields.Boolean(default=True)

    def action_test_connection(self):
        """Run a tiny live request so the admin can confirm the key works."""
        self.ensure_one()
        service = self.env["ai.service"]
        try:
            raw = service._call_provider(
                self,
                system_prompt="You are a connectivity test. Reply with the JSON "
                '{"domain": [], "group_by": []} and nothing else.',
                user_query="ping",
            )
        except Exception as exc:  # noqa: BLE001
            raise UserError(_("Connection failed:\n\n%s") % exc) from exc

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Connection OK"),
                "message": _("Provider responded:\n%s") % (raw or "")[:300],
                "type": "success",
                "sticky": False,
            },
        }