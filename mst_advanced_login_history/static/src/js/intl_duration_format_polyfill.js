/** @odoo-module ignore **/
/**
 * Intl.DurationFormat fallback for older browsers.
 *
 * Odoo 20 formats every duration (float_time, timesheets, planning...) with
 * Intl.DurationFormat, which only exists in Chrome/Edge 129+, Firefox 136+ and
 * Safari 16.4+. On older browsers the web client crashes with
 * "Intl.DurationFormat is not a constructor".
 *
 * This file only defines a fallback when the browser has no native
 * implementation, so up-to-date browsers keep using the real one. It supports
 * what Odoo 20 needs: format() and formatToParts() for the "narrow", "short",
 * "long" and "digital" styles with hours/minutes/seconds and their *Display
 * options. Unit labels are localized through Intl.NumberFormat.
 */
(function () {
    "use strict";
    if (typeof Intl === "undefined" || typeof Intl.DurationFormat === "function") {
        return;
    }

    const UNITS = [
        ["years", "year"],
        ["months", "month"],
        ["weeks", "week"],
        ["days", "day"],
        ["hours", "hour"],
        ["minutes", "minute"],
        ["seconds", "second"],
        ["milliseconds", "millisecond"],
    ];

    class DurationFormat {
        constructor(locales, options = {}) {
            const style = options.style || "short";
            this._locale = new Intl.NumberFormat(locales).resolvedOptions().locale;
            this._options = { ...options, style };
        }

        resolvedOptions() {
            return { locale: this._locale, numberingSystem: "latn", ...this._options };
        }

        _display(key) {
            const opt = this._options[`${key}Display`];
            if (opt) {
                return opt;
            }
            // Like the native API: digital style always shows h/m/s
            return this._options.style === "digital" &&
                ["hours", "minutes", "seconds"].includes(key)
                ? "always"
                : "auto";
        }

        formatToParts(duration = {}) {
            const style = this._options.style;
            const parts = [];
            if (style === "digital") {
                const keys = ["hours", "minutes", "seconds"].filter(
                    (key, index) =>
                        this._display(key) === "always" || (duration[key] || 0) !== 0 || index === 1
                );
                keys.forEach((key, index) => {
                    const unit = UNITS.find((u) => u[0] === key)[1];
                    const raw = Math.abs(Math.trunc(duration[key] || 0));
                    const value = index === 0 ? String(raw) : String(raw).padStart(2, "0");
                    if (index > 0) {
                        parts.push({ type: "literal", value: ":" });
                    }
                    parts.push({ type: "integer", value, unit });
                });
                return parts;
            }
            const unitDisplay = style === "long" ? "long" : style === "short" ? "short" : "narrow";
            let first = true;
            for (const [key, unit] of UNITS) {
                const amount = duration[key] || 0;
                if (amount === 0 && this._display(key) !== "always") {
                    continue;
                }
                let unitParts;
                try {
                    unitParts = new Intl.NumberFormat(this._locale, {
                        style: "unit",
                        unit,
                        unitDisplay,
                    }).formatToParts(amount);
                } catch {
                    // Very old engines without unit formatting
                    unitParts = [
                        { type: "integer", value: String(amount) },
                        { type: "unit", value: unit[0] },
                    ];
                }
                if (!first) {
                    parts.push({ type: "literal", value: " " });
                }
                first = false;
                for (const part of unitParts) {
                    if (part.type === "literal" && !part.value.trim()) {
                        continue; // Odoo joins parts itself ("1h 30m")
                    }
                    parts.push({ ...part, unit });
                }
            }
            return parts;
        }

        format(duration = {}) {
            const parts = this.formatToParts(duration);
            if (this._options.style === "digital") {
                return parts.map((p) => p.value).join("");
            }
            let out = "";
            for (const part of parts) {
                out += part.value;
                if (part.type === "unit") {
                    out += " ";
                }
            }
            return out.replace(/\s+/g, " ").trim();
        }
    }

    Object.defineProperty(Intl, "DurationFormat", {
        value: DurationFormat,
        writable: true,
        configurable: true,
    });
})();
