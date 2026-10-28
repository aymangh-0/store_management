from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    STORE_LOCKED_LINE_FIELDS = {
        'product_id', 'product_uom_qty', 'product_uom_id', 'price_unit', 'discount',
    }

    def _store_check_not_confirmed(self):
        if any(line.order_id.is_store_order and line.order_id.state == 'sale' for line in self):
            raise UserError(_('The lines of a confirmed store order cannot be modified.'))

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._store_check_not_confirmed()
        return lines

    def write(self, vals):
        if self.STORE_LOCKED_LINE_FIELDS & set(vals):
            self._store_check_not_confirmed()
        return super().write(vals)

    @api.constrains('product_uom_qty')
    def _check_store_quantity(self):
        for line in self:
            if not line.order_id.is_store_order or line.display_type or line.is_downpayment:
                continue
            quantity = line.product_uom_qty
            if quantity <= 0 or quantity != int(quantity):
                raise ValidationError(
                    _('The ordered quantity must be a whole number greater than 0.')
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