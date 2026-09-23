# Field Highlight Widget - Odoo 19

Developer-only frontend widget. There are no configuration models, menus, security records, or database rules.

## Basic color

Use a hex color code directly in `color`:

```xml
<field name="name"
       widget="field_highlight"
       options="{'color': '#FFF3CD'}"/>
```

The widget automatically selects readable light/dark text for a direct hex color code.

By default the same highlight is also applied to the field label. To highlight only the field value, use:

```xml
<field name="name"
       widget="field_highlight"
       options="{
           'color': '#FFF3CD',
           'highlight_label': False
       }"/>
```

## Custom colors

```xml
<field name="amount_total"
       widget="field_highlight"
       options="{
           'background_color': '#FFF3CD',
           'text_color': '#664D03',
           'border_color': '#FFC107',
           'bold': True,
           'border_width': 1,
           'border_radius': 8,
           'padding_x': 8,
           'padding_y': 4
       }"/>
```

## Conditional highlight using current field value

```xml
<field name="state"
       widget="field_highlight"
       options="{
           'operator': 'equal',
           'comparison_value': 'done',
           'color': '#198754',
           'bold': True
       }"/>
```

Operators:
- `always`
- `equal`
- `not_equal`
- `contains`
- `not_contains`
- `empty`
- `not_empty`
- `greater`
- `greater_equal`
- `less`
- `less_equal`
- `in`
- `not_in`

For `in` / `not_in`, use a comma-separated `comparison_value`.

## Multiple colors by field value

```xml
<field name="state"
       widget="field_highlight"
       options="{
           'value_colors': {
               'draft': '#6C757D',
               'confirmed': '#0D6EFD',
               'done': '#198754',
               'cancel': '#DC3545'
           },
           'bold': True
       }"/>
```

A value can also use custom style options:

```xml
<field name="state"
       widget="field_highlight"
       options="{
           'value_colors': {
               'draft': {
                   'background_color': '#F1F3F5',
                   'text_color': '#343A40',
                   'border_color': '#CED4DA'
               },
               'done': {
                   'background_color': '#D1E7DD',
                   'text_color': '#0F5132',
                   'border_color': '#BADBCC',
                   'bold': True
               }
           }
       }"/>
```

## Edit / readonly mode

```xml
<field name="state"
       widget="field_highlight"
       options="{
           'color': '#0D6EFD',
           'apply_mode': 'readonly'
       }"/>
```

Allowed values: `both`, `edit`, `readonly`.

## Preserve another Odoo widget

Use `base_widget` when the field must retain a special underlying widget:

```xml
<field name="partner_id"
       widget="field_highlight"
       options="{
           'base_widget': 'many2one_avatar',
           'color': '#0D6EFD'
       }"/>
```

## Use with Odoo statusbar and statusbar_visible

Do not add two `widget` attributes. Keep `field_highlight` as the outer widget and set `statusbar` as `base_widget`:

```xml
<field name="state"
       widget="field_highlight"
       statusbar_visible="draft,confirmed,done"
       options="{
           'base_widget': 'statusbar',
           'value_colors': {
               'draft': '#6C757D',
               'confirmed': '#0D6EFD',
               'done': '#198754',
               'cancel': '#DC3545'
           },
           'bold': True
       }"/>
```

The `statusbar_visible` attribute is preserved and its sequence is used as the exact left-to-right workflow order by this widget. This intentionally differs from native Odoo 19, which normally takes the ordering from the selection field definition.

For `base_widget: 'statusbar'`, `value_colors` highlights only the current statusbar state using its actual technical selection value. The mapping key must exactly match the value stored by the field (for example `cancel` and `cancelled` are different values).

The highlight widget wraps the normal Odoo field renderer; it does not change the stored field value.
