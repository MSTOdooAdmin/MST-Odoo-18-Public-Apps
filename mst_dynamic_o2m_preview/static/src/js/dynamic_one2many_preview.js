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

    get columns() {
        const fields = this.options.fields || [];
        const labels = this.options.labels || fields;
        const wrapFields = this.options.wrap_fields || [];

        return fields.map((fieldName, index) => {
            return {
                name: fieldName,
                label: labels[index] || fieldName,
                wrap: wrapFields.includes(fieldName),
            };
        });
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
                props.record.resModel ||
                props.record.model?.config?.resModel ||
                false;

            const parentId =
                props.record.resId ||
                props.record.data?.id ||
                false;

            const fieldName = props.name;
            const columns = this.columns;

            if (!parentModel || !parentId || !fieldName || !columns.length) {
                this.state.lines = [];
                this.state.totalCount = 0;
                this.state.loading = false;
                return;
            }

            const fieldsInfo = await this.orm.call(
                parentModel,
                "fields_get",
                [[fieldName], ["relation", "type"]]
            );

            const relationModel = fieldsInfo?.[fieldName]?.relation;

            if (!relationModel) {
                this.state.lines = [];
                this.state.totalCount = 0;
                this.state.loading = false;
                return;
            }

            const parentData = await this.orm.read(
                parentModel,
                [parentId],
                [fieldName]
            );

            const lineIds = parentData?.[0]?.[fieldName] || [];
            this.state.totalCount = lineIds.length;

            if (!lineIds.length) {
                this.state.lines = [];
                this.state.loading = false;
                return;
            }

            const fieldsToRead = columns.map((column) => column.name);

            this.state.lines = await this.orm.read(
                relationModel,
                lineIds.slice(0, this.maxRows),
                fieldsToRead
            );

            this.state.loading = false;
        } catch (error) {
            console.error("Dynamic One2Many Preview Error:", error);
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
    extractProps: ({ options }) => ({
        options: options || {},
    }),
});