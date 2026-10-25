# Store Management — Odoo 19

A custom Odoo 19 module for managing a small retail store: products, stock, customers, and sales orders, with a customer portal for placing orders online.

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
- Ordered quantity must be greater than `0`
- The same product cannot be added twice to the same order (change its quantity instead)
- Order total computed automatically from the order lines (without taxes)
- Workflow buttons: **Confirm**, **Cancel**, **Reset to Draft**, **Print**
- Status bar: **Draft → Confirmed → Cancelled**
- Business rules:
  - A confirmed order can no longer be edited (enforced in Python, from any screen)
  - A cancelled order cannot be confirmed
  - Reset to Draft is only allowed from Cancelled
- Stock handling:
  - An order cannot be confirmed if any product's quantity is greater than its available stock
  - Confirming an order deducts the ordered quantities from stock
  - Cancelling a confirmed order returns the quantities to stock (cancelling a draft order does not change stock)
- Cancellation reason:
  - **Cancel** opens a pop-up with ready-made reasons: **Customer request**, **Wrong order details**, **Payment issue**, or **Other** (requires a written reason)
  - The reason is saved on the order, shown on the form, and posted in the chatter
  - Optional **Cancellation Reason** column in the orders list (hidden by default)
- Customer selection limited to store customers
- Search by order number, customer, and product
- Filters by status and order date, grouping by customer, status, and date

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

- Breadcrumbs on every page: **Home / Store Orders / …**
- **Live total**: the order total updates while the customer types, with thousands separators and the currency
- A quantity above the available stock turns the field red immediately, and the browser blocks submitting it
- Placing an order creates a store order and **confirms it directly**: the stock is deducted, the history is logged, and the confirmation email is sent
- If the order fails (for example not enough stock), nothing is saved and the page shows the error

Protection is applied on the server, not only in the page:

| Layer | Where | Purpose |
|---|---|---|
| Red field and live total | JavaScript in the browser | Guidance while typing only |
| Maximum quantity on the field | Browser | Stops the form from being submitted |
| Login required, own orders only, stock check | Python controller and model | The real protection |

- Every page requires login; a customer only ever sees their own store orders (another customer's order number redirects silently to the list)
- Products and orders are read with system rights, always filtered by the logged-in customer
- Order creation and confirmation run inside a savepoint, so a failed confirmation leaves no half-created order
- Forms include Odoo's CSRF token

To give a customer access: open the contact, then **Action → Grant portal access** (the contact needs an email, which becomes the login).

### Security

| Group | Access |
|---|---|
| **Store User** | Views and creates store orders (sees own orders only), confirms and cancels them. Read-only access to products, categories, and customers. Cannot delete orders. |
| **Store Manager** | Full access to products, customers, and orders (sees all orders), restock, low stock alerts, read-only stock history, and the **Configuration** menu. |

- Store Manager includes all Store User rights.
- Both groups include the matching Sales groups (**Own Documents** for Store User, **All Documents** for Store Manager), because store orders are built on `sale.order`.
- Store Manager can edit the store order sequence only; a record rule blocks edits to other sequences.
- Stock changes caused by a Store User confirming or cancelling an order are applied with system rights, and are still logged under that user's name.

## Tests

Automated tests in `tests/test_store_order.py` (14 tests) cover the main business rules:

| Area | What is tested |
|---|---|
| Order rules | Duplicate products are rejected; confirming more than the stock is rejected and nothing changes; a confirmed order cannot be modified |
| Stock | Confirming deducts the stock; cancelling a confirmed order restores it; cancelling a draft does not change it |
| Stock history | Initial stock, order confirmation, and manual changes are logged with the right type, quantity, stock after, and order |
| Low stock | The limit is exactly `5` (`6` is not low, `5` is) |
| Cancel wizard | A ready-made reason is saved and the stock is restored; **Other** with an empty reason is rejected |
| Restock wizard | Selected products are loaded, stock is added, and the reference is logged; no quantity is rejected |

Each test runs in a transaction that is rolled back, so the database is never changed. Run them with:

```bash
python odoo-bin -c odoo.conf -d <database> -u store_management --test-enable --test-tags /store_management --stop-after-init --no-http
```

The last result line should read `0 failed, 0 error(s) of 14 tests`.

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
│   └── store_restock_wizard_views.xml
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
  - **Order Sequence** — edit the `CMD/` numbering
  - **Store Team** — view users in the store groups
  - **Stock History** — view all stock movements

Store customers use the portal from the website: **My Account → Store Orders**.

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

## License

LGPL-3
