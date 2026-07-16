/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

// Single in-memory source of truth for "what is MY status in this browser
// tab right now". Both the profile-menu widget and the notification
// suppressor read/write this same object.
//
// Initialized SYNCHRONOUSLY from session.custom_presence_status, which the
// server now embeds directly into the page's initial session_info payload
// (see res_users.py _get_session_info). This is what actually eliminates
// the "briefly/always shows Online right after reload" symptom: there is
// no async RPC race anymore, because the correct value is already present
// before this module even finishes loading, let alone before any menu or
// avatar dot renders.
export const presenceState = {
    status: session.custom_presence_status || "online",
};

export function setPresenceStateLocally(status) {
    presenceState.status = status;
}

async function fetchStatus() {
    // Kept as a fallback/refresh path (e.g. if the status was changed in
    // another tab since this page loaded), but is no longer relied on for
    // the initial value.
    try {
        const result = await rpc("/web/dataset/call_kw", {
            model: "res.users",
            method: "read",
            args: [[session.uid], ["custom_presence_status"]],
            kwargs: {},
        });
        if (result && result.length && result[0].custom_presence_status) {
            presenceState.status = result[0].custom_presence_status;
        }
    } catch (e) {
        console.warn("mst_custom_user_status: could not refresh presence status", e);
    }
}

// Kept for backward compatibility with call sites that still call this
// directly; now just re-triggers a fresh fetch on demand.
export const loadPresenceState = fetchStatus;

registry.category("services").add("custom_presence_state", {
    async start() {
        return { presenceState, refresh: fetchStatus, setPresenceStateLocally };
    },
});
