/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";

async function registerCurrentSession() {
    try {
        await rpc("/mst_advanced_login_history/register_session", {});
    } catch {
        // Audit registration must never block the Odoo web client.
    }
}

async function reverseGeocode(latitude, longitude) {
    const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}&zoom=18&addressdetails=1&accept-language=en`;
    try {
        const response = await fetch(url, {
            method: "GET",
            headers: {
                Accept: "application/json",
            },
        });
        if (!response.ok) {
            return {};
        }
        const data = await response.json();
        const address = data.address || {};
        const city = address.city || address.town || address.village || address.municipality || address.suburb || address.county || "";
        const region = address.state || address.region || address.state_district || address.county || "";
        const country = address.country || "";
        const full_location = [city, region, country].filter(Boolean).join(", ") || (data.display_name || "");
        return { city, region, country, full_location };
    } catch {
        return {};
    }
}

function sendBrowserLocation(payload) {
    return rpc("/mst_advanced_login_history/update_location", payload).catch(() => false);
}

function captureBrowserLocation() {
    if (!navigator.geolocation) {
        return;
    }

    const isLocalhost = ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
    if (!window.isSecureContext && !isLocalhost) {
        return;
    }

    navigator.geolocation.getCurrentPosition(
        async (position) => {
            const payload = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            };
            const locationMeta = await reverseGeocode(position.coords.latitude, position.coords.longitude);
            await sendBrowserLocation({ ...payload, ...locationMeta });
        },
        () => {},
        {
            enableHighAccuracy: false,
            timeout: 8000,
            maximumAge: 5 * 60 * 1000,
        }
    );
}

window.setTimeout(async () => {
    await registerCurrentSession();
    captureBrowserLocation();
}, 500);
