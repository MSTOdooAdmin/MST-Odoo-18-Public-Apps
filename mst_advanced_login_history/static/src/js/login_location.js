/** @odoo-module **/

function postJson(url, payload = {}) {
    return fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    }).catch(() => false);
}

async function reverseGeocode(latitude, longitude) {
    const url = `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}&zoom=18&addressdetails=1&accept-language=en`;
    try {
        const response = await fetch(url, {
            method: "GET",
            headers: { Accept: "application/json" },
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

function captureLoginPageLocation() {
    const loginForm = document.querySelector("form.oe_login_form");
    if (!loginForm || !navigator.geolocation) {
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
            postJson("/mst_advanced_login_history/save_guest_location", { ...payload, ...locationMeta });
        },
        () => {},
        {
            enableHighAccuracy: false,
            timeout: 8000,
            maximumAge: 5 * 60 * 1000,
        }
    );
}

function registerAuthenticatedFrontendSession() {
    const loginForm = document.querySelector("form.oe_login_form");
    const sessionInfo = window.odoo && window.odoo.__session_info__;
    if (loginForm || !sessionInfo || !sessionInfo.uid) {
        return;
    }

    fetch("/mst_advanced_login_history/register_frontend_session", {
        method: "POST",
        credentials: "same-origin",
    }).catch(() => false);
}

window.setTimeout(() => {
    captureLoginPageLocation();
    registerAuthenticatedFrontendSession();
}, 500);
