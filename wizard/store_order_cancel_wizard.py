from odoo import _, fields, models
from odoo.exceptions import UserError


class StoreOrderCancelWizard(models.TransientModel):
    _name = "store.order.cancel.wizard"
    _description = "Store Order Cancel Wizard"

    order_id = fields.Many2one('sale.order', string="Order", required=True)
    reason_type = fields.Selection(
        selection=[
            ('customer_request', 'Customer request'),
            ('wrong_order', 'Wrong order details'),
            ('payment_issue', 'Payment issue'),
            ('other', 'Other'),
        ],
        string="Reason",
        required=True,
    )
    reason = fields.Text(string="Details")

    def action_confirm_cancel(self):
        self.ensure_one()
        if self.reason_type == 'other':
            if not self.reason or not self.reason.strip():
                raise UserError(_('Please write the cancellation reason.'))
            final_reason = self.reason.strip()
        else:
            labels = dict(self._fields['reason_type'].selection)
            final_reason = labels[self.reason_type]

        self.order_id.action_store_cancel()
        self.order_id.store_cancel_reason = final_reason
        self.order_id.message_post(
            body=_('Order cancelled. Reason: %s', final_reason)
        )
        return {'type': 'ir.actions.act_window_close'}