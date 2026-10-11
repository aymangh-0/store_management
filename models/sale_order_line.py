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