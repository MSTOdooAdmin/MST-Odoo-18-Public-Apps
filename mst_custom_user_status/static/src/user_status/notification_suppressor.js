/** @odoo-module **/

import { presenceState } from "./presence_state";

const isDoNotDisturb = () => presenceState.status === "busy";

/**
 * This module works at the browser-API level (window.Notification and
 * HTMLMediaElement.play) rather than patching Odoo's internal mail
 * services directly. Reason: the exact service/file names Odoo uses to
 * trigger a desktop popup and to play the "ting" sound have changed
 * between minor versions, and guessing wrong would silently do nothing.
 * Every path that shows a desktop notification or plays a sound
 * ultimately goes through one of these two browser APIs, so patching
 * here is version-resilient.
 *
 * Tradeoff: this mutes/suppresses ALL browser notifications and ALL
 * audio playback on the page while Do Not Disturb is active, not just
 * mail-related ones. In a standard Odoo backend tab this is virtually
 * always what you want, but keep it in mind if you have other custom
 * modules on the same page that rely on the Notification or Audio API
 * for something unrelated to chat.
 */

// --- Suppress desktop/browser notification popups ---
const NativeNotification = window.Notification;
if (NativeNotification) {
    function PatchedNotification(title, options) {
        if (isDoNotDisturb()) {
            // Return an inert stub instead of a real Notification so any
            // calling code (close(), event handlers, etc.) doesn't throw.
            return {
                title,
                options,
                close: () => {},
                addEventListener: () => {},
                removeEventListener: () => {},
                onclick: null,
                onclose: null,
                onerror: null,
                onshow: null,
            };
        }
        return new NativeNotification(title, options);
    }
    PatchedNotification.permission = NativeNotification.permission;
    PatchedNotification.requestPermission = (...args) =>
        NativeNotification.requestPermission(...args);
    PatchedNotification.prototype = NativeNotification.prototype;
    window.Notification = PatchedNotification;
}

// --- Mute notification sounds ---
const originalPlay = HTMLMediaElement.prototype.play;
HTMLMediaElement.prototype.play = function (...args) {
    if (isDoNotDisturb()) {
        // Behave like a resolved play() promise so any calling code that
        // awaits it doesn't see an unexpected rejection.
        return Promise.resolve();
    }
    return originalPlay.apply(this, args);
};
