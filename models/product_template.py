from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_store_product = fields.Boolean(
        string='Store Product',
        default=False,
    )

    store_stock_qty = fields.Integer(
        string='Stock Quantity',
        default=0,
    )

    _default_code_unique = models.Constraint(
        'unique(default_code)',
        'Product Reference must be unique!',
    )

    @api.constrains('list_price', 'is_store_product')
    def _check_list_price(self):
        for product in self:
            if product.is_store_product and product.list_price < 0:
                raise ValidationError(_('Sales Price cannot be negative.'))

    @api.constrains('default_code', 'is_store_product')
    def _check_store_reference(self):
        for product in self:
            if (
                product.is_store_product
                and product.product_variant_count <= 1
                and not product.default_code
            ):
                raise ValidationError(_('Store products must have a Reference.'))