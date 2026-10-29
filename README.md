# Store Management — Odoo 19

A custom Odoo 19 module for managing a small retail store: products, stock, customers, and sales orders, with a customer portal for placing, paying for, and cancelling orders online.

This is a training project built to practice the core concepts of Odoo development: models, fields, views, menus, actions, relationships, computed fields, business rules, workflows, security, QWeb reports, wizards, scheduled actions, email templates, translations, automated tests, portal controllers, and frontend JavaScript.

## Approach

The module **extends Odoo's existing models** using `_inherit` (extension inheritance), adding only what the store needs, and creates new models only where nothing suitable exists:

| Store concept | Model | What the module adds |
|---|---|---|
| Store Product | `product.template` *(extended)* | Stock quantity, low stock flag, unique reference, non-negative sales price, automatic stock history |
| Product Category | `product.category` *(reused)* | Its own menu |
| Store Customer | `res.partner` *(extended)* | Store customer flag, store orders, orders count, smart button |
| Store Order | `sale.order` *(extended)* | `CMD/YYYY/NNNN` sequence, store total, store status, custom workflow, stock deduction, confirmation email, cancellation reason |
| Store Order Line | `sale.order.line` *(extended)* | Quantity rule, no duplicate products, sales price auto-fill |
| Stock History | `store.stock.history` *(new)* | Read-only log of every stock change |
| Cancel Wizard | `store.order.cancel.wizard` *(new, transient)* | Pop-up that asks for the cancellation reason |
| Restock Wizard | `store.restock.wizard` + `store.restock.wizard.line` *(new, transient)* | Pop-up to add received quantities to several products at once |
| Store Settings | `store.settings.wizard` *(new, transient)* | Pop-up where the Store Manager sets the daily portal order limit |

The customer portal is built on Odoo's `portal` module: a controller that inherits `CustomerPortal`, QWeb page templates, and one frontend JavaScript interaction.

Store records are kept separate from regular Sales records (`is_store_customer`, `is_store_order`), and all store screens are standalone views, so the standard Sales app keeps working unchanged.

## Features

### Products
- **Stock Quantity** field (default `0`)
- **Low Stock** flag, computed automatically when the stock is `5` or less; the stock number turns red in the list
- Reference is required and unique
- Sales Price cannot be negative
- List, **Kanban** (cards with image, price, stock, and a red *Low Stock* badge), Form, and Search views
- Filters: **Active** (default) and **Low Stock (≤ 5)**
- **Restock** button on the form and **Restock** action on the list *(Store Manager only)*
- **Stock History** tab on the form *(Store Manager only)*

### Restock
- Select one or more products and open **Restock** from the Actions menu (or the button on the form)
- One line per product with its current stock; enter the quantity received
- Optional **Reference** (e.g. a supplier invoice number), saved in the stock history
- Lines left at `0` are skipped; negative quantities are rejected

### Stock History
Every change to a product's stock is logged automatically, from one place (the product's `create` and `write` methods):

| Type | When | Quantity |
|---|---|---|
| **Initial Stock** | A product is created with stock | Positive |
| **Restock** | Stock is added with the Restock wizard | Positive |
| **Order Confirmed** | A store order is confirmed | Negative |
| **Order Cancelled** | A confirmed order is cancelled | Positive |
| **Manual Adjustment** | The stock is edited by hand | Positive or negative |

- Each entry shows the date, product, type, quantity, stock after the change, related order, reference, and user
- Available from **Configuration → Stock History** and from the **Stock History** tab on the product form
- Search by product, order, and reference; filters by type and date; grouping by product and type
- **Read-only for everyone**, including managers, so the log can be trusted; entries are created by the system only

### Low Stock Alert
A scheduled action (**Store: Low Stock Alert**) runs once a day:
- Creates a **warning activity** for every Store Manager on each low stock product
- Does not create duplicates while an alert for the same product is still open
- Marks old alerts as done automatically when the product's stock is back above the limit

