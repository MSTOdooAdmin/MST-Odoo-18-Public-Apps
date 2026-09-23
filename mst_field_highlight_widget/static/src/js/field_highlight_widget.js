/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Field, getFieldFromRegistry } from "@web/views/fields/field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { StatusBarField, statusBarField } from "@web/views/fields/statusbar/statusbar_field";
import { Component, onWillUnmount, useEffect, useRef } from "@odoo/owl";

const COLORS = {
    yellow: {
        background_color: "#FFF3CD",
        text_color: "#664D03",
        border_color: "#FFECB5",
    },
    green: {
        background_color: "#D1E7DD",
        text_color: "#0F5132",
        border_color: "#BADBCC",
    },
    red: {
        background_color: "#F8D7DA",
        text_color: "#842029",
        border_color: "#F5C2C7",
    },
    blue: {
        background_color: "#CFE2FF",
        text_color: "#084298",
        border_color: "#B6D4FE",
    },
    orange: {
        background_color: "#FFE5D0",
        text_color: "#7A2E00",
        border_color: "#FFC69B",
    },
    purple: {
        background_color: "#E2D9F3",
        text_color: "#432874",
        border_color: "#C5B3E6",
    },
    gray: {
        background_color: "#E2E3E5",
        text_color: "#41464B",
        border_color: "#D3D6D8",
    },
    cyan: {
        background_color: "#CFF4FC",
        text_color: "#055160",
        border_color: "#B6EFFB",
    },
    black: {
        background_color: "#212529",
        text_color: "#FFFFFF",
        border_color: "#000000",
    },
};


// Strong solid colors used only for the statusbar current-state highlight.
// Normal field highlights continue using the softer COLORS palette above.
const STATUSBAR_COLORS = {
    yellow: {
        background_color: "#997404",
        text_color: "#FFFFFF",
        border_color: "#664D03",
    },
    green: {
        background_color: "#146C43",
        text_color: "#FFFFFF",
        border_color: "#0F5132",
    },
    red: {
        background_color: "#B02A37",
        text_color: "#FFFFFF",
        border_color: "#842029",
    },
    blue: {
        background_color: "#0A58CA",
        text_color: "#FFFFFF",
        border_color: "#084298",
    },
    orange: {
        background_color: "#B54708",
        text_color: "#FFFFFF",
        border_color: "#7A2E00",
    },
    purple: {
        background_color: "#59359A",
        text_color: "#FFFFFF",
        border_color: "#432874",
    },
    gray: {
        background_color: "#495057",
        text_color: "#FFFFFF",
        border_color: "#343A40",
    },
    cyan: {
        background_color: "#087990",
        text_color: "#FFFFFF",
        border_color: "#055160",
    },
    black: {
        background_color: "#111111",
        text_color: "#FFFFFF",
        border_color: "#000000",
    },
};

const HIGHLIGHT_OPTION_KEYS = new Set([
    "base_widget",
    "color",
    "operator",
    "comparison_value",
    "compare_value",
    "background_color",
    "text_color",
    "border_color",
    "bold",
    "border_width",
    "border_radius",
    "padding_x",
    "padding_y",
    "apply_mode",
    "value_colors",
    "highlight_label",
]);

function isEmpty(value) {
    if (value === false || value === null || value === undefined || value === "") {
        return true;
    }
    if (Array.isArray(value)) {
        return value.length === 0;
    }
    if (typeof value === "object") {
        if ("count" in value) {
            return value.count === 0;
        }
        if ("id" in value) {
            return !value.id;
        }
    }
    return false;
}

function valueToComparable(value) {
    if (value === false || value === null || value === undefined) {
        return "";
    }
    if (typeof value === "boolean") {
        return value ? "true" : "false";
    }
    if (typeof value === "number" || typeof value === "string") {
        return String(value);
    }
    if (Array.isArray(value)) {
        return value.map((item) => valueToComparable(item)).join(",");
    }
    if (typeof value === "object") {
        if (typeof value.toISO === "function") {
            return value.toISO() || "";
        }
        if (typeof value.toISODate === "function") {
            return value.toISODate() || "";
        }
        if (value.id !== undefined) {
            return String(value.id || "");
        }
        if (value.display_name !== undefined) {
            return String(value.display_name || "");
        }
    }
    return String(value);
}

function isHexColor(value) {
    return typeof value === "string" && /^#(?:[0-9a-f]{3}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(value.trim());
}

