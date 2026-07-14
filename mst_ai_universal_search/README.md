# AI Universal Search for Odoo 18

Natural-language search inside the **native Odoo 18 search bar**, powered by **OpenAI ChatGPT** and **Anthropic Claude AI**.

AI Universal Search enables users to search records using simple English instead of manually creating complex Odoo search domains and filters.

Normal Odoo search, filters, group by, favorites, and advanced search continue to work exactly as before. AI search is only activated when the search text starts with the prefix **`ai:`**.

---

# Features

- Natural language search inside the native Odoo search bar
- Powered by OpenAI ChatGPT
- Powered by Anthropic Claude AI
- Works with all standard Odoo list views
- Automatically generates Odoo search domains
- Automatically applies Group By when applicable
- AI Search History
- Secure API Key configuration
- Native Odoo user experience
- No changes to existing Odoo search functionality
- Fully compatible with Odoo 18

---

# Installation

1. Copy the **mst_ai_universal_search** module into your custom addons directory.

2. Restart the Odoo server.

3. Upgrade the module.

------

# Configure AI Providers

Navigate to

**AI Search → AI Providers**

Create one or more providers.

---

## OpenAI ChatGPT

| Field | Value |
|---------|---------|
| Provider | OpenAI |
| Model | gpt-4o |
| API Key | sk-xxxxxxxx |
| Base URL | Default |

---

## Anthropic Claude

| Field | Value |
|---------|---------|
| Provider | Claude |
| Model | claude-sonnet-4 |
| API Key | sk-ant-xxxxxxxx |
| Base URL | Default |

Click **Test Connection** to verify the API credentials.

---

# Selecting an AI Provider

If only one provider is active, every AI search will use that provider automatically.

If multiple providers are active, specify the provider in your search query.

Examples

```
ai:gpt employees who joined this month

ai:chatgpt attendance below 80 percent

ai:claude sales orders above 100000

ai:claude overdue customer invoices
```

Supported keywords

- gpt
- chatgpt
- openai
- claude

---

# Using AI Search

Open any List View.

Type your search into the standard Odoo search bar.

Examples

```
ai: employees who joined this month

ai: customers from Chennai

ai: attendance below 80 percent

ai: sales orders above 100000

ai: overdue invoices

ai: group employees by department
```

Press **Enter**.

The module will:

1. Send your query to ChatGPT or Claude.
2. Convert the request into an Odoo search domain.
3. Validate all generated fields.
4. Apply filters automatically.
5. Apply Group By if returned by AI.
6. Display matching records.

Without the **ai:** prefix, Odoo behaves exactly like the standard search.

---

# AI Search History

Every AI search is stored with

- Search Text
- AI Provider
- Odoo Model
- Generated Domain
- Generated Group By
- Search Time
- User

---

# Supported Applications

- Employees
- Attendance
- Leave
- Recruitment
- CRM
- Sales
- Purchase
- Inventory
- Accounting
- Manufacturing
- Projects
- Helpdesk
- Contacts
- Custom Models

---

# Security

The AI never executes Python code.

It only returns structured JSON.

Before applying the search:

- Every field is validated.
- Invalid fields are removed.
- Invalid domains are rejected.
- Only valid Odoo domains are applied.

---

# Internet Requirement

The Odoo server must have outbound internet access to:

### OpenAI

```
https://api.openai.com
```

### Anthropic Claude

```
https://api.anthropic.com
```

---

# Module Structure

```
mst_ai_universal_search/

├── __manifest__.py
├── controllers/
│   └── ai_search_controller.py
├── models/
│   ├── ai_provider.py
│   ├── ai_search_history.py
│   └── ai_service.py
├── security/
├── views/
├── static/
│   ├── src/js/search_bar_patch.js
│   ├── src/scss/ai_search.scss
│   └── description/
└── README.md
```

---

# Compatibility

- Odoo 18 Community
- Odoo 18 Enterprise

---

# Author

**Mind Spark Technologies**

Website

https://www.mindsparktechnologies.com