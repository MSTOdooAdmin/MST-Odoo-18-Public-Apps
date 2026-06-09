/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class DynamicOne2ManyPreview extends Component {
    static template = "mst_dynamic_o2m_preview.DynamicOne2ManyPreview";

    static props = {
        ...standardFieldProps,
        options: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");

        this.state = useState({
            lines: [],
            loading: true,
            totalCount: 0,
        });

        onWillStart(async () => {
            await this.loadLines(this.props);
        });

        onWillUpdateProps(async (nextProps) => {
            await this.loadLines(nextProps);
        });
    }

    get options() {
        return this.props.options || {};
    }

    getColumns(props = this.props) {
        const options = props.options || {};
        const fields = options.fields || [];
        const labels = options.labels || fields;
        const wrapFields = options.wrap_fields || [];

        return fields.map((fieldName, index) => {
            return {
                name: fieldName,
                label: labels[index] || fieldName,
                wrap: wrapFields.includes(fieldName),
            };
        });
    }

    get columns() {
        return this.getColumns(this.props);
    }

    get maxRows() {
        return this.options.max_rows || 5;
    }

    get columnWidth() {
        return this.options.column_width || 140;
    }

    get wrapTextLength() {
        return this.options.wrap_text_length || 25;
    }

    get tableMinWidth() {
        const columnCount = this.columns.length || 1;
        return `${columnCount * this.columnWidth}px`;
    }

    get cellWidth() {
        return `${this.columnWidth}px`;
    }

    async loadLines(props) {
        this.state.loading = true;

        try {
            const parentModel =
                props.record?.resModel ||
                props.record?.model?.config?.resModel ||
                false;

            const parentId =
                props.record?.resId ||
                props.record?.data?.id ||
                false;

            const fieldName = props.name;
            const columns = this.getColumns(props);

            if (!parentModel || !parentId || !fieldName || !columns.length) {
                this.state.lines = [];
                this.state.totalCount = 0;
                this.state.loading = false;
                return;
            }

            const fieldsInfo = await this.orm.call(
                parentModel,
                "fields_get",
                [[fieldName]],
                {
                    attributes: ["relation", "type"],
                }
            );

            const relationModel = fieldsInfo?.[fieldName]?.relation;

            if (!relationModel) {
                this.state.lines = [];
                this.state.totalCount = 0;
                this.state.loading = false;
                return;
            }

            const parentData = await this.orm.call(
                parentModel,
                "read",
                [[parentId], [fieldName]]
            );

            const lineIds = parentData?.[0]?.[fieldName] || [];

            this.state.totalCount = lineIds.length;

            if (!lineIds.length) {
                this.state.lines = [];
                this.state.loading = false;
                return;
            }

            const fieldsToRead = columns.map((column) => column.name);

            this.state.lines = await this.orm.call(
                relationModel,
                "read",
                [lineIds.slice(0, this.maxRows), fieldsToRead]
            );

            this.state.loading = false;
        } catch (error) {
            console.error("Dynamic One2Many Preview Error:", error);

            if (error?.data?.message) {
                console.error("Odoo RPC Message:", error.data.message);
            }

            if (error?.data?.debug) {
                console.error("Odoo RPC Debug:", error.data.debug);
            }

            this.state.lines = [];
            this.state.totalCount = 0;
            this.state.loading = false;
        }
    }

    getCellValue(line, column) {
        const value = line[column.name];

        if (value === false || value === null || value === undefined) {
            return "";
        }

        if (Array.isArray(value)) {
            return value[1] || "";
        }

        if (typeof value === "object" && value.display_name) {
            return value.display_name;
        }

        return value;
    }

    shouldWrapCell(line, column) {
        const value = String(this.getCellValue(line, column) || "");

        if (column.wrap) {
            return true;
        }

        return value.length > this.wrapTextLength;
    }

    getCellClass(line, column) {
        return this.shouldWrapCell(line, column)
            ? "o_dynamic_o2m_cell o_dynamic_o2m_cell_wrap"
            : "o_dynamic_o2m_cell";
    }

    get hasMoreRecords() {
        return this.state.totalCount > this.maxRows;
    }

    get moreRecordsText() {
        const remaining = this.state.totalCount - this.maxRows;
        return `+${remaining} more`;
    }
}

registry.category("fields").add("dynamic_one2many_preview", {
    component: DynamicOne2ManyPreview,
    supportedTypes: ["one2many", "many2many"],
    extractProps: ({ options }) => ({
        options: options || {},
    }),
});