function hexToRgb(value) {
    if (!isHexColor(value)) {
        return null;
    }
    let hex = value.trim().slice(1);
    if (hex.length === 3) {
        hex = hex.split("").map((char) => char + char).join("");
    }
    // Ignore the alpha channel for contrast calculation when #RRGGBBAA is used.
    if (hex.length === 8) {
        hex = hex.slice(0, 6);
    }
    return {
        r: parseInt(hex.slice(0, 2), 16),
        g: parseInt(hex.slice(2, 4), 16),
        b: parseInt(hex.slice(4, 6), 16),
    };
}

function contrastTextColor(backgroundColor) {
    const rgb = hexToRgb(backgroundColor);
    if (!rgb) {
        return "";
    }
    // YIQ contrast keeps dynamically supplied colors readable without
    // requiring a separate text color for every value.
    const yiq = (rgb.r * 299 + rgb.g * 587 + rgb.b * 114) / 1000;
    return yiq >= 160 ? "#212529" : "#FFFFFF";
}

function resolveColorOption(colorValue, palette) {
    if (isHexColor(colorValue)) {
        const colorCode = colorValue.trim();
        return {
            background_color: colorCode,
            text_color: contrastTextColor(colorCode),
            border_color: colorCode,
        };
    }
    return palette[colorValue] || {};
}

function normalizeStyle(styleOption, fallback = {}) {
    let raw = styleOption;
    if (typeof raw === "string") {
        // Dynamic value_colors can now use a color code directly:
        // {'draft': '#6C757D', 'done': '#198754'}
        raw = { color: raw };
    }
    raw = raw || {};

    const selectedColor =
        Object.keys(resolveColorOption(raw.color, COLORS)).length
            ? resolveColorOption(raw.color, COLORS)
            : resolveColorOption(fallback.color, COLORS);
    return {
        background_color:
            raw.background_color || fallback.background_color || selectedColor.background_color || "",
        text_color: raw.text_color || fallback.text_color || selectedColor.text_color || "",
        border_color: raw.border_color || fallback.border_color || selectedColor.border_color || "",
        bold: raw.bold !== undefined ? Boolean(raw.bold) : Boolean(fallback.bold),
        border_width: Number.isFinite(Number(raw.border_width ?? fallback.border_width))
            ? Number(raw.border_width ?? fallback.border_width)
            : 1,
        border_radius: Number.isFinite(Number(raw.border_radius ?? fallback.border_radius))
            ? Number(raw.border_radius ?? fallback.border_radius)
            : 6,
        padding_x: Number.isFinite(Number(raw.padding_x ?? fallback.padding_x))
            ? Number(raw.padding_x ?? fallback.padding_x)
            : 8,
        padding_y: Number.isFinite(Number(raw.padding_y ?? fallback.padding_y))
            ? Number(raw.padding_y ?? fallback.padding_y)
            : 4,
    };
}

function normalizeStatusbarStyle(styleOption, fallback = {}) {
    let raw = styleOption;
    if (typeof raw === "string") {
        raw = { color: raw };
    }
    raw = raw || {};

    const resolvedCurrent = resolveColorOption(raw.color, STATUSBAR_COLORS);
    const selectedColor = Object.keys(resolvedCurrent).length
        ? resolvedCurrent
        : resolveColorOption(fallback.color, STATUSBAR_COLORS);

    return {
        background_color:
            raw.background_color || fallback.background_color || selectedColor.background_color || "#495057",
        text_color:
            raw.text_color || fallback.text_color || selectedColor.text_color || "#FFFFFF",
        border_color:
            raw.border_color || fallback.border_color || selectedColor.border_color || "#343A40",
        bold: raw.bold !== undefined ? Boolean(raw.bold) : (fallback.bold !== undefined ? Boolean(fallback.bold) : true),
        border_width: Number.isFinite(Number(raw.border_width ?? fallback.border_width))
            ? Number(raw.border_width ?? fallback.border_width)
            : 1,
        border_radius: Number.isFinite(Number(raw.border_radius ?? fallback.border_radius))
            ? Number(raw.border_radius ?? fallback.border_radius)
            : 6,
        padding_x: Number.isFinite(Number(raw.padding_x ?? fallback.padding_x))
            ? Number(raw.padding_x ?? fallback.padding_x)
            : 8,
        padding_y: Number.isFinite(Number(raw.padding_y ?? fallback.padding_y))
            ? Number(raw.padding_y ?? fallback.padding_y)
            : 4,
    };
}

