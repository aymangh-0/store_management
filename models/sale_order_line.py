from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError

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

    def _check_store_order_editable(self):
        for line in self:
            if (
                line.order_id.is_store_order
                and line.order_id.state == 'sale'
                and not line.is_downpayment
            ):
                raise UserError(_('A confirmed order cannot be modified.'))

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._check_store_order_editable()
        return lines

    def write(self, vals):
        if set(vals) & set(self._get_protected_fields()):
            self._check_store_order_editable()
        return super().write(vals)