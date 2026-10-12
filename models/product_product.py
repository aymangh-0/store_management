from odoo import api, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Only Store Managers can change the store flag (same rule as the template).
    @api.model
    def _has_field_access(self, field, operation):
        if self.env['product.template']._is_store_flag_write_denied(field, operation):
            return False
        return super()._has_field_access(field, operation)

    # Check the store Reference of templates created together with their variant.
    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        new_template_products = products.browse([
            product.id for product, vals in zip(products, vals_list)
            if not vals.get('product_tmpl_id')
        ])
        new_template_products.product_tmpl_id._check_store_reference()
        return products

    # Re-check the store Reference when it or the store flag changes.
    def write(self, vals):
        res = super().write(vals)
        if {'default_code', 'is_store_product'} & set(vals):
            self.product_tmpl_id._check_store_reference()
        return res
