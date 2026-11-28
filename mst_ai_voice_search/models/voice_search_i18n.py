"""Built-in reply translations.

Voice Search answers in the language chosen in the voice panel (English / தமிழ்).
These translations ship with the module, so Tamil replies work even when the Tamil
language is not installed in Odoo. Placeholders (%s, %(name)s ...) are unchanged;
record names, numbers and model names are inserted as they are.
"""

TAMIL = {
    "I didn't catch anything. Try again or type your request.":
        "எதுவும் கேட்கவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது உங்கள் கோரிக்கையை தட்டச்சு செய்யவும்.",
    "%s has no screens you can open.": "%s-இல் நீங்கள் திறக்கக்கூடிய திரைகள் இல்லை.",
    "%s has these screens. Which one?": "%s-இல் இந்த திரைகள் உள்ளன. எதைத் திறக்க வேண்டும்?",
    "Opening %(menu)s in %(view)s view.": "%(menu)s-ஐ %(view)s காட்சியில் திறக்கிறேன்.",
    "%(menu)s doesn't have a %(view)s view on its screen, so I opened its records in %(view)s view.":
        "%(menu)s திரையில் %(view)s காட்சி இல்லை, எனவே அதன் பதிவுகளை %(view)s காட்சியில் திறந்தேன்.",
    "none": "இல்லை",
    "%(menu)s has no %(view)s view. Available views: %(available)s.":
        "%(menu)s-இல் %(view)s காட்சி இல்லை. கிடைக்கும் காட்சிகள்: %(available)s.",
    "I couldn't match that to a menu or records. Try \"open invoices\", \"show customers named Azure\" or \"how many draft quotations\".":
        "அதை ஒரு மெனு அல்லது பதிவுடன் பொருத்த முடியவில்லை. \"open invoices\", \"show customers named Azure\" "
        "அல்லது \"how many draft quotations\" என்று முயற்சிக்கவும்.",
    "No %(label)s named “%(name)s” was found.": "“%(name)s” என்ற பெயரில் %(label)s எதுவும் இல்லை.",
    "Opening %s": "%s-ஐ திறக்கிறேன்",
    "You don't have access to these %s records.": "இந்த %s பதிவுகளை அணுக உங்களுக்கு அனுமதி இல்லை.",
    "I couldn't run that search. Try rephrasing it.": "அந்தத் தேடலை இயக்க முடியவில்லை. வேறு விதமாகக் கேட்டுப் பாருங்கள்.",
    "%(label)s: %(count)s found.": "%(label)s: %(count)s கிடைத்தன.",
    "No %s records match that request.": "அந்தக் கோரிக்கைக்குப் பொருந்தும் %s பதிவுகள் இல்லை.",
    "%(label)s: %(total)s found, showing %(shown)s.": "%(label)s: %(total)s கிடைத்தன, %(shown)s காட்டப்படுகின்றன.",
    "%(label)s: %(total)s found.": "%(label)s: %(total)s கிடைத்தன.",
    "Deleting by voice is turned off in Settings → AI Voice Search.":
        "குரல் மூலம் நீக்குதல் Settings → AI Voice Search-இல் அணைக்கப்பட்டுள்ளது.",
    "Changes by voice are turned off in Settings → AI Voice Search.":
        "குரல் மூலம் மாற்றங்கள் Settings → AI Voice Search-இல் அணைக்கப்பட்டுள்ளன.",
    "I can't find that kind of record in your menus.": "அந்த வகைப் பதிவை உங்கள் மெனுக்களில் காண முடியவில்லை.",
    "You don't have permission to %(action)s %(label)s records.":
        "%(label)s பதிவுகளை %(action)s உங்களுக்கு அனுமதி இல்லை.",
    "%s records can't be archived.": "%s பதிவுகளை காப்பகப்படுத்த முடியாது.",
    "create": "உருவாக்க", "edit": "திருத்த", "delete": "நீக்க", "archive": "காப்பகப்படுத்த",
    "restore": "மீட்டெடுக்க", "duplicate": "நகலெடுக்க",
    "That field can't be changed by voice.": "அந்தப் புலத்தை குரல் மூலம் மாற்ற முடியாது.",
    "“%(value)s” isn't a number for %(field)s.": "“%(value)s” என்பது %(field)s-க்கான எண் அல்ல.",
    "Yes": "ஆம்", "No": "இல்லை",
    "Say yes or no for %s.": "%s-க்கு ஆம் அல்லது இல்லை என்று சொல்லவும்.",
    "“%(value)s” isn't a valid %(field)s.": "“%(value)s” என்பது சரியான %(field)s அல்ல.",
    "“%(value)s” isn't a date I understand for %(field)s.": "%(field)s-க்கான “%(value)s” என்ற தேதி புரியவில்லை.",
    "No %(field)s named “%(value)s” was found.": "“%(value)s” என்ற பெயரில் %(field)s எதுவும் இல்லை.",
    "Several %(field)s match “%(value)s”: %(names)s. Say the full name.":
        "“%(value)s”-க்கு பல %(field)s பொருந்துகின்றன: %(names)s. முழுப் பெயரைச் சொல்லவும்.",
    "“%s” can't be set by voice.": "“%s”-ஐ குரல் மூலம் அமைக்க முடியாது.",
    "%s records don't have product lines.": "%s பதிவுகளில் பொருள் வரிகள் இல்லை.",
    "No product named “%s” was found.": "“%s” என்ற பெயரில் பொருள் எதுவும் இல்லை.",
    "Several products match “%(value)s”: %(names)s. Say the full name.":
        "“%(value)s”-க்கு பல பொருட்கள் பொருந்துகின்றன: %(names)s. முழுப் பெயரைச் சொல்லவும்.",
    "Line: %(qty)s × %(product)s": "வரி: %(qty)s × %(product)s",
    "Say the new value, e.g. “set phone of customer Azure Interior to 9876543210”.":
        "புதிய மதிப்பைச் சொல்லவும், எ.கா. “set phone of customer Azure Interior to 9876543210”.",
    "Which kind of record? e.g. “%s quotation S00012”.": "எந்த வகைப் பதிவு? எ.கா. “%s quotation S00012”.",
    "Create %s": "%s உருவாக்கு",
    "Which %s? Say its name or reference.": "எந்த %s? அதன் பெயர் அல்லது குறிப்பைச் சொல்லவும்.",
    "I couldn't find the field “%(field)s” on %(label)s.": "%(label)s-இல் “%(field)s” என்ற புலம் இல்லை.",
    "Say what to change, e.g. “set phone of customer Azure Interior to 98765”.":
        "என்ன மாற்ற வேண்டும் என்று சொல்லவும், எ.கா. “set phone of customer Azure Interior to 98765”.",
    "Update": "புதுப்பி", "Delete": "நீக்கு", "Archive": "காப்பகப்படுத்து", "Restore": "மீட்டெடு",
    "Duplicate": "நகலெடு",
    "Several %s match. Which one?": "பல %s பொருந்துகின்றன. எது?",
    "This permanently deletes the record.": "இது பதிவை நிரந்தரமாக நீக்கும்.",
    "The record will be hidden from lists until restored.": "மீட்டெடுக்கும் வரை பதிவு பட்டியல்களில் மறைக்கப்படும்.",
    "Please confirm.": "தயவுசெய்து உறுதிப்படுத்தவும்.",
    "Nothing to do.": "செய்ய எதுவும் இல்லை.",
    "A linked record no longer exists.": "இணைக்கப்பட்ட ஒரு பதிவு இப்போது இல்லை.",
    "You don't have access to a linked record.": "இணைக்கப்பட்ட பதிவை அணுக உங்களுக்கு அனுமதி இல்லை.",
    "That %s no longer exists.": "அந்த %s இப்போது இல்லை.",
    "A product no longer exists.": "ஒரு பொருள் இப்போது இல்லை.",
    "%(label)s %(name)s created.": "%(label)s %(name)s உருவாக்கப்பட்டது.",
    "%s updated.": "%s புதுப்பிக்கப்பட்டது.", "%s deleted.": "%s நீக்கப்பட்டது.",
    "%s archived.": "%s காப்பகப்படுத்தப்பட்டது.", "%s restored.": "%s மீட்டெடுக்கப்பட்டது.",
    "Copy created: %s.": "நகல் உருவாக்கப்பட்டது: %s.",
    "You don't have permission to %(action)s this %(label)s.": "இந்த %(label)s-ஐ %(action)s உங்களுக்கு அனுமதி இல்லை.",
    "Odoo couldn't %(action)s this %(label)s. Open it to complete the required information.":
        "இந்த %(label)s-ஐ Odoo-வால் %(action)s முடியவில்லை. தேவையான தகவலை நிரப்ப அதைத் திறக்கவும்.",
    "%(label)s records have no %(field)s to filter on.": "%(label)s பதிவுகளில் வடிகட்ட %(field)s இல்லை.",
    "date": "தேதி",
    "I couldn't understand the date “%s”.": "“%s” என்ற தேதி புரியவில்லை.",
    "I couldn't find a field for “%s”.": "“%s”-க்கான புலம் கிடைக்கவில்லை.",
    "Which records? e.g. “%s contacts”.": "எந்தப் பதிவுகள்? எ.கா. “%s contacts”.",
    "Group by which field? e.g. “group contacts by country”.":
        "எந்தப் புலத்தின்படி குழுவாக்க வேண்டும்? எ.கா. “group contacts by country”.",
    "%(label)s records have no %(view)s view.": "%(label)s பதிவுகளுக்கு %(view)s காட்சி இல்லை.",
    "You don't have permission to import %s records.": "%s பதிவுகளை இறக்குமதி செய்ய உங்களுக்கு அனுமதி இல்லை.",
    "Opening the import screen for %s.": "%s-க்கான இறக்குமதித் திரையைத் திறக்கிறேன்.",
    "I couldn't find the field “%(field)s” to group %(label)s by.":
        "%(label)s-ஐ குழுவாக்க “%(field)s” என்ற புலம் கிடைக்கவில்லை.",
    "%(label)s by %(field)s": "%(field)s வாரியாக %(label)s",
    "%(label)s grouped by %(field)s (%(count)s records).":
        "%(field)s வாரியாக குழுவாக்கப்பட்ட %(label)s (%(count)s பதிவுகள்).",
    "No %s records match, so there is nothing to export.": "பொருந்தும் %s பதிவுகள் இல்லை, எனவே ஏற்றுமதி செய்ய எதுவும் இல்லை.",
    "Exporting %(count)s %(label)s records to Excel.": "%(count)s %(label)s பதிவுகளை Excel-க்கு ஏற்றுமதி செய்கிறேன்.",
    "%(label)s filtered by %(filters)s: %(count)s found.":
        "%(filters)s வடிகட்டிய %(label)s: %(count)s கிடைத்தன.",
    "You can't export these records.": "இந்தப் பதிவுகளை நீங்கள் ஏற்றுமதி செய்ய முடியாது.",
    "Fill in the required fields, then press Create.": "தேவையான புலங்களை நிரப்பி, பிறகு Create அழுத்தவும்.",
    "Press Create to create the %s.": "%s-ஐ உருவாக்க Create அழுத்தவும்.",
    "Choose a valid %s.": "சரியான %s-ஐத் தேர்ந்தெடுக்கவும்.",
    "Please fill in: %s.": "தயவுசெய்து நிரப்பவும்: %s.",
    "Messages need the Discuss app.": "செய்திகளுக்கு Discuss செயலி தேவை.",
    "Say who and what, e.g. “send message to Mitchell Admin saying the meeting is at 5”.":
        "யாருக்கு, என்ன என்று சொல்லவும், எ.கா. “send message to Mitchell Admin saying the meeting is at 5”.",
    "No user named “%s” was found.": "“%s” என்ற பெயரில் பயனர் எவரும் இல்லை.",
    "Send message to %s": "%s-க்கு செய்தி அனுப்பு",
    "Several users match. Who should get the message?": "பல பயனர்கள் பொருந்துகின்றனர். செய்தி யாருக்கு?",
    "That message can't be sent.": "அந்தச் செய்தியை அனுப்ப முடியாது.",
    "Message sent to %s.": "%s-க்கு செய்தி அனுப்பப்பட்டது.",
    "Opening %(label)s %(name)s.": "%(label)s %(name)s-ஐ திறக்கிறேன்.",
    "%(label)s has no “%(rel)s”.": "%(label)s-இல் “%(rel)s” இல்லை.",
    "Several %(label)s match “%(name)s”: %(names)s. Say the full name.":
        "“%(name)s”-க்கு பல %(label)s பொருந்துகின்றன: %(names)s. முழுப் பெயரைச் சொல்லவும்.",
    "You don't have access to these records.": "இந்தப் பதிவுகளை அணுக உங்களுக்கு அனுமதி இல்லை.",
    "%(record)s has %(count)s %(relation)s.": "%(record)s-இல் %(count)s %(relation)s உள்ளன.",
    "%(relation)s of %(record)s: %(count)s.": "%(record)s-இன் %(relation)s: %(count)s.",
    "%(record)s has no %(relation)s.": "%(record)s-இல் %(relation)s இல்லை.",
}

TRANSLATIONS = {"ta": TAMIL}
