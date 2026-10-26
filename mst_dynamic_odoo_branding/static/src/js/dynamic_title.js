/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const dynamicBrandingService = {
    async start() {
        let brandName = "";
        try {
            const config = await rpc("/mst_dynamic_odoo_branding/config", {});
            brandName = (config && config.brand_name) || "";
        } catch {
            return;
        }
        if (!brandName) {
            return;
        }

        const applyBrandTitle = () => {
            if (document.title !== brandName) {
                document.title = brandName;
            }
        };

        applyBrandTitle();

        const titleElement = document.querySelector("title");
        if (titleElement) {
            const observer = new MutationObserver(applyBrandTitle);
            observer.observe(titleElement, {
                childList: true,
                subtree: true,
                characterData: true,
            });
        }
    },
};

registry.category("services").add("mst_dynamic_branding", dynamicBrandingService);
