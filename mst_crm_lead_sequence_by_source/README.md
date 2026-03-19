# CRM Lead Sequence by Source

Generate CRM Lead sequence numbers based on Lead Source (UTM Source).

## Features
- Adds **Lead Prefix** field in **Lead Source (UTM Source)**.
- Creates a dedicated sequence per Lead Source automatically.
- Assigns Lead sequence during lead creation.
- Falls back to default `crm.lead` sequence when source is not set.

## Configuration
1. Go to **CRM → Configuration → Lead Sources**
2. Open any Lead Source
3. Set **Lead Prefix** (Example: `FB-`, `GG-`, `REF-`)

## Usage
- Create a new Lead with Lead Source selected.
- The Lead will get a sequence number based on that source.

## Compatibility
- Odoo 18.0
- CRM + UTM installed
