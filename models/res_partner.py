from odoo import api, fields, models

class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_store_customer = fields.Boolean(
        string='Store Customer',
        default=False,
    )

    store_order_ids = fields.One2many(
        comodel_name='sale.order',
        inverse_name='partner_id',
        string='Store Orders',
        domain=[('is_store_order', '=', True)],
    )

    store_order_count = fields.Integer(
        string='Orders Count',
        compute='_compute_store_order_count',
    )

    @api.depends('store_order_ids')
    def _compute_store_order_count(self):
        for partner in self:
            partner.store_order_count = len(partner.store_order_ids)

    def action_view_store_orders(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'store_management.store_order_action'
        )
        action['domain'] = [
            ('is_store_order', '=', True),
            ('partner_id', '=', self.id),
        ]
        action['context'] = {
            'default_is_store_order': True,
            'default_partner_id': self.id,
        }
        return action