function matchesCondition(options, value) {
    const operator = options.operator || "always";
    const comparison = String(options.comparison_value ?? options.compare_value ?? "").trim();
    const current = valueToComparable(value).trim();
    const currentLower = current.toLowerCase();
    const comparisonLower = comparison.toLowerCase();

    switch (operator) {
        case "always":
            return true;
        case "equal":
            return currentLower === comparisonLower;
        case "not_equal":
            return currentLower !== comparisonLower;
        case "contains":
            return currentLower.includes(comparisonLower);
        case "not_contains":
            return !currentLower.includes(comparisonLower);
        case "empty":
            return isEmpty(value);
        case "not_empty":
            return !isEmpty(value);
        case "greater":
            return Number(current) > Number(comparison);
        case "greater_equal":
            return Number(current) >= Number(comparison);
        case "less":
            return Number(current) < Number(comparison);
        case "less_equal":
            return Number(current) <= Number(comparison);
        case "in": {
            const values = comparisonLower.split(",").map((v) => v.trim()).filter(Boolean);
            return values.includes(currentLower);
        }
        case "not_in": {
            const values = comparisonLower.split(",").map((v) => v.trim()).filter(Boolean);
            return !values.includes(currentLower);
        }
        default:
            return false;
    }
}

function appliesInMode(options, readonly) {
    const mode = options.apply_mode || "both";
    return mode === "both" || (mode === "readonly" && readonly) || (mode === "edit" && !readonly);
}


/**
 * Odoo 19's native statusbar uses the selection field definition order.
 * For this developer widget we intentionally make `statusbar_visible` the
 * authoritative visual order, because that is the order declared in XML.
 *
 * Example:
 * statusbar_visible="draft,confirmed,partial,completed,billed"
 * => Draft -> In Progress -> Partially Completed -> Completed -> Billed
 */
export class MstOrderedStatusBarField extends StatusBarField {
    getAllItems() {
        const items = super.getAllItems();
        const visibleSelection = this.props.visibleSelection || [];

        if (this.field.type !== "selection" || !visibleSelection.length) {
            return items;
        }

        const itemByValue = new Map(items.map((item) => [String(item.value), item]));
        const orderedItems = [];
        const usedValues = new Set();

        // First: exact order declared by statusbar_visible.
        for (const value of visibleSelection) {
            const key = String(value);
            const item = itemByValue.get(key);
            if (item) {
                orderedItems.push(item);
                usedValues.add(key);
            }
        }

        // Native Odoo keeps the current value visible even when it is not in
        // statusbar_visible (e.g. cancelled). Preserve that behavior, but only
        // after the explicitly ordered normal workflow states.
        for (const item of items) {
            const key = String(item.value);
            if (!usedValues.has(key)) {
                orderedItems.push(item);
            }
        }

        return orderedItems;
    }
}

export const mstOrderedStatusBarField = {
    ...statusBarField,
    component: MstOrderedStatusBarField,
    // FieldHighlightWidget renders the base widget through a nested generic
    // <Field/> component. Without this class Odoo sees that wrapper as
    // `o_field_selection`, so the native statusbar SCSS (including its
    // row-reverse layout) is not applied. Add the native class explicitly.
    // This makes ANY statusbar_visible sequence render in the exact XML order.
    additionalClasses: [
        ...(statusBarField.additionalClasses || []),
        "o_field_statusbar",
    ],
};

registry.category("fields").add("mst_ordered_statusbar", mstOrderedStatusBarField);

export class FieldHighlightWidget extends Component {
    static template = "mst_field_highlight_widget.FieldHighlightWidget";
    static components = { Field };
    static props = {
        ...standardFieldProps,
        highlightOptions: { type: Object, optional: true },
        originalFieldInfo: { type: Object },
    };

    setup() {
        this.rootRef = useRef("root");
        this.highlightedLabel = null;
        this.labelOriginalStyle = null;
        this.statusbarOriginalStyles = new Map();

        useEffect(
            () => {
                this.syncLabelHighlight();
                return () => this.restoreLabelHighlight();
            },
            () => [this.highlightStyle, this.hasHighlight, this.options.highlight_label]
        );

        useEffect(
            () => {
                this.syncStatusbarHighlight();
                return () => this.restoreStatusbarHighlight();
            },
            () => [
                this.currentValue,
                this.options.base_widget,
                JSON.stringify(this.options.value_colors || {}),
                this.options.bold,
                this.options.border_width,
            ]
        );

        onWillUnmount(() => {
            this.restoreLabelHighlight();
            this.restoreStatusbarHighlight();
        });
    }

