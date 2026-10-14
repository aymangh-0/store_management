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

    store_cancel_reason = fields.Text(
        string="Cancellation Reason", readonly=True, copy=False
    )

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


    @api.depends('order_line.price_subtotal')
    def _compute_store_total(self):
        for order in self:
            order.store_total = sum(order.order_line.mapped('price_subtotal'))

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

    # Workflow actions: confirm, cancel and reset to draft, with their rules

    def _store_check_stock(self):
        for order in self:
            for line in order.order_line.filtered(lambda l: l.product_id):
                product = line.product_id.product_tmpl_id
                if line.product_uom_qty > product.store_stock_qty:
                    raise UserError(_(
                        'Not enough stock for "%(product)s". '
                        'Available: %(available)s, ordered: %(ordered)s.',
                        product=product.display_name,
                        available=product.store_stock_qty,
                        ordered=int(line.product_uom_qty),
                    ))

    def _store_update_stock(self, sign):
        move_type = 'order_confirm' if sign < 0 else 'order_cancel'
        for order in self:
            for line in order.order_line.filtered(lambda l: l.product_id):
                product = line.product_id.product_tmpl_id.sudo().with_context(
                    store_move_type=move_type,
                    store_order_id=order.id,
                )
                product.store_stock_qty += sign * int(line.product_uom_qty)

    def action_store_confirm(self):
        for order in self:
            if order.state == 'cancel':
                raise UserError(_('A cancelled order cannot be confirmed. Reset it to draft first.'))
            if order.state != 'draft':
                raise UserError(_('Only draft orders can be confirmed.'))
            if not order.order_line.filtered(lambda line: not line.display_type):
                raise UserError(_('You cannot confirm an order without products.'))
        self._store_check_stock()
        result = self.action_confirm()
        self._store_update_stock(-1)
        return result

    def action_store_cancel(self):
        for order in self:
            if order.state == 'cancel':
                raise UserError(_('This order is already cancelled'))
        confirmed_orders = self.filtered(lambda o: o.state == 'sale')
        result = self.action_cancel()
        confirmed_orders._store_update_stock(1)
        return result

    def action_store_reset_draft(self):
        for order in self:
            if order.state != 'cancel':
                raise UserError(_('Only cancelled orders can be reset to draft'))
        return self.action_draft()

    def write(self, vals):
        protected_fields = {'partner_id', 'date_order', 'order_line'}
        for order in self:
            if order.is_store_order and order.state == 'sale' and protected_fields & set(vals):
                raise UserError(_('A confirmed order cannot be modified.'))
        return super().write(vals)
