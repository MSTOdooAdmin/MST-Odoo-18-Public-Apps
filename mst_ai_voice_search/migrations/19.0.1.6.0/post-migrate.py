def migrate(cr, version):
    """Earlier versions defaulted to English replies. Replies now follow the language chosen
    in the voice panel (English / Tamil): switch databases still on the old default."""
    cr.execute("""
        UPDATE ir_config_parameter SET value = 'panel'
         WHERE key = 'mst_ai_voice_search.reply_language' AND value = 'en'
    """)