    get options() {
        return this.props.highlightOptions || {};
    }

    get isStatusbarMode() {
        return this.options.base_widget === "statusbar";
    }

    get currentValue() {
        return this.props.record.data[this.props.name];
    }

    get innerFieldInfo() {
        const original = this.props.originalFieldInfo;
        const fieldType = original.type || this.props.record.fields[this.props.name].type;
        const options = { ...(original.options || {}) };

        // Remove only wrapper options. Any options needed by base_widget remain untouched.
        for (const key of HIGHLIGHT_OPTION_KEYS) {
            delete options[key];
        }

        let baseWidget = this.options.base_widget;
        if (baseWidget === "field_highlight") {
            baseWidget = undefined;
        }

        // In statusbar mode use our thin Odoo-19 subclass so the XML
        // `statusbar_visible` sequence controls the visual order as well as
        // visibility. All native statusbar behavior is otherwise preserved.
        const renderedWidget = baseWidget === "statusbar" ? "mst_ordered_statusbar" : baseWidget;
        const nativeField = getFieldFromRegistry(fieldType, renderedWidget, original.viewType);

        return {
            ...original,
            widget: renderedWidget,
            field: nativeField,
            options,
        };
    }

    get matchedStyle() {
        const options = this.options;
        const readonly = Boolean(this.props.readonly);

        if (!appliesInMode(options, readonly)) {
            return null;
        }

        // Developer syntax:
        // 'value_colors': {'draft': '#6C757D', 'done': '#198754'}
        // Each value may also be a full style object.
        const valueColors = options.value_colors;
        if (valueColors && typeof valueColors === "object") {
            const comparableValue = valueToComparable(this.currentValue);
            if (Object.prototype.hasOwnProperty.call(valueColors, comparableValue)) {
                return normalizeStyle(valueColors[comparableValue], options);
            }
        }

        if (!matchesCondition(options, this.currentValue)) {
            return null;
        }

        const hasStyle = [
            "color",
            "background_color",
            "text_color",
            "border_color",
        ].some((key) => Boolean(options[key]));

        return hasStyle ? normalizeStyle(options) : null;
    }

    get hasHighlight() {
        return Boolean(this.matchedStyle);
    }

    get highlightStyle() {
        // A statusbar must keep Odoo's own arrow layout. Its colors are applied
        // directly to the status buttons in syncStatusbarHighlight().
        if (this.isStatusbarMode) {
            return "";
        }
        const style = this.matchedStyle;
        if (!style) {
            return "";
        }
        return this.buildStyleString(style);
    }

    buildStyleString(style) {
        const background = style.background_color || "transparent";
        const text = style.text_color || "inherit";
        const border = style.border_color || "transparent";
        const borderWidth = Math.max(0, style.border_width);
        const radius = Math.max(0, style.border_radius);
        const paddingX = Math.max(0, style.padding_x);
        const paddingY = Math.max(0, style.padding_y);
        const weight = style.bold ? "600" : "inherit";

        return [
            `--mst-highlight-bg:${background}`,
            `--mst-highlight-text:${text}`,
            `--mst-highlight-border:${border}`,
            `background-color:${background}`,
            `color:${text}`,
            `border:${borderWidth}px solid ${border}`,
            `border-radius:${radius}px`,
            `padding:${paddingY}px ${paddingX}px`,
            `font-weight:${weight}`,
        ].join(";");
    }

    rememberStatusbarStyle(element) {
        if (!this.statusbarOriginalStyles.has(element)) {
            this.statusbarOriginalStyles.set(element, element.getAttribute("style"));
        }
    }

    applyStatusbarStyle(element, style) {
        this.rememberStatusbarStyle(element);

        const background = style.background_color || "transparent";
        const text = style.text_color || "inherit";
        const border = style.border_color || background;
        const weight = style.bold ? "600" : "inherit";

        // Odoo 19 statusbar arrows use CSS variables for the active/hover
        // background and for the clipped arrow border (::before). Setting the
        // variables on each button keeps the native statusbar shape intact.
        element.style.setProperty("--o-statusbar-background-active", background);
        element.style.setProperty("--o-statusbar-background-hover", background);
        element.style.setProperty("--o-statusbar-border", border);
        element.style.setProperty("--o-statusbar-border-active", border);
        element.style.setProperty("background-color", background, "important");
        element.style.setProperty("color", text, "important");
        element.style.setProperty("font-weight", weight, "important");
    }

