from odoo import _, api, fields, models
from odoo.exceptions import UserError

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

    store_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('cancel', 'Cancelled'),
        ],
        string='Store Status',
        compute='_compute_store_state',
        store=True,
    )

    # Give store orders a CMD/<year>/NNNN number.
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            is_store_order = vals.get(
                'is_store_order',
                self.env.context.get('default_is_store_order', False),
            )
            if is_store_order and vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('store.order') or _('New')
        return super().create(vals_list)


    # Order total from the line subtotals.
    @api.depends('order_line.price_subtotal')
    def _compute_store_total(self):
        for order in self:
            order.store_total = sum(order.order_line.mapped('price_subtotal'))

    # Map the Sales state to the store status (Draft / Confirmed / Cancelled).
    @api.depends('state')
    def _compute_store_state(self):
        mapping = {
            'draft': 'draft',
            'sent': 'draft',
            'sale': 'confirmed',
            'cancel': 'cancel',
        }
        for order in self:
            order.store_state = mapping.get(order.state, 'draft')

    # Confirm button: draft orders with products only.
    def action_store_confirm(self):
        for order in self:
            if order.state == 'cancel':
                raise UserError(_('A cancelled order cannot be confirmed. Reset it to draft first.'))
            if order.state != 'draft':
                raise UserError(_('Only draft orders can be confirmed.'))
            if not order.order_line.filtered(lambda line: not line.display_type):
                raise UserError(_('You cannot confirm an order without products.'))
        return self.action_confirm()

    # Cancel button.
    def action_store_cancel(self):
        for order in self:
            if order.state == 'cancel':
                raise UserError(_('This order is already cancelled'))
        return self.action_cancel()

    # Reset to Draft button: cancelled orders only.
    def action_store_reset_draft(self):
        for order in self:
            if order.state != 'cancel':
                raise UserError(_('Only cancelled orders can be reset to draft'))
        return self.action_draft()

    # A confirmed store order cannot change its customer, date or lines.
    def write(self, vals):
        protected_fields = {'partner_id', 'date_order', 'order_line'}
        for order in self:
            if order.is_store_order and order.state == 'sale' and protected_fields & set(vals):
                raise UserError(_('A confirmed order cannot be modified.'))
        return super().write(vals)
