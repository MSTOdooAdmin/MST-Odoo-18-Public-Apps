/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { Domain } from "@web/core/domain";

const AI_PREFIX = "ai:";
// After "ai:", the text can optionally start with a provider hint word
// ("gpt", "claude", "gemini", ... or the exact Name of a configured
// provider) followed by a space, to force that provider for one query,
// e.g. "ai:claude sale orders above 100000". Parsing of the hint happens
// server-side (ai.service._split_provider_hint) so it stays in one place.

patch(SearchBar.prototype, {
    setup() {
        super.setup();
        this._aiNotification = useService("notification");
    },

    /**
     * Intercept Enter on the native search input. If the text starts with
     * "ai:" we route it to the AI backend instead of the normal search flow.
     * Anything else is handled by Odoo exactly as before.
     */
    async onSearchKeydown(ev) {
        const raw = (ev.target.value || "").trim();
        if (ev.key === "Enter" && raw.toLowerCase().startsWith(AI_PREFIX)) {
            ev.preventDefault();
            ev.stopPropagation();
            const query = raw.slice(AI_PREFIX.length).trim();
            if (query) {
                await this._runAiSearch(query, ev.target);
            }
            return;
        }
        return super.onSearchKeydown(...arguments);
    },

    async _runAiSearch(query, inputEl) {
        const searchModel = this.env.searchModel;
        const modelName = searchModel.resModel;
        const notif = this._aiNotification;

        let result;
        try {
            result = await rpc("/ai/search/domain", {
                model_name: modelName,
                query: query,
            });
        } catch {
            notif.add("AI search request failed. Check the server logs.", {
                type: "danger",
            });
            return;
        }

        if (!result || result.success === false) {
            notif.add((result && result.error) || "AI could not interpret the query.", {
                type: "danger",
                title: "AI Search",
            });
            return;
        }

        const domain = result.domain || [];
        const groupBy = result.group_by || [];

        if (domain.length) {
            const domainStr = new Domain(domain).toString();
            searchModel.createNewFilters([
                {
                    description: "AI: " + query,
                    domain: domainStr,
                    type: "filter",
                },
            ]);
        }

        for (const gb of groupBy) {
            const field = gb.split(":")[0];
            const known = searchModel.searchViewFields || {};
            if (known[field] && typeof searchModel.createNewGroupBy === "function") {
                try {
                    searchModel.createNewGroupBy(field);
                } catch {
                    // Ignore group by fields that cannot be grouped on this view.
                }
            }
        }

        if (inputEl) {
            inputEl.value = "";
        }
        if (this.state) {
            this.state.expanded = [];
            this.state.focusedIndex = 0;
        }

        const providerTag = result.provider_name ? `[${result.provider_name}] ` : "";
        notif.add(providerTag + (result.explanation || "AI filter applied."), {
            type: "success",
            title: "AI Search",
        });
    },
});
