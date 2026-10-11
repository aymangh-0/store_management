from odoo import _, api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_store_order = fields.Boolean(
        string='Store Order',
        default=False,
    )

    store_total= fields.Monetary(
        string='Store Total',
        compute='_compute_store_total',
        store=True,
        currency_field='currency_id',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_store_order') and vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('store.order') or _('New')
        return super().create(vals_list)


    @api.depends('order_line.price_subtotal')
    def _compute_store_total(self):
        for order in self:
            order.store_total = sum(order.order_line.mapped('price_subtotal'))