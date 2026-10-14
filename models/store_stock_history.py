from odoo import fields, models


class StoreStockHistory(models.Model):
    _name = "store.stock.history"
    _description = "Store Stock History"
    _order = "date desc, id desc"

    date = fields.Datetime(
        default=fields.Datetime.now, required=True, readonly=True
    )
    product_id = fields.Many2one(
        'product.template', string="Product",
        required=True, ondelete='cascade', readonly=True,
    )
    move_type = fields.Selection(
        selection=[
            ('initial', 'Initial Stock'),
            ('order_confirm', 'Order Confirmed'),
            ('order_cancel', 'Order Cancelled'),
            ('manual', 'Manual Adjustment'),
        ],
        string="Type", required=True, readonly=True,
    )

    quantity = fields.Integer(readonly=True)
    stock_after = fields.Integer(string="Stock After", readonly=True)
    order_id = fields.Many2one(
        'sale.order', string="Order", ondelete='set null', readonly=True
    )
    user_id = fields.Many2one(
        'res.users', string="User",
        default=lambda self: self.env.user, readonly=True,
    )