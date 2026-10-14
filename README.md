# Store Management — Odoo 19

A custom Odoo 19 module for managing a small retail store: products, customers, and sales orders.

This is a training project built to practice the core concepts of Odoo development: models, fields, views, menus, actions, relationships, computed fields, business rules, workflows, security, QWeb reports, wizards, and scheduled actions.

## Approach

Instead of creating new models from scratch, the module **extends Odoo's existing models** using `_inherit` (extension inheritance), adding or adjusting only what the store needs:

| Store concept | Extended model | What the module adds |
|---|---|---|
| Store Product | `product.template` | Stock quantity, low stock flag, daily low stock alert, unique reference, non-negative sales price |
| Product Category | `product.category` | Reused as is, with its own menu |
| Store Customer | `res.partner` | Store customer flag, store orders relation, orders count |
| Store Order | `sale.order` | `CMD/YYYY/NNNN` sequence, store total, store status, custom workflow, stock deduction, cancellation reason |
| Store Order Line | `sale.order.line` | Quantity rule, no duplicate products, sales price auto-fill |
| Cancel Wizard | `store.order.cancel.wizard` *(new transient model)* | Pop-up that asks for the cancellation reason |

Store records are kept separate from regular Sales records (`is_store_customer`, `is_store_order`), so the standard Sales app keeps working unchanged.

## Features

### Products
- Stock Quantity field (default `0`)
- **Low Stock** flag, set automatically when the stock is below `10` (the stock number turns red in the list)
- Reference is required and unique
- Sales Price cannot be negative
- List, Form, and Search views
- Filters: **Active** and **Low Stock**

### Customers
- Dedicated list and form for store customers only
- **Store Orders** tab on the customer form (One2many)
- Orders count per customer
- Search with filters (with / without orders, archived) and grouping by city and country

### Orders
- Automatic numbering: `CMD/2026/0001`, `CMD/2026/0002`, …
- Sales price filled automatically when a product is selected
- Ordered quantity must be greater than 0
- The same product cannot be added twice to the same order (change its quantity instead)
- Order total computed automatically from the order lines
- Workflow buttons: **Confirm**, **Cancel**, **Reset to Draft**
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
  - **Cancel** opens a pop-up (wizard) that requires a reason
  - The reason is saved on the order, shown on the form, and posted in the chatter
  - Optional **Cancellation Reason** column in the orders list (hidden by default)
- Customer selection limited to store customers
- Search by order number, customer, and product
- Filters by status and order date, grouping by customer, status, and date

### Low Stock Alert
A scheduled action (**Store: Low Stock Alert**) runs once a day:
- Creates a **warning activity** for every Store Manager on each low stock product
- Does not create duplicates while an alert for the same product is still open
- Marks old alerts as done automatically when the product's stock is back above the limit

To run it manually: **Settings → Technical → Scheduled Actions → Store: Low Stock Alert → Run Manually** (Developer Mode).

### PDF Report
A printable QWeb PDF report for each order, available from the **Print** button on the order form. It shows:
- Company logo and name (from the company's document layout)
- Order number, order date, and status
- Customer name, address, phone, and email
- Ordered products with quantity, unit price, and line subtotal
- Grand total

### Security

| Group | Access |
|---|---|
| **Store User** | Views and creates store orders (sees own orders only). Read-only access to products, categories, and customers. Cannot delete orders. |
| **Store Manager** | Full access to products, customers, and orders (sees all orders), plus the **Configuration** menu. |

- Store Manager includes all Store User rights.
- Both groups include the matching Sales groups (**Own Documents** for Store User, **All Documents** for Store Manager), because store orders are built on `sale.order`.
- Store Manager can edit the store order sequence only; a record rule blocks edits to other sequences.

## Module Structure

```
store_management/
├── __init__.py
├── __manifest__.py
├── security/
│   ├── security.xml
│   └── ir.model.access.csv
├── data/
│   ├── sequence.xml
│   └── cron.xml
├── models/
│   ├── __init__.py
│   ├── product_template.py
│   ├── res_partner.py
│   ├── sale_order.py
│   └── sale_order_line.py
├── wizard/
│   ├── __init__.py
│   ├── store_order_cancel_wizard.py
│   └── store_order_cancel_wizard_views.xml
├── report/
│   ├── order_report_templates.xml
│   └── order_report.xml
└── views/
    ├── product_views.xml
    ├── customer_views.xml
    ├── order_views.xml
    ├── config_views.xml
    └── menus.xml
```

## Requirements

- Odoo 19.0
- Depends on: `sale` (which brings in `product`, `sales_team`, and `base`)
- `wkhtmltopdf` installed on the server for PDF reports

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

To upgrade after changes:

```bash
python odoo-bin -c odoo.conf -d <database> -u store_management
```

## Usage

The **Store Management** app adds the following menus:

- **Products** — manage store products and stock
- **Categories** — manage product categories
- **Customers** — manage store customers and view their orders
- **Orders** — create, confirm, cancel, and print store orders
- **Configuration** *(Store Manager only)*
  - **Order Sequence** — edit the `CMD/` numbering
  - **Store Team** — view users in the store groups

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
- [x] Cancellation reason wizard

## License

LGPL-3
