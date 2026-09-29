import { registry } from "@web/core/registry";
import { Component, onWillStart, onWillUpdateProps, proxy, t, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * Odoo 20 / OWL 3 props schema.
 * OWL 3 ignores "static props"; props must be declared through useProps().
 */
export const dynamicOne2ManyPreviewProps = {
    ...standardFieldProps,
    options: t.object().optional({}),
};

export class DynamicOne2ManyPreview extends Component {
    static template = "mst_dynamic_o2m_preview.DynamicOne2ManyPreview";

    props = useProps(dynamicOne2ManyPreviewProps);

    setup() {
        this.orm = useService("orm");

        // OWL 3: "useState" was removed, reactive state is created with proxy().
        this.state = proxy({
            lines: [],
            loading: true,
            totalCount: 0,
        });

        // Incremented on every load so a slow, outdated RPC never overwrites newer data.
        this._loadToken = 0;

        onWillStart(() => this.loadLines(this.props));
        onWillUpdateProps((nextProps) => this.loadLines(nextProps));
    }

    // ----------------------------------------------------------------------
    // Options (computed from a given props object so they are also correct
    // for "nextProps" inside onWillUpdateProps)
    // ----------------------------------------------------------------------

    getOptions(props = this.props) {
        return props.options || {};
    }

    getColumns(props = this.props) {
        const options = this.getOptions(props);
        const fields = options.fields || [];
        const labels = options.labels || fields;
        const wrapFields = options.wrap_fields || [];

        return fields.map((fieldName, index) => ({
            name: fieldName,
            label: labels[index] || fieldName,
            wrap: wrapFields.includes(fieldName),
        }));
    }

    getMaxRows(props = this.props) {
        return this.getOptions(props).max_rows || 5;
    }

    get options() {
        return this.getOptions();
    }

    get columns() {
        return this.getColumns();
    }

    get maxRows() {
        return this.getMaxRows();
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

    // ----------------------------------------------------------------------
    // Data loading
    // ----------------------------------------------------------------------

    _setEmpty() {
        this.state.lines = [];
        this.state.totalCount = 0;
        this.state.loading = false;
    }

    async _getRelationModel(parentModel, fieldName, record) {
        // The relation is already known by the record: no extra RPC needed.
        const relation = record?.fields?.[fieldName]?.relation;
        if (relation) {
            return relation;
        }
        const fieldsInfo = await this.orm.call(parentModel, "fields_get", [[fieldName]], {
            attributes: ["relation", "type"],
        });
        return fieldsInfo?.[fieldName]?.relation || false;
    }

    async loadLines(props) {
        const token = ++this._loadToken;
        const isCurrent = () => token === this._loadToken;

        this.state.loading = true;

        try {
            const record = props.record;
            const parentModel = record?.resModel || record?.model?.config?.resModel || false;
            const parentId = record?.resId || record?.data?.id || false;
            const fieldName = props.name;
            const columns = this.getColumns(props);
            const maxRows = this.getMaxRows(props);

            if (!parentModel || !parentId || !fieldName || !columns.length) {
                if (isCurrent()) {
                    this._setEmpty();
                }
                return;
            }

            const relationModel = await this._getRelationModel(parentModel, fieldName, record);
            if (!isCurrent()) {
                return;
            }
            if (!relationModel) {
                this._setEmpty();
                return;
            }

            const parentData = await this.orm.call(parentModel, "read", [[parentId], [fieldName]]);
            if (!isCurrent()) {
                return;
            }

            const lineIds = parentData?.[0]?.[fieldName] || [];
            if (!lineIds.length) {
                this._setEmpty();
                return;
            }

            const fieldsToRead = columns.map((column) => column.name);
            const lines = await this.orm.call(relationModel, "read", [
                lineIds.slice(0, maxRows),
                fieldsToRead,
            ]);
            if (!isCurrent()) {
                return;
            }

            this.state.totalCount = lineIds.length;
            this.state.lines = lines;
            this.state.loading = false;
        } catch (error) {
            console.error("Dynamic One2Many Preview Error:", error);
            if (error?.data?.message) {
                console.error("Odoo RPC Message:", error.data.message);
            }
            if (error?.data?.debug) {
                console.error("Odoo RPC Debug:", error.data.debug);
            }
            if (isCurrent()) {
                this._setEmpty();
            }
        }
    }

    // ----------------------------------------------------------------------
    // Rendering helpers
    // ----------------------------------------------------------------------

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
        return String(value);
    }

    shouldWrapCell(line, column) {
        if (column.wrap) {
            return true;
        }
        return this.getCellValue(line, column).length > this.wrapTextLength;
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

export const dynamicOne2ManyPreview = {
    component: DynamicOne2ManyPreview,
    supportedTypes: ["one2many", "many2many"],
    extractProps: ({ options }) => ({
        options: options || {},
    }),
};

registry.category("fields").add("dynamic_one2many_preview", dynamicOne2ManyPreview);