To run it manually: **Settings → Technical → Scheduled Actions → Store: Low Stock Alert → Run Manually** (Developer Mode).

### Customers
- Dedicated list and form for store customers only
- **Store Orders** smart button: opens the customer's orders with all order views (list, form, graph, pivot)
- **Store Orders** tab on the customer form, opened first by default
- Search with filters (with / without orders, archived) and grouping by city and country

### Orders
- Automatic numbering: `CMD/2026/0001`, `CMD/2026/0002`, …
- Sales price filled automatically when a product is selected
- Ordered quantity must be a whole number greater than `0`
- The same product cannot be added twice to the same order (change its quantity instead)
- Order total computed automatically from the order lines (without taxes)
- Workflow buttons: **Register Payment**, **Confirm**, **Cancel**, **Reset to Draft**, **Print**
- Status bar: **Draft → Confirmed → Cancelled**
- Business rules:
  - A confirmed order can no longer be edited (enforced in Python, from any screen)
  - The lines of a confirmed order cannot be changed, added, or removed, even directly on the line
  - Store buttons (**Confirm**, **Cancel**, **Reset to Draft**) work on store orders only
  - A cancelled order cannot be confirmed
  - Reset to Draft is only allowed from Cancelled
- Stock handling:
  - Built into Odoo's own confirm and cancel methods, so it applies from any route: the store buttons, the Sales app, the cancel pop-ups, or an external integration
  - An order cannot be confirmed if any product's quantity is greater than its available stock
  - Confirming an order deducts the ordered quantities from stock
  - Cancelling a confirmed order returns the quantities to stock (cancelling a draft order does not change stock)
- Payment *(test payment, no real money)*:
  - **Payment Status** on every order: **Not Paid**, **Paid**, or **Refunded**, shown as a colored badge in the form, the list, and the portal
  - An order must be **paid before it can be confirmed**, from any route (store buttons, Sales app, or integration)
  - Customers pay on the portal when they place an order; staff use **Register Payment** for payments received in the store (e.g. orders created in the back office)
  - Cancelling a paid order marks it **Refunded** automatically, from any cancel route
  - Resetting a refunded order to draft sets it back to **Not Paid**, so it must be paid again
  - Every payment and refund is posted in the chatter with the amount and the user
- Cancellation reason:
  - **Cancel** opens a pop-up with ready-made reasons: **Customer request**, **Wrong order details**, **Payment issue**, or **Other** (requires a written reason)
  - The reason is saved on the order, shown on the form, and posted in the chatter
  - Optional **Cancellation Reason** column in the orders list (hidden by default)
- Store orders cannot be signed or paid online, so a customer can never confirm one from the standard sales portal page
- Customer selection limited to store customers
- Search by order number, customer, and product
- Filters by status, payment status (**Not Paid**, **Paid**, **Refunded**), and order date, grouping by customer, status, and date

### Sales Analysis
- **Graph** view: store sales per month (bar chart, can be switched to line or pie)
- **Pivot** view: customers in rows, months in columns, store total in cells
- Both work with all order filters and groupings (e.g. apply **Confirmed** to see actual sales only)

### Confirmation Email
- When a store order is confirmed, the customer receives an email with the order number, the ordered products, and the total
- The PDF order report is attached automatically
- The email is posted in the order's chatter
- Sent only if the customer has an email address; confirmation is never blocked by email
- Sent in the customer's language (the **Language** set on the customer)
- The template (**Store: Order Confirmed**) can be edited from **Settings → Technical → Email Templates**

> An outgoing mail server must be configured for emails to actually be delivered. Without one, emails are still created and visible in the chatter and in **Settings → Technical → Emails**.

