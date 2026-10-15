from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class StoreRestockWizard(models.TransientModel):
    _name = "store.restock.wizard"
    _description = "Store Restock Wizard"

    line_ids = fields.One2many(
        'store.restock.wizard.line', 'wizard_id', string="Products"
    )
    reference = fields.Char()

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        if context.get('active_model') == 'product.template':
            res['line_ids'] = [
                Command.create({'product_id': product_id})
                for product_id in context.get('active_ids', [])
            ]
        return res

    def action_restock(self):
        self.ensure_one()
        if self.line_ids.filtered(lambda l: l.quantity < 0):
            raise UserError(_('Quantity received cannot be negative.'))
        lines = self.line_ids.filtered(lambda l: l.quantity > 0)
        if not lines:
            raise UserError(_('Enter a quantity for at least one product.'))
        for line in lines:
            product = line.product_id.with_context(
                store_move_type='restock',
                store_move_note=self.reference,
            )
            product.store_stock_qty += line.quantity
        return {'type': 'ir.actions.act_window_close'}


class StoreRestockWizardLine(models.TransientModel):
    _name = "store.restock.wizard.line"
    _description = "Store Restock Wizard Line"

    wizard_id = fields.Many2one(
        'store.restock.wizard', required=True, ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.template', string="Product", required=True
    )
    current_stock = fields.Integer(
        related='product_id.store_stock_qty', string="Current Stock"
    )
    quantity = fields.Integer(string="Quantity Received")