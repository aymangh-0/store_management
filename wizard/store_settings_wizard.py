from odoo import _,api,models,fields
from odoo.exceptions import ValidationError

DAILY_LIMIT_PARAM = 'store_management.daily_order_limit'
DEFAULT_DAILY_LIMIT = 5

class StoreSettingsWizard(models.TransientModel):
    _name = 'store.settings.wizard'
    _description = 'Store Settings Wizard'

    daily_order_limit = fields.Integer(string='Portal Orders per Customer in 24 Hours')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        value = self.env['ir.config_parameter'].sudo().get_param(DAILY_LIMIT_PARAM)
        try:
            res['daily_order_limit'] = int(value)
        except (TypeError, ValueError):
            res['daily_order_limit'] = DEFAULT_DAILY_LIMIT
        return res

    def action_save(self):
        self.ensure_one()
        if self.daily_order_limit < 0:
            raise ValidationError(_('The daily order limit cannot be negative.'))
        self.env['ir.config_parameter'].sudo().set_param(
            DAILY_LIMIT_PARAM, self.daily_order_limit)
        return {'type': 'ir.actions.act_window_close'}