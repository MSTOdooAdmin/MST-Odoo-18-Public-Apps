/** @odoo-module **/

import { Component, onWillUnmount, useExternalListener, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
const START_WAIT_MS = 10000; // time to start speaking before giving up
const MAX_LISTEN_MS = 30000; // hard stop for one request
const LANG_KEY = "mst_ai_voice_search.lang";

const EXAMPLES = [
    "Open invoices",
    "Show customers named Azure",
    "How many draft quotations",
    "Create sales order for Azure Interior",
    "Group contacts by country",
    "Export customers",
];
// Tamil examples are real Tamil commands (understood with or without AI)
const EXAMPLES_TA = [
    "விலைப்பட்டியல்களை திற",
    "வாடிக்கையாளர்களை காட்டு",
    "எத்தனை வாடிக்கையாளர்கள்",
    "நாடு வாரியாக வாடிக்கையாளர்களை குழுவாக்கு",
    "வாடிக்கையாளர்களை ஏற்றுமதி",
];
// The panel's own wording in Tamil (follows the English / தமிழ் switch immediately)
const TA_UI = {
    "Voice search": "குரல் தேடல்",
    "Voice language": "குரல் மொழி",
    "Close": "மூடு",
    "Listening… speak now": "கேட்கிறேன்… இப்போது பேசுங்கள்",
    "Searching your database…": "உங்கள் தரவுத்தளத்தில் தேடுகிறேன்…",
    "Ask for a menu or for records, by voice or by typing.": "மெனு அல்லது பதிவுகளைக் குரல் மூலமோ தட்டச்சு மூலமோ கேளுங்கள்.",
    "e.g. Show customers named Azure": "எ.கா. வாடிக்கையாளர்களை காட்டு",
    "Your request": "உங்கள் கோரிக்கை",
    "Search": "தேடு",
    "Speak": "பேசு",
    "Stop listening": "கேட்பதை நிறுத்து",
    "Confirm": "உறுதிப்படுத்து",
    "Cancel": "ரத்து செய்",
    "or say “yes” / “no”": "அல்லது “ஆம்” / “இல்லை” என்று சொல்லுங்கள்",
    "Open list": "பட்டியலைத் திற",
    "Create": "உருவாக்கு",
    "Open full form": "முழுப் படிவத்தைத் திற",
    "Required:": "தேவை:",
    "Also required, fill in the full form:": "மேலும் தேவை, முழுப் படிவத்தில் நிரப்பவும்:",
    "Type to search…": "தேட தட்டச்சு செய்யவும்…",
    "Cancelled. Nothing was changed.": "ரத்து செய்யப்பட்டது. எதுவும் மாற்றப்படவில்லை.",
    "Excel file downloaded.": "Excel கோப்பு பதிவிறக்கப்பட்டது.",
    "I didn't catch that. Tap the mic and try again, or type your request.":
        "அது கேட்கவில்லை. மைக்கைத் தட்டி மீண்டும் முயற்சிக்கவும் அல்லது தட்டச்சு செய்யவும்.",
    "Microphone access is blocked. Allow it in your browser, or type your request.":
        "மைக்ரோஃபோன் அணுகல் தடுக்கப்பட்டுள்ளது. உலாவியில் அனுமதிக்கவும் அல்லது தட்டச்சு செய்யவும்.",
    "No microphone was found. Connect one, or type your request.":
        "மைக்ரோஃபோன் இல்லை. ஒன்றை இணைக்கவும் அல்லது தட்டச்சு செய்யவும்.",
    "That menu couldn't be opened.": "அந்த மெனுவைத் திறக்க முடியவில்லை.",
    "That record couldn't be opened.": "அந்தப் பதிவைத் திறக்க முடியவில்லை.",
    "That screen couldn't be opened.": "அந்தத் திரையைத் திறக்க முடியவில்லை.",
    "The change couldn't be completed. Check your connection and try again.":
        "மாற்றத்தை முடிக்க முடியவில்லை. இணைப்பைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.",
    "The export couldn't be downloaded. Try again.": "ஏற்றுமதியைப் பதிவிறக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்.",
    "The microphone needs a secure (https) connection. Type your request instead.":
        "மைக்ரோஃபோனுக்கு பாதுகாப்பான (https) இணைப்பு தேவை. தட்டச்சு செய்யவும்.",
    "The record couldn't be created. Check your connection and try again.":
        "பதிவை உருவாக்க முடியவில்லை. இணைப்பைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.",
    "The search couldn't be completed. Check your connection and try again.":
        "தேடலை முடிக்க முடியவில்லை. இணைப்பைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும்.",
    "This browser can't listen in that language. Try another language or type.":
        "இந்த உலாவி அந்த மொழியில் கேட்க முடியாது. வேறு மொழியை முயற்சிக்கவும் அல்லது தட்டச்சு செய்யவும்.",
    "Voice input couldn't start. Type your request instead.": "குரல் உள்ளீட்டைத் தொடங்க முடியவில்லை. தட்டச்சு செய்யவும்.",
    "Voice input isn't supported in this browser. Type your request instead, or use Chrome or Edge.":
        "இந்த உலாவியில் குரல் உள்ளீடு இல்லை. தட்டச்சு செய்யவும் அல்லது Chrome / Edge பயன்படுத்தவும்.",
    "Voice input stopped. Try again, or type your request.": "குரல் உள்ளீடு நின்றது. மீண்டும் முயற்சிக்கவும் அல்லது தட்டச்சு செய்யவும்.",
    "Voice recognition needs an internet connection. Type your request instead.":
        "குரல் அறிதலுக்கு இணைய இணைப்பு தேவை. தட்டச்சு செய்யவும்.",
};
const YES_RE = /^(yes|yeah|yep|ok|okay|confirm|do it|go ahead|sure|ஆம்|ஆமாம்|சரி)(\s|$|\b)/i;
const NO_RE = /^(no|nope|cancel|stop|don't|do not|இல்லை|வேண்டாம்)(\s|$|\b)/i;

export class VoiceSearch extends Component {
    static template = "mst_ai_voice_search.VoiceSearch";
    static props = {};

    setup() {
        this.actionService = useService("action");
        this.menuService = useService("menu");
        this.inputRef = useRef("input");

        this.speechSupported = Boolean(SpeechRecognitionAPI);
        this.secureContext = window.isSecureContext;
        this.config = null;
        this.recognition = null;
        this.requestToken = 0;
        this.state = useState({
            open: false,
            // idle | listening | thinking | done | error
            status: "idle",
            interim: "",
            text: "",
            message: "",
            result: null,
            lang: "",
            form: null, // { values, display, suggestions, searching }
        });
        this.languages = [];
        useExternalListener(window, "keydown", (ev) => {
            if (ev.key === "Escape" && this.state.open) {
                this.close();
            }
        });
        onWillUnmount(() => this.stopListening(true));
    }

    // ------------------------------------------------------------------
    // Panel
    // ------------------------------------------------------------------
    /** Panel wording in the panel's language (Tamil when தமிழ் is selected). */
    tr(text) {
        if (this.isTamil) {
            return TA_UI[text] || _t(text);
        }
        return _t(text);
    }

    get isTamil() {
        return (this.state.lang || "").toLowerCase().startsWith("ta");
    }

    get examples() {
        return this.isTamil ? EXAMPLES_TA : EXAMPLES.map((e) => _t(e));
    }

    get canListen() {
        return this.speechSupported && this.secureContext;
    }

    get unavailableReason() {
        if (!this.speechSupported) {
            return this.tr("Voice input isn't supported in this browser. Type your request instead, or use Chrome or Edge.");
        }
        if (!this.secureContext) {
            return this.tr("The microphone needs a secure (https) connection. Type your request instead.");
        }
        return "";
    }

    async onFabClick() {
        if (this.state.open && this.state.status === "listening") {
            this.stopListening(false);
            return;
        }
        if (!this.state.open) {
            this.state.open = true;
            this.resetResult();
            await this.loadConfig();
        }
        if (this.canListen) {
            this.startListening();
        } else {
            this.state.status = "idle";
            this.state.message = this.unavailableReason;
            this.focusInput();
        }
    }

    close() {
        this.stopListening(true);
        this.requestToken++; // ignore any answer still on its way
        this.state.open = false;
        this.state.status = "idle";
        window.speechSynthesis?.cancel();
    }

    resetResult() {
        this.state.result = null;
        this.state.form = null;
        this.state.message = "";
        this.state.interim = "";
    }

    focusInput() {
        setTimeout(() => this.inputRef.el?.focus(), 50);
    }

    async loadConfig() {
        if (this.config) {
            return;
        }
        try {
            this.config = await rpc("/mst_ai_voice_search/config", {});
        } catch {
            this.config = { speak_replies: false, ai_enabled: false, languages: [], silence_ms: 3000 };
        }
        this.languages = this.config.languages || [];
        let saved = "";
        try {
            saved = window.localStorage.getItem(LANG_KEY) || "";
        } catch {
            saved = "";
        }
        const codes = this.languages.map((l) => l.code);
        this.state.lang = codes.includes(saved) ? saved : codes[0] || "";
    }

    setLanguage(code) {
        this.state.lang = code;
        try {
            window.localStorage.setItem(LANG_KEY, code);
        } catch {
            // private mode: the choice just isn't remembered
        }
        if (this.state.status === "listening") {
            this.startListening(); // restart in the new language
        }
    }

    // ------------------------------------------------------------------
    // Speech recognition
    // ------------------------------------------------------------------
    get speechLang() {
        return this.state.lang || (user.lang || "en_US").replace("_", "-");
    }

    get replyLang() {
        // replies follow the panel language unless the admin fixed another reply language
        if (!this.config || this.config.reply_mode === "panel") {
            return this.isTamil ? "ta-IN" : "en-US";
        }
        return this.config.reply_lang || "en-US";
    }

    get hasPendingDecision() {
        return ["confirm", "choose", "menu_choices", "open_choices"].includes(this.state.result?.type);
    }

    startListening() {
        this.stopListening(true);
        if (this.hasPendingDecision) {
            // keep the confirmation on screen: the user is about to say "yes" / "no"
            this.state.message = "";
            this.state.interim = "";
        } else {
            this.resetResult();
        }
        this.state.text = "";
        const recognition = new SpeechRecognitionAPI();
        recognition.lang = this.speechLang;
        recognition.interimResults = true;
        // continuous: pauses between words don't end the request; we stop after the silence wait
        recognition.continuous = true;
        recognition.maxAlternatives = 1;
        const session = { finalText: "", failed: false, startedAt: Date.now(), restarts: 0, heard: false };
        const silenceMs = this.config?.silence_ms || 3000;
        const clearTimers = () => {
            clearTimeout(this.silenceTimer);
            clearTimeout(this.maxTimer);
        };
        const finishSoon = () => {
            clearTimeout(this.silenceTimer);
            this.silenceTimer = setTimeout(() => this.stopListening(false), silenceMs);
        };

        recognition.onresult = (event) => {
            let interim = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const chunk = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    session.finalText += (session.finalText ? " " : "") + chunk.trim();
                } else {
                    interim += chunk;
                }
            }
            session.heard = true;
            this.state.text = session.finalText.trim();
            this.state.interim = interim.trim();
            finishSoon(); // every word resets the silence timer
        };
        recognition.onerror = (event) => {
            if (event.error === "aborted" || event.error === "no-speech") {
                return; // no-speech: onend decides whether to keep waiting
            }
            session.failed = true;
            const messages = {
                "not-allowed": this.tr("Microphone access is blocked. Allow it in your browser, or type your request."),
                "service-not-allowed": this.tr("Microphone access is blocked. Allow it in your browser, or type your request."),
                "audio-capture": this.tr("No microphone was found. Connect one, or type your request."),
                network: this.tr("Voice recognition needs an internet connection. Type your request instead."),
                "language-not-supported": this.tr("This browser can't listen in that language. Try another language or type."),
            };
            this.state.status = "error";
            this.state.message = messages[event.error] || this.tr("Voice input stopped. Try again, or type your request.");
            this.focusInput();
        };
        recognition.onend = () => {
            if (this.recognition !== recognition) {
                return; // replaced or aborted on purpose
            }
            const waitedTooLong = Date.now() - session.startedAt > START_WAIT_MS;
            // The browser ended before the user said anything: keep listening a little longer
            if (!session.failed && !session.heard && !this.userStopped && !waitedTooLong && session.restarts < 3) {
                session.restarts++;
                try {
                    recognition.start();
                    return;
                } catch {
                    // fall through
                }
            }
            clearTimers();
            this.recognition = null;
            const text = (session.finalText + " " + this.state.interim).trim();
            this.state.interim = "";
            if (text) {
                this.state.text = text;
                this.submit(text);
            } else if (!session.failed) {
                this.state.status = "idle";
                this.state.message = this.tr("I didn't catch that. Tap the mic and try again, or type your request.");
            }
        };

        this.recognition = recognition;
        this.userStopped = false;
        this.state.status = "listening";
        clearTimers();
        this.maxTimer = setTimeout(() => this.stopListening(false), MAX_LISTEN_MS);
        try {
            recognition.start();
        } catch {
            this.recognition = null;
            this.state.status = "error";
            this.state.message = this.tr("Voice input couldn't start. Type your request instead.");
            this.focusInput();
        }
    }

    stopListening(abort) {
        clearTimeout(this.silenceTimer);
        clearTimeout(this.maxTimer);
        const recognition = this.recognition;
        if (!recognition) {
            return;
        }
        this.userStopped = true;
        if (abort) {
            this.recognition = null;
            recognition.abort();
        } else {
            recognition.stop(); // onend submits what was heard
        }
    }

    // ------------------------------------------------------------------
    // Typed input
    // ------------------------------------------------------------------
    onInput(ev) {
        this.state.text = ev.target.value;
    }

    onInputKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.submit(this.state.text);
        }
    }

    onSendClick() {
        this.submit(this.state.text);
    }

    useExample(example) {
        this.state.text = example;
        this.submit(example);
    }

    // ------------------------------------------------------------------
    // Server round trip
    // ------------------------------------------------------------------
    async submit(text) {
        text = (text || "").trim();
        if (!text || this.state.status === "thinking") {
            return;
        }
        // Records listed: saying one of their names opens it
        if (this.state.result?.type === "open_choices") {
            const wanted = text.toLowerCase();
            const choice = this.state.result.choices.find((c) => c.name.toLowerCase() === wanted);
            if (choice) {
                return this.pickRecord(choice);
            }
        }
        // Sub-menus listed: saying one of their names opens it
        if (this.state.result?.type === "menu_choices") {
            const wanted = text.toLowerCase();
            const choice = this.state.result.choices.find(
                (c) => c.name.toLowerCase() === wanted || c.name.toLowerCase().split(" / ").pop() === wanted
            );
            if (choice) {
                return this.pickMenu(choice);
            }
        }
        // A change is waiting for confirmation: "yes" / "no" answers it
        if (this.state.result?.type === "confirm") {
            if (YES_RE.test(text)) {
                this.state.text = "";
                return this.confirmOperation(this.state.result);
            }
            if (NO_RE.test(text)) {
                this.state.text = "";
                return this.cancelOperation();
            }
        }
        this.stopListening(true);
        const token = ++this.requestToken;
        this.resetResult();
        this.state.text = text;
        this.state.status = "thinking";
        let result;
        try {
            result = await rpc("/mst_ai_voice_search/query", {
                text,
                current_app_id: this.menuService.getCurrentApp()?.id || false,
                lang: this.state.lang || "",
            });
        } catch {
            if (token === this.requestToken) {
                this.state.status = "error";
                this.state.message = this.tr("The search couldn't be completed. Check your connection and try again.");
            }
            return;
        }
        if (token !== this.requestToken) {
            return; // a newer request (or closing the panel) replaced this one
        }
        await this.handleResult(result);
    }

    async handleResult(result) {
        this.state.result = result;
        this.state.message = result.message || "";
        this.state.status = result.type === "error" ? "error" : "done";
        this.speak(result.message);
        if (result.type === "form") {
            this.openForm(result);
            return;
        }
        if (result.type === "action") {
            // filter / group by / import: open the prepared screen
            try {
                await this.actionService.doAction(result.action);
                this.close();
            } catch {
                this.state.status = "error";
                this.state.message = this.tr("That screen couldn't be opened.");
            }
            return;
        }
        if (result.type === "export") {
            await this.exportFile(result);
            return;
        }
        if (result.type === "navigate") {
            await this.openMenu(result.menu_id, result.action_id, result.view_type);
        }
    }

    /**
     * Open a menu like Odoo's own menu click (breadcrumbs cleared, app bar updated),
     * optionally directly in a view type (kanban, list, pivot...).
     */
    async openMenu(menuId, actionId, viewType = false) {
        try {
            const menu = this.menuService.getMenu(menuId);
            const targetAction = (menu && menu.actionID) || actionId;
            if (!targetAction) {
                throw new Error("menu without action");
            }
            const options = { clearBreadcrumbs: true };
            if (viewType) {
                options.viewType = viewType;
            }
            if (menu) {
                options.onActionReady = () => this.menuService.setCurrentMenu(menu);
            }
            await this.actionService.doAction(targetAction, options);
            this.close();
        } catch {
            this.state.status = "error";
            this.state.message = this.tr("That menu couldn't be opened.");
        }
    }

    pickMenu(choice) {
        return this.openMenu(choice.menu_id, choice.action_id);
    }

    async pickRecord(choice) {
        // several records matched "open k channel": open the chosen one
        try {
            await this.actionService.doAction(choice.action);
            this.close();
        } catch {
            this.state.status = "error";
            this.state.message = this.tr("That record couldn't be opened.");
        }
    }

    // ------------------------------------------------------------------
    // Export
    // ------------------------------------------------------------------
    async exportFile(result) {
        try {
            await download({
                url: "/mst_ai_voice_search/export",
                data: { model: result.model, domain: JSON.stringify(result.domain || []), lang: this.state.lang || "" },
            });
            this.state.message = this.tr("Excel file downloaded.");
        } catch {
            this.state.status = "error";
            this.state.message = this.tr("The export couldn't be downloaded. Try again.");
        }
    }

    // ------------------------------------------------------------------
    // Create form: required fields first, then create
    // ------------------------------------------------------------------
    openForm(result) {
        const values = {};
        const display = {};
        for (const field of result.fields) {
            values[field.name] = field.value === false || field.value === null ? "" : field.value;
            display[field.name] = field.display || "";
        }
        this.state.form = { values, display, suggestions: {}, searching: {} };
    }

    onFormInput(field, ev) {
        const value = field.type === "boolean" ? ev.target.checked : ev.target.value;
        if (field.type === "many2one") {
            this.state.form.display[field.name] = value;
            this.state.form.values[field.name] = "";
            clearTimeout(this.searchTimer);
            this.searchTimer = setTimeout(() => this.searchRelated(field, value), 250);
            return;
        }
        this.state.form.values[field.name] = value;
    }

    async searchRelated(field, term) {
        const form = this.state.form;
        if (!form) {
            return;
        }
        form.searching[field.name] = true;
        try {
            form.suggestions[field.name] = await rpc("/mst_ai_voice_search/field_search", {
                model: this.state.result.model,
                field: field.name,
                term,
            });
        } catch {
            form.suggestions[field.name] = [];
        }
        form.searching[field.name] = false;
    }

    pickRelated(field, option) {
        this.state.form.values[field.name] = option[0];
        this.state.form.display[field.name] = option[1];
        this.state.form.suggestions[field.name] = [];
    }

    get formMissing() {
        const result = this.state.result;
        if (!result || result.type !== "form" || !this.state.form) {
            return [];
        }
        return result.fields
            .filter((f) => f.required && f.type !== "boolean" && !this.state.form.values[f.name])
            .map((f) => f.label);
    }

    async submitForm() {
        if (this.state.status === "thinking" || this.formMissing.length) {
            return;
        }
        const result = this.state.result;
        const token = ++this.requestToken;
        this.state.status = "thinking";
        let done;
        try {
            done = await rpc("/mst_ai_voice_search/create_from_form", {
                model: result.model,
                values: this.state.form.values,
                lines: result.lines || [],
                lang: this.state.lang || "",
            });
        } catch {
            if (token === this.requestToken) {
                this.state.status = "error";
                this.state.message = this.tr("The record couldn't be created. Check your connection and try again.");
            }
            return;
        }
        if (token !== this.requestToken) {
            return;
        }
        if (done.type === "error") {
            this.state.status = "error";
            this.state.message = done.message; // keep the form so the user can fix it
            return;
        }
        this.state.form = null;
        this.state.result = done;
        this.state.message = done.message || "";
        this.state.status = "done";
        this.speak(done.message);
        if (done.open) {
            await this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: done.open.res_model,
                res_id: done.open.res_id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    async openFullForm() {
        await this.actionService.doAction(this.state.result.open_form_action);
        this.close();
    }

    // ------------------------------------------------------------------
    // Voice actions (create / edit / delete / archive / restore / duplicate)
    // ------------------------------------------------------------------
    chooseRecord(choice) {
        // a "which one?" answer becomes a normal confirmation
        this.state.result = choice;
        this.state.message = choice.message;
        this.state.status = "done";
    }

    cancelOperation() {
        this.state.result = null;
        this.state.status = "idle";
        this.state.message = this.tr("Cancelled. Nothing was changed.");
    }

    async confirmOperation(confirmation) {
        if (this.state.status === "thinking") {
            return;
        }
        const token = ++this.requestToken;
        this.state.status = "thinking";
        let result;
        try {
            result = await rpc("/mst_ai_voice_search/execute", {
                operation: confirmation.operation,
                lang: this.state.lang || "",
            });
        } catch {
            if (token === this.requestToken) {
                this.state.status = "error";
                this.state.message = this.tr("The change couldn't be completed. Check your connection and try again.");
            }
            return;
        }
        if (token !== this.requestToken) {
            return;
        }
        this.state.result = result;
        this.state.message = result.message || "";
        this.state.status = result.type === "error" ? "error" : "done";
        this.speak(result.message);
        if (result.type !== "done") {
            return;
        }
        if (result.open) {
            await this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: result.open.res_model,
                res_id: result.open.res_id,
                views: [[false, "form"]],
                target: "current",
            });
        } else if (result.reload) {
            // refresh the current screen so a deleted/archived record disappears
            await this.actionService.doAction({ type: "ir.actions.client", tag: "soft_reload" });
        }
    }

    speak(message) {
        if (!message || !this.config?.speak_replies || !window.speechSynthesis) {
            return;
        }
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(message);
        utterance.lang = this.replyLang;
        window.speechSynthesis.speak(utterance);
    }

    // ------------------------------------------------------------------
    // Results
    // ------------------------------------------------------------------
    async openRecord(row) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: this.state.result.model,
            res_id: row.id,
            views: [[false, "form"]],
            target: "current",
        });
        this.close();
    }

    async openList() {
        if (!this.state.result?.list_action) {
            return;
        }
        await this.actionService.doAction(this.state.result.list_action);
        this.close();
    }
}

registry.category("main_components").add("mst_ai_voice_search.VoiceSearch", {
    Component: VoiceSearch,
});
