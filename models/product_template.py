from odoo import api, fields, models
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    store_stock_qty = fields.Integer(
        string="Stock Quantity",
        default=0,
    )

    _default_code_unique = models.Constraint(
        'unique(default_code)',
        'Product Reference must be unique!',
    )

    @api.constrains('list_price')
    def _check_list_price(self):
        for product in self:
            if product.list_price < 0:
                raise ValidationError(
                    'Sales Price cannot be negative'
                )