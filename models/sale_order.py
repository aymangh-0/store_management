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

    def _store_check_is_store_order(self):
        if self.filtered(lambda order: not order.is_store_order):
            raise UserError(_('This action is only available for store orders.'))

    def action_confirm(self):
        store_orders = self.filtered('is_store_order')
        store_orders._store_check_stock()
        result = super().action_confirm()
        store_orders._store_update_stock(-1)
        store_orders._store_send_confirmation_email()
        return result

    def _action_cancel(self):
        confirmed_store_orders = self.filtered(
            lambda order: order.is_store_order and order.state == 'sale'
        )
        result = super()._action_cancel()
        confirmed_store_orders._store_update_stock(1)
        return result

    def action_store_confirm(self):
        self._store_check_is_store_order()
        for order in self:
            if order.state == 'cancel':
                raise UserError(_('A cancelled order cannot be confirmed. Reset it to draft first.'))
            if order.state != 'draft':
                raise UserError(_('Only draft orders can be confirmed.'))
            if not order.order_line.filtered(lambda line: not line.display_type):
                raise UserError(_('You cannot confirm an order without products.'))
        return self.action_confirm()

    def _store_send_confirmation_email(self):
        template = self.env.ref('store_management.mail_template_store_order_confirmed')
        for order in self:
            if order.partner_id.email:
                order.message_post_with_source(
                    template,
                    subtype_xmlid='mail.mt_comment',
                    email_layout_xmlid='mail.mail_notification_light',
                )

    def action_store_cancel(self):
        self._store_check_is_store_order()
        for order in self:
            if order.state == 'cancel':
                raise UserError(_('This order is already cancelled'))
        return self.with_context(disable_cancel_warning=True).action_cancel()

    def action_store_reset_draft(self):
        self._store_check_is_store_order()
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

    def _has_to_be_signed(self):
        return not self.is_store_order and super()._has_to_be_signed()

    def _has_to_be_paid(self):
        return not self.is_store_order and super()._has_to_be_paid()
