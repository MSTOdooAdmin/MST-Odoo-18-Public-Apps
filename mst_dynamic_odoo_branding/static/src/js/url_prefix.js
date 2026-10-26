/**
 * Dynamic URL prefix: show /<prefix>/... instead of /odoo/... in the address bar.
 *
 * Odoo's router (core/browser/router.js) builds and parses URLs with the fixed
 * "/odoo" prefix and only talks to the browser through `browser.location` and
 * `browser.history`. This file wraps both:
 *   - the router keeps seeing "/odoo/..." (nothing in Odoo has to change),
 *   - the address bar, history entries, reloads and bookmarks use "/<prefix>/...".
 *
 * It is prepended to web.assets_backend so it is evaluated before router.js.
 * The prefix comes from the web client page (views/web_templates.xml).
 */
import { browser } from "@web/core/browser/browser";

const prefix = String(window.odoo?.__mst_url_prefix__ || "").replace(/^\/+|\/+$/g, "");

if (prefix && prefix !== "odoo") {
    const publicRoot = `/${prefix}`;

    /** "/<prefix>/discuss" -> "/odoo/discuss" (what Odoo's router expects) */
    const toInternalPath = (path) => {
        if (path === publicRoot) {
            return "/odoo";
        }
        if (path.startsWith(`${publicRoot}/`)) {
            return "/odoo" + path.slice(publicRoot.length);
        }
        return path;
    };
    /** "/odoo/discuss" -> "/<prefix>/discuss" (what the user sees) */
    const toPublicPath = (path) => {
        if (path === "/odoo") {
            return publicRoot;
        }
        if (path.startsWith("/odoo/")) {
            return publicRoot + path.slice("/odoo".length);
        }
        return path;
    };
    /** Apply a path mapping to a same-origin URL (absolute or relative). */
    const mapUrl = (url, mapPath) => {
        if (url === undefined || url === null || url === "") {
            return url;
        }
        let parsed;
        try {
            parsed = new URL(String(url), window.location.href);
        } catch {
            return url;
        }
        if (parsed.origin !== window.location.origin) {
            return url;
        }
        parsed.pathname = mapPath(parsed.pathname);
        return parsed.href;
    };

    // ---- history: everything the router pushes is shown with the prefix ----
    const realHistory = window.history;
    browser.history = {
        pushState(state, title, url) {
            return realHistory.pushState(state, title, mapUrl(url, toPublicPath));
        },
        replaceState(state, title, url) {
            return realHistory.replaceState(state, title, mapUrl(url, toPublicPath));
        },
        back: () => realHistory.back(),
        forward: () => realHistory.forward(),
        go: (delta) => realHistory.go(delta),
        get state() {
            return realHistory.state;
        },
        get length() {
            return realHistory.length;
        },
        get scrollRestoration() {
            return realHistory.scrollRestoration;
        },
        set scrollRestoration(value) {
            realHistory.scrollRestoration = value;
        },
    };

    // ---- location: the router always reads the internal /odoo form ----
    const realLocation = window.location;
    // The proxy target is a plain object on purpose: window.location's own
    // properties (toString, assign, replace...) are non-configurable, so a proxy
    // around it may not return different values for them. Every read and write
    // is forwarded to the real location instead.
    const locationView = new Proxy({}, {
        get(_unused, key) {
            const target = realLocation;
            switch (key) {
                case "pathname":
                    return toInternalPath(target.pathname);
                case "href":
                    return mapUrl(target.href, toInternalPath);
                case "toString":
                case "valueOf":
                    return () => mapUrl(target.href, toInternalPath);
                case "assign":
                    return (url) => target.assign(mapUrl(url, toPublicPath));
                case "replace":
                    return (url) => target.replace(mapUrl(url, toPublicPath));
                default: {
                    const value = target[key];
                    return typeof value === "function" ? value.bind(target) : value;
                }
            }
        },
        set(_unused, key, value) {
            const target = realLocation;
            if (key === "href") {
                target.href = mapUrl(value, toPublicPath);
            } else if (key === "pathname") {
                target.pathname = toPublicPath(value);
            } else {
                target[key] = value;
            }
            return true;
        },
    });
    Object.defineProperty(browser, "location", {
        get() {
            return locationView;
        },
        set(value) {
            window.location = mapUrl(value, toPublicPath);
        },
        configurable: true,
    });

    // Opened through /odoo/... (server redirect, old bookmark, link in an email):
    // show the prefixed URL right away, without reloading the page.
    const shown = mapUrl(realLocation.href, toPublicPath);
    if (shown !== realLocation.href) {
        realHistory.replaceState(realHistory.state, "", shown);
    }
}
