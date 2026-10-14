from odoo import _, api, models
from odoo.exceptions import ValidationError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.constrains('product_uom_qty')
    def _check_store_quantity(self):
        for line in self:
            if (
                    line.order_id.is_store_order
                    and not line.display_type
                    and not line.is_downpayment
                    and line.product_uom_qty <= 0
            ):
                raise ValidationError(
                    _('Ordered quantity must be greater than 0.')
                )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        res = super()._onchange_product_id()
        if self.order_id.is_store_order and self.product_id:
            self.price_unit = self.product_id.lst_price
        return res

    @api.constrains('product_id', 'order_id')
    def _check_store_duplicate_product(self):
        for line in self:
            order = line.order_id
            if not order.is_store_order or not line.product_id:
                continue
            same_lines = order.order_line.filtered(
                lambda l: l.product_id == line.product_id
            )
            if len(same_lines) > 1:
                raise ValidationError(_(
                    'The product "%s" is already in this order. '
                    'Change its quantity instead.',
                    line.product_id.display_name,
                ))