### PDF Report
A printable QWeb PDF report for each order, available from the **Print** button on the order form and attached to the confirmation email. It shows:
- Company logo and name (from the company's document layout)
- Order number, order date, and status
- Customer name, address, phone, and email
- Ordered products with quantity, unit price, and line subtotal
- Grand total

### Arabic Translation
- Full Arabic translation in `i18n/ar.po`: menus, fields, buttons, statuses, filters, error messages, the PDF report, the confirmation email, and the portal pages
- Install Arabic from **Settings → Languages**, then choose it in the user's preferences; the interface switches to right-to-left
- Each user sees the module in their own language; each customer receives emails in theirs
- On the website, the portal language comes from the URL (e.g. `/ar/my/store/orders`) or the language selector; Arabic must be added to the website's languages

To update after adding new texts: export a new template from **Settings → Translations → Export Translation** (format **PO**, app **Store Management**), translate the new entries in `ar.po`, and upgrade the module.

### Customer Portal
Store customers with portal access can log in to the website and manage their own orders at `/my/store/orders`.

| Page | URL | What it shows |
|---|---|---|
| Portal home | `/my` | A **Store Orders** card (the standard **Sales Orders** card is hidden) |
| Store Orders | `/my/store/orders` | The customer's store orders with number, date, total, and colored status, plus a **New Order** button |
| Order | `/my/store/orders/<id>` | Order date, status, cancellation reason (if any), ordered products, total, and **Download PDF** |
| New Order | `/my/store/orders/new` | Products in stock with price and available quantity, and a quantity field for each |
| Payment | `/my/store/orders/<id>/pay` | Test payment page: order number, amount, **Pay Now** and **Pay Later** (unpaid drafts only) |

Order flow:

| Step | Who | Result |
|---|---|---|
| Place an order | Customer, on the portal | A **draft**, **Not Paid** store order. Stock is checked but not deducted. The customer is taken to the payment page |
| Pay | Customer, with **Pay Now** (right away, or later from the order page) | The order is **Paid** |
| Confirm | Store User or Store Manager, in the back office | Paid orders only. Stock is deducted, the history is logged, and the confirmation email is sent |
| Cancel a draft | Customer, with **Cancel Order** on the order page | The order is cancelled with the reason *Cancelled by the customer from the portal.*; a paid order is **Refunded** |
| Cancel | Store User or Store Manager, with the cancel wizard | Draft or confirmed; a confirmed order returns its stock, and a paid order is **Refunded** |

- Breadcrumbs on every page: **Home / Store Orders / …**
- **Live total**: the order total updates while the customer types, with thousands separators and the currency
- A quantity above the available stock turns the field red immediately, and the browser blocks submitting it
- Placing an order creates a **draft** store order; the stock is checked again when staff confirm it, because a draft does not reserve stock
- A customer can only cancel their own **draft** orders; confirmed orders are cancelled by staff
- The payment page clearly says it is a test payment; it has no card fields and charges nothing
- Paying is a form submission (`POST`) to its own URL; opening the payment page of an order that cannot be paid redirects to the order
- **Daily limit**: a customer can place up to `5` orders in 24 hours (cancelled orders count too; orders created by staff for the customer do not)
- If the order fails (not enough stock, or the daily limit is reached), nothing is saved and the page shows the error

Protection is applied on the server, not only in the page:

| Layer | Where | Purpose |
|---|---|---|
| Red field and live total | JavaScript in the browser | Guidance while typing only |
| Maximum quantity on the field | Browser | Stops the form from being submitted |
| Login required, own orders only, stock check, draft-only cancel, daily limit | Python controller and model | The real protection |

- Every page requires login; a customer only ever sees their own store orders (another customer's order number redirects silently to the list)
- Products and orders are read with system rights, always filtered by the logged-in customer
- Order creation and the stock check run inside a savepoint, so a rejected order leaves nothing behind
- Placing and cancelling orders accept form submissions only (`POST`)
- Forms include Odoo's CSRF token

To give a customer access: open the contact, then **Action → Grant portal access** (the contact needs an email, which becomes the login).

### Store Settings
**Configuration → Store Settings** *(Store Manager only)* opens a pop-up with one setting:

| Setting | Default | Meaning |
|---|---|---|
| **Portal Orders per Customer in 24 Hours** | `5` | Maximum portal orders per customer in the last 24 hours; `0` means no limit |

- The value is stored as the system parameter `store_management.daily_order_limit` and is kept on module upgrades
- The Store Manager has no access to system parameters: the pop-up reads and writes this one key only, with system rights
- If the parameter is missing or invalid, the default `5` is used

### Security

| Group | Access |
|---|---|
| **Store User** | Views and creates store orders (sees own orders only), confirms and cancels them. Read-only access to products, categories, and customers. Cannot delete orders. |
| **Store Manager** | Full access to products, customers, and orders (sees all orders), restock, low stock alerts, read-only stock history, store settings, and the **Configuration** menu. |

- Store Manager includes all Store User rights.
- Both groups include the matching Sales groups (**Own Documents** for Store User, **All Documents** for Store Manager), because store orders are built on `sale.order`.
- Store Manager can edit the store order sequence only; a record rule blocks edits to other sequences.
- Stock changes caused by a Store User confirming or cancelling an order are applied with system rights, and are still logged under that user's name.

## Tests

Automated tests in `tests/test_store_order.py` (29 tests) cover the main business rules:

| Area | What is tested |
|---|---|
| Order rules | Duplicate products are rejected; confirming more than the stock is rejected and nothing changes; a confirmed order cannot be modified; fractional quantities are rejected |
| Confirmed lines | A line quantity cannot be changed, a line cannot be added or deleted |
| Regular orders | Store confirm and cancel reject a regular sales order and leave the stock unchanged |
| Standard routes | Odoo's own confirm checks and deducts the stock, and its cancel restores it; store orders cannot be signed or paid |
| Payment | Paying marks the order paid and cannot happen twice; an unpaid order cannot be confirmed from any route; cancelling a paid order refunds it, an unpaid one stays unpaid; a refunded order reset to draft needs payment again |
| Stock | Confirming deducts the stock; cancelling a confirmed order restores it; cancelling a draft does not change it |
| Stock history | Initial stock, order confirmation, and manual changes are logged with the right type, quantity, stock after, and order |
| Low stock | The limit is exactly `5` (`6` is not low, `5` is) |
| Cancel wizard | A ready-made reason is saved and the stock is restored; **Other** with an empty reason is rejected |
| Restock wizard | Selected products are loaded, stock is added, and the reference is logged; no quantity is rejected |

Each test runs in a transaction that is rolled back, so the database is never changed. Run them with:

```bash
python odoo-bin -c odoo.conf -d <database> -u store_management --test-enable --test-tags /store_management --stop-after-init --no-http
```

The last result line should read `0 failed, 0 error(s) of 29 tests`.

## Module Structure

```
store_management/
├── __init__.py
├── __manifest__.py
├── security/
│   ├── security.xml
│   └── ir.model.access.csv
├── controllers/
│   ├── __init__.py
│   └── portal.py
├── static/
│   └── src/
│       └── js/
│           └── store_order_total.js
├── i18n/
│   ├── ar.po
│   └── store_management.pot
├── data/
│   ├── sequence.xml
│   ├── cron.xml
│   ├── config_parameter.xml
│   └── mail_template.xml
├── models/
│   ├── __init__.py
│   ├── product_template.py
│   ├── res_partner.py
│   ├── sale_order.py
│   ├── sale_order_line.py
│   └── store_stock_history.py
├── wizard/
│   ├── __init__.py
│   ├── store_order_cancel_wizard.py
│   ├── store_order_cancel_wizard_views.xml
│   ├── store_restock_wizard.py
│   ├── store_restock_wizard_views.xml
│   ├── store_settings_wizard.py
│   └── store_settings_wizard_views.xml
├── tests/
│   ├── __init__.py
│   └── test_store_order.py
├── report/
│   ├── order_report_templates.xml
│   └── order_report.xml
└── views/
    ├── product_views.xml
    ├── customer_views.xml
    ├── order_views.xml
    ├── config_views.xml
    ├── stock_history_views.xml
    ├── menus.xml
    └── portal_templates.xml
```

## Requirements

- Odoo 19.0
- Depends on: `sale` (which brings in `product`, `sales_team`, `mail`, and `base`) and `portal`
- The **Website** app is optional; with it, the portal uses the website layout and language selector
- `wkhtmltopdf` installed on the server for PDF reports
- An outgoing mail server, only if confirmation emails should actually be delivered

## Installation

1. Clone this repository into your custom addons folder:
   ```bash
   git clone https://github.com/aymangh-0/store_management store_management
   ```
2. Make sure the folder is listed in `addons_path` in your Odoo configuration file.
3. Restart the Odoo server.
4. Enable **Developer Mode**, go to **Apps**, and click **Update Apps List**.
5. Search for **Store Management** and click **Install**.
6. Assign users to **Store User** or **Store Manager** from **Settings → Users** (under the **Sales** section).

To upgrade after changes (restart the server this way whenever Python files are added or changed):

```bash
python odoo-bin -c odoo.conf -d <database> -u store_management
```

## Usage

The **Store Management** app adds the following menus:

- **Products** — manage store products, stock, and restocking
- **Categories** — manage product categories
- **Customers** — manage store customers and view their orders
- **Orders** — create, confirm, cancel, print, and analyze store orders
- **Configuration** *(Store Manager only)*
  - **Store Settings** — set the daily portal order limit
  - **Order Sequence** — edit the `CMD/` numbering
  - **Store Team** — view users in the store groups
  - **Stock History** — view all stock movements

Store customers use the portal from the website: **My Account → Store Orders**. Their orders arrive as drafts in **Orders**, to be confirmed by staff.

## Known Limitations

These are deliberate simplifications for a training project:

| Topic | Current behavior |
|---|---|
| Taxes | The store total excludes taxes, while Odoo's own total includes them |
| Price lists | The sales price is filled directly from the product, so price lists are not applied in the back office |
| Units of measure | Quantities are counted in the product's unit; other units (e.g. dozens) are not converted |
| Variants | Stock is kept on the product template, shared by all its variants |
| Confirming several orders at once | Each line is checked against the current stock, so confirming several orders in one call could exceed it |
| Locked orders setting | If Sales is set to lock confirmed orders, cancelling a confirmed store order is blocked by Odoo |
| Unique reference | Applies to all products in the database, not only store products |
| Daily limit | Counted before the order is created, so two orders at the exact same moment could both pass |
| Multi-company | The portal lists products without a company filter |
| Payment | A test payment only: no payment provider, no invoice, and no accounting entries |
| Orders before the payment feature | Existing orders start as **Not Paid**, including confirmed ones; they can be marked paid once from the Odoo shell |

## Roadmap

- [x] Product management
- [x] Customer management
- [x] Order management, sequence, and workflow
- [x] Orders search view (filters by status and customer)
- [x] QWeb PDF report for orders
- [x] Security groups: **Store User** and **Store Manager**
- [x] No duplicate products in the same order
- [x] Stock deduction on confirm and restore on cancel
- [x] Low stock flag
- [x] Daily low stock alert (scheduled action)
- [x] Cancellation reason wizard with ready-made reasons
- [x] Stock history log
- [x] Restock wizard
- [x] Graph and pivot views for orders
- [x] Store orders smart button on customers
- [x] Kanban view for products
- [x] Confirmation email with the PDF report attached
- [x] Arabic translation, with emails in the customer's language
- [x] Automated tests
- [x] Customer portal: order list, order details, PDF download, and new orders
- [x] Live order total in the portal (frontend JavaScript)
- [x] Portal orders arrive as drafts and are confirmed by staff
- [x] Customers can cancel their draft orders from the portal
- [x] Daily portal order limit per customer, set by the Store Manager
- [x] Test payment: customers pay when ordering, staff confirm paid orders only, refunds on cancel
- [x] Code review fixes: stock in Odoo's own confirm and cancel, locked confirmed lines, whole quantities, no online signing or payment

## License

LGPL-3
