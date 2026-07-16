/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { session } from "@web/session";
import { presenceState, loadPresenceState, setPresenceStateLocally } from "./presence_state";
import { refreshAvatarDot } from "./avatar_dot";
import { notifyManualStatusChange } from "./idle_detector";

const userMenuRegistry = registry.category("user_menuitems");

// Ordered list of statuses. Colored circle emojis are used instead of CSS
// icon classes so the color renders reliably everywhere (menu item icons in
// the user_menuitems registry only support plain text/description strings).
const STATUS_OPTIONS = [
    { value: "online", emoji: "🟢", label: _t("Online") },
    { value: "away", emoji: "🟡", label: _t("Away") },
    { value: "busy", emoji: "🔴", label: _t("Do Not Disturb") },
    { value: "meeting", emoji: "🟣", label: _t("In a Meeting") },
    { value: "offline", emoji: "⚪", label: _t("Offline") },
];

const CLIENT_BUILD = "client-build-2026-07-06-idle-auto-away";

async function setStatus(env, value) {
    let result;
    try {
        result = await env.services.orm.call("res.users", "action_set_custom_presence_status", [
            [session.uid],
            value,
        ]);
    } catch (e) {
        // action_set_custom_presence_status now verifies the write against
        // the database and raises a clear error if it didn't persist, so
        // surface that to the user instead of silently doing nothing.
        env.services.notification.add(
            e?.data?.message || _t("Could not update your status. Please try again."),
            { type: "danger", sticky: true }
        );
        throw e;
    }

    // Trust the server-confirmed value (not just the value we asked for),
    // since action_set_custom_presence_status reads it back from the
    // database before returning.
    const confirmed = result?.status || value;
    setPresenceStateLocally(confirmed);
    notifyManualStatusChange();
    refreshAvatarDot();

    // Refresh the navbar avatar tooltip if present (best-effort, safe no-op
    // if the DOM structure differs on your version/theme).
    const avatarEl = document.querySelector(".o_user_menu img, .o_avatar img");
    if (avatarEl) {
        const opt = STATUS_OPTIONS.find((o) => o.value === confirmed);
        avatarEl.setAttribute("title", opt ? opt.label.toString() : "");
    }

    // Build tags are shown so you can instantly tell, right in the toast,
    // whether the browser (client) and the Odoo process (server) are
    // running the same version of this module -- the #1 cause of "I
    // applied the fix but nothing changed" is the server not having been
    // restarted after a Python change.
    const serverBuild = result?.server_build || "unknown (old server code, no build tag)";
    env.services.notification.add(
        _t("Status updated to: %s", STATUS_OPTIONS.find((o) => o.value === confirmed)?.label),
        { type: "success" }
    );
    // eslint-disable-next-line no-console
    console.log(
        `[mst_custom_user_status] client build: ${CLIENT_BUILD} | server build: ${serverBuild}`
    );
}

STATUS_OPTIONS.forEach((option, index) => {
    userMenuRegistry.add(
        `custom_presence_status_${option.value}`,
        (env) => {
            // The "custom_presence_state" service already loaded the real
            // status before the web client finished starting, so
            // presenceState.status is accurate by the time this ever runs.
            // This call is a harmless extra refresh in case the status was
            // changed from elsewhere since boot.
            loadPresenceState();
            const isCurrent = presenceState.status === option.value;
            return {
                type: "item",
                id: `presence_status_${option.value}`,
                description: `${option.emoji}  ${isCurrent ? "✔ " : ""}${option.label}`,
                callback: () => setStatus(env, option.value),
                sequence: 20 + index,
            };
        },
        { force: true }
    );
});
