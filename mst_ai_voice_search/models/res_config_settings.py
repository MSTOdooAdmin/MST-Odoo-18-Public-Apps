from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    mst_voice_ai_provider = fields.Selection(
        [("none", "No AI (keyword matching)"), ("openai", "ChatGPT / OpenAI"), ("gemini", "Google Gemini")],
        string="AI Provider",
        config_parameter="mst_ai_voice_search.ai_provider",
        default="none",
    )
    mst_voice_ai_api_key = fields.Char(
        string="AI API Key",
        config_parameter="mst_ai_voice_search.ai_api_key",
    )
    mst_voice_ai_model = fields.Char(
        string="AI Model",
        config_parameter="mst_ai_voice_search.ai_model",
        help="Leave empty for the default: gpt-4o-mini (OpenAI) or gemini-2.5-flash (Gemini).",
    )
    mst_voice_max_results = fields.Integer(
        string="Maximum Results",
        config_parameter="mst_ai_voice_search.max_results",
        default=10,
        help="Records shown per answer (1-50).",
    )
    mst_voice_action_mode = fields.Selection(
        [("read", "Search and navigate only"),
         ("write", "Also create, edit, archive and duplicate"),
         ("all", "Everything, including delete")],
        string="Voice Actions",
        config_parameter="mst_ai_voice_search.action_mode",
        default="all",
        help="Every change is shown for confirmation first and runs with the user's own access rights.",
    )
    mst_voice_reply_language = fields.Selection(
        [("panel", "Same as the voice panel language (English / Tamil)"), ("en", "Always English"),
         ("user", "Same as the user's Odoo language")],
        string="Reply Language",
        config_parameter="mst_ai_voice_search.reply_language",
        default="panel",
        help="Language of the answers, messages, chat and spoken replies (also for AI replies). "
             "With the voice panel language, switching English / தமிழ் changes the replies immediately.",
    )
    mst_voice_languages = fields.Selection(
        [("en-IN,ta-IN", "English and Tamil (switch in the panel)"),
         ("en-IN", "English (India)"), ("en-US", "English (US)"), ("ta-IN", "Tamil"),
         ("auto", "The user's Odoo language")],
        string="Voice Languages",
        config_parameter="mst_ai_voice_search.voice_languages",
        default="en-IN,ta-IN",
        help="Languages the microphone listens in.",
    )
    mst_voice_silence_seconds = fields.Integer(
        string="Silence Wait (seconds)",
        config_parameter="mst_ai_voice_search.silence_seconds",
        default=3,
        help="How long to wait after you stop speaking before the request is sent (1-10).",
    )
    # Default False on purpose: a boolean config parameter is deleted when unticked,
    # so reading it back as False is always correct.
    mst_voice_speak_replies = fields.Boolean(
        string="Speak Replies",
        config_parameter="mst_ai_voice_search.speak_replies",
        help="Read the answer aloud after each request.",
    )
