from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    store_stock_qty = fields.Integer(
        string="Stock Quantity",
        default=0,
    )

    store_is_low_stock = fields.Boolean(
        string="Low Stock",
        compute="_compute_store_is_low_stock",
        store=True,
    )

    _default_code_unique = models.Constraint(
        'unique(default_code)',
        'Product Reference must be unique!',
    )

    @api.constrains('list_price')
    def _check_list_price(self):
        for product in self:
            if product.list_price < 0:
                raise ValidationError(_('Sales Price cannot be negative.'))

    @api.depends('store_stock_qty')
    def _compute_store_is_low_stock(self):
        for product in self:
            product.store_is_low_stock = product.store_stock_qty < 10

    @api.model
    def _cron_store_low_stock_alert(self):
        products = self.search([('store_is_low_stock', '=', True)])
        managers = self.env.ref('store_management.group_store_manager').user_ids
        activity_type = self.env.ref('mail.mail_activity_data_warning')

        recovered = self.search([('store_is_low_stock', '=', False)])
        old_alerts = recovered.activity_ids.filtered(
            lambda a: a.activity_type_id == activity_type
        )
        old_alerts.action_feedback(feedback=_('Stock is back above the limit.'))

        for product in products:
            for manager in managers:
                already_sent = product.activity_ids.filtered(
                    lambda a: a.activity_type_id == activity_type
                    and a.user_id == manager
                )
                if already_sent:
                    continue
                product.activity_schedule(
                    'mail.mail_activity_data_warning',
                    user_id=manager.id,
                    summary=_('Low Stock'),
                    note=_('Only %s left in stock.', product.store_stock_qty),
                )