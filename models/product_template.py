from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    store_stock_qty = fields.Integer(
        string="Stock Quantity",
        default=0,
    )

    store_is_low_stock = fields.Boolean(
        string="Low Stock",
        compute="_compute_store_is_low_stock",
        store=True,
    )

    _default_code_unique = models.Constraint(
        'unique(default_code)',
        'Product Reference must be unique!',
    )

    @api.constrains('list_price')
    def _check_list_price(self):
        for product in self:
            if product.list_price < 0:
                raise ValidationError(_('Sales Price cannot be negative.'))

    @api.depends('store_stock_qty')
    def _compute_store_is_low_stock(self):
        for product in self:
            product.store_is_low_stock = product.store_stock_qty < 10