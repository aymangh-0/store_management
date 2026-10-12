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

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        # Only templates created by this call; variants added to an existing
        # template (e.g. from product.template.create) are checked there.
        new_template_products = products.browse([
            product.id for product, vals in zip(products, vals_list)
            if not vals.get('product_tmpl_id')
        ])
        new_template_products.product_tmpl_id._check_store_reference()
        return products

    def write(self, vals):
        res = super().write(vals)
        if {'default_code', 'is_store_product'} & set(vals):
            self.product_tmpl_id._check_store_reference()
        return res
