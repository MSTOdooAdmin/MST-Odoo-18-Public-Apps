/** @odoo-module **/

import { Component, onWillStart, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";

export class AdvancedLoginHistoryDashboard extends Component {
    static template = "mst_advanced_login_history.AdvancedLoginHistoryDashboard";

    setup() {
        this.action = useService("action");
        this.state = proxy({
            loading: true,
            error: false,
            cards: [],
            rows: [],
            location: {},
            recent_activity: [],
            summary: {},
        });

        onWillStart(() => this.loadDashboardData());
    }

    async loadDashboardData() {
        this.state.loading = true;
        this.state.error = false;
        try {
            const result = await rpc("/mst_advanced_login_history/dashboard_data", {});
            this.state.cards = result.cards || [];
            this.state.rows = result.rows || [];
            this.state.location = result.location || {};
            this.state.recent_activity = result.recent_activity || [];
            this.state.summary = result.summary || {};
        } catch (error) {
            this.state.error = true;
        } finally {
            this.state.loading = false;
        }
    }

    refreshDashboard() {
        return this.loadDashboardData();
    }

    openCard(card) {
        if (!card || !card.model) {
            return;
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: card.title,
            res_model: card.model,
            domain: card.domain || [],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openLoginRecord(row) {
        if (!row || !row.res_model || !row.res_id) {
            return;
        }
        return this.action.doAction({
            type: "ir.actions.act_window",
            name: row.status || "Audit Detail",
            res_model: row.res_model,
            res_id: row.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openMap() {
        if (this.state.location && this.state.location.open_url) {
            window.open(this.state.location.open_url, "_blank", "noopener,noreferrer");
        }
    }
}

registry.category("actions").add(
    "mst_advanced_login_history.dashboard",
    AdvancedLoginHistoryDashboard
);
