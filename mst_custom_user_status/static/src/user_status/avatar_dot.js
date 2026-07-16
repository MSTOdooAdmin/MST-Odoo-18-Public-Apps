/** @odoo-module **/

import { presenceState } from "./presence_state";

const STATUS_COLORS = {
    online: "#28a745",
    away: "#f0ad4e",
    busy: "#dc3545",
    meeting: "#7f77dd",
    offline: "#adb5bd",
};

const DOT_CLASS = "o_custom_presence_avatar_dot";

function findAvatarAnchor() {
    // Anchor on the clickable user-menu trigger itself (button/link that
    // opens the dropdown), not on an <img> inside it -- letter-based
    // avatars (a colored circle with an initial, like "A") are commonly
    // rendered as a plain <div>/<span>, not an <img>, which is exactly
    // why this previously found nothing and drew no dot at all.
    return (
        document.querySelector(".o_user_menu") ||
        document.querySelector("header .o_avatar") ||
        document.querySelector(".o_avatar")
    );
}

function applyDot() {
    const anchor = findAvatarAnchor();
    if (!anchor) {
        return;
    }
    if (getComputedStyle(anchor).position === "static") {
        anchor.style.position = "relative";
    }
    let dot = anchor.querySelector(`.${DOT_CLASS}`);
    if (!dot) {
        dot = document.createElement("span");
        dot.className = DOT_CLASS;
        Object.assign(dot.style, {
            position: "absolute",
            bottom: "2px",
            right: "2px",
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            border: "2px solid white",
            boxSizing: "content-box",
            zIndex: "1000",
            pointerEvents: "none",
        });
        anchor.appendChild(dot);
    }
    dot.style.backgroundColor = STATUS_COLORS[presenceState.status] || STATUS_COLORS.online;
    dot.title = presenceState.status;
}

function init() {
    // The SPA can re-render the navbar (route changes, menu re-renders)
    // which would wipe out our injected dot, so watch for DOM changes
    // and reapply.
    const observer = new MutationObserver(() => applyDot());
    observer.observe(document.body, { childList: true, subtree: true });

    // Safety net in case a re-render happens in a way the observer misses.
    setInterval(applyDot, 2000);

    applyDot();
}

// This module can execute before document.body exists yet (it depends on
// exactly when the asset bundle runs relative to HTML parsing), which
// previously crashed MutationObserver.observe() with
// "parameter 1 is not of type 'Node'". Guard against that by waiting for
// the DOM to actually be ready first.
if (document.body) {
    init();
} else {
    document.addEventListener("DOMContentLoaded", init, { once: true });
}

export { applyDot as refreshAvatarDot };
