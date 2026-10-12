from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _has_field_access(self, field, operation):
        # Same guard as product.template. Without it, default_get on a variant
        # passes the template default is_store_product=False to the template
        # create, which then refuses it for non-managers.
        if self.env['product.template']._is_store_flag_write_denied(field, operation):
            return False
        return super()._has_field_access(field, operation)
