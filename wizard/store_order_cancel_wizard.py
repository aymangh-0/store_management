from odoo import _, fields, models

class StoreOrderCancelWizard(models.TransientModel):
    _name = 'store.order.cancel.wizard'
    _description = 'Store Order Cancel Wizard'

    order_id = fields.Many2one('sale.order', string="Order", required=True)
    reason = fields.Text(string="Cancellation Reason", required=True)

    def action_confirm_cancel(self):
        self.ensure_one()
        self.order_id.action_store_cancel()
        self.order_id.store_cancel_reason = self.reason
        self.order_id.message_post(
            body=_('Order cancelled. Reason: %s', self.reason)
        )
        return {'type': 'ir.actions.act_window_close'}