    syncStatusbarHighlight() {
        this.restoreStatusbarHighlight();
        if (!this.isStatusbarMode) {
            return;
        }

        const root = this.rootRef.el;
        const valueColors = this.options.value_colors;
        if (!root || !valueColors || typeof valueColors !== "object") {
            return;
        }

        // Highlight ONLY the record's current status. `value_colors` is a
        // mapping from state value -> color, not an instruction to color every
        // visible statusbar step at the same time. All non-current states are
        // left untouched so they retain Odoo's native neutral appearance.
        const currentValue = valueToComparable(this.currentValue);
        const currentStyleOption = valueColors[currentValue];
        if (currentStyleOption === undefined) {
            return;
        }

        const currentStyle = normalizeStatusbarStyle(currentStyleOption, this.options);
        const buttons = root.querySelectorAll(
            ".o_statusbar_status .o_arrow_button[data-value]"
        );
        for (const button of buttons) {
            if (button.dataset.value === currentValue) {
                this.applyStatusbarStyle(button, currentStyle);
            }
        }

        // On small screens Odoo collapses the statusbar into one dropdown.
        // That dropdown represents the current state, so highlight it too.
        const compactButtons = root.querySelectorAll(
            ".o_statusbar_status button.dropdown-toggle:not(.o_arrow_button)"
        );
        for (const button of compactButtons) {
            this.applyStatusbarStyle(button, currentStyle);
        }
    }

    restoreStatusbarHighlight() {
        for (const [element, originalStyle] of this.statusbarOriginalStyles.entries()) {
            if (originalStyle === null) {
                element.removeAttribute("style");
            } else {
                element.setAttribute("style", originalStyle);
            }
        }
        this.statusbarOriginalStyles.clear();
    }

    findRelatedLabel() {
        const root = this.rootRef.el;
        if (!root) {
            return null;
        }

        // Standard Odoo inner-group layout: label cell is immediately before input cell.
        const inputCell = root.closest(".o_wrap_input");
        const previousCell = inputCell?.previousElementSibling;
        if (previousCell?.classList.contains("o_wrap_label")) {
            const label = previousCell.querySelector(".o_form_label, label");
            if (label) {
                return label;
            }
        }

        // Fallback for explicit labels outside a standard group.
        const form = root.closest(".o_form_renderer");
        const id = this.props.id;
        if (form && id) {
            const safeId = window.CSS?.escape ? window.CSS.escape(id) : id.replace(/"/g, '\\"');
            return form.querySelector(`label[for="${safeId}"]`);
        }

        return null;
    }

    syncLabelHighlight() {
        this.restoreLabelHighlight();

        // Header statusbars do not have a normal form label and must not try
        // to highlight one.
        if (this.isStatusbarMode) {
            return;
        }

        // Label highlighting is enabled by default. Use highlight_label: False to disable it.
        if (!this.hasHighlight || this.options.highlight_label === false) {
            return;
        }

        const label = this.findRelatedLabel();
        const style = this.matchedStyle;
        if (!label || !style) {
            return;
        }

        this.highlightedLabel = label;
        this.labelOriginalStyle = label.getAttribute("style");
        label.classList.add("o_mst_highlight_label");
        label.setAttribute("style", this.buildStyleString(style));
    }

    restoreLabelHighlight() {
        if (!this.highlightedLabel) {
            return;
        }

        this.highlightedLabel.classList.remove("o_mst_highlight_label");
        if (this.labelOriginalStyle === null) {
            this.highlightedLabel.removeAttribute("style");
        } else {
            this.highlightedLabel.setAttribute("style", this.labelOriginalStyle);
        }
        this.highlightedLabel = null;
        this.labelOriginalStyle = null;
    }
}

export const fieldHighlight = {
    component: FieldHighlightWidget,
    displayName: _t("Field Highlight"),
    supportedTypes: [
        "boolean",
        "integer",
        "float",
        "monetary",
        "many2one",
        "selection",
        "date",
        "datetime",
        "char",
        "text",
    ],
    extractProps: (fieldInfo) => ({
        highlightOptions: { ...(fieldInfo.options || {}) },
        originalFieldInfo: fieldInfo,
    }),
};

registry.category("fields").add("field_highlight", fieldHighlight);
