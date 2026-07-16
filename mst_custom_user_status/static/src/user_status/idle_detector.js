/** @odoo-module **/

import { presenceState, setPresenceStateLocally } from "./presence_state";
import { refreshAvatarDot } from "./avatar_dot";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";

const IDLE_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes
const ACTIVITY_EVENTS = ["mousemove", "keydown", "mousedown", "scroll", "touchstart", "wheel"];

let idleTimer = null;

// True only while the CURRENT "Away" status was set automatically by this
// idle detector -- as opposed to the user having deliberately picked
// Away themselves from the menu. Only in the former case should activity
// automatically bring them back to Online.
let autoAwayActive = false;

async function callSetStatus(value) {
    try {
        const result = await rpc("/web/dataset/call_kw", {
            model: "res.users",
            method: "action_set_custom_presence_status",
            args: [[session.uid], value],
            kwargs: {},
        });
        const confirmed = result?.status || value;
        setPresenceStateLocally(confirmed);
        refreshAvatarDot();
    } catch (e) {
        console.warn("mst_custom_user_status: idle auto-status update failed", e);
    }
}

function goIdle() {
    // Only auto-apply idle-away if the status is currently plain Online.
    // A manually-chosen Away/Do Not Disturb/In a Meeting/Offline always
    // takes priority and is never overridden by inactivity.
    if (presenceState.status === "online") {
        autoAwayActive = true;
        callSetStatus("away");
    }
}

function handleActivity() {
    if (autoAwayActive) {
        autoAwayActive = false;
        callSetStatus("online");
    }
    if (idleTimer) {
        clearTimeout(idleTimer);
    }
    idleTimer = setTimeout(goIdle, IDLE_TIMEOUT_MS);
}

// Called by the profile menu whenever the user manually picks a status,
// so a deliberate choice is never later mistaken for (and reverted by)
// the idle system.
export function notifyManualStatusChange() {
    autoAwayActive = false;
}

function init() {
    ACTIVITY_EVENTS.forEach((evt) =>
        window.addEventListener(evt, handleActivity, { passive: true })
    );
    handleActivity(); // start the timer
}

if (document.body) {
    init();
} else {
    document.addEventListener("DOMContentLoaded", init, { once: true });
}