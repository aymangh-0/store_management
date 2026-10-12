from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_store_product = fields.Boolean(
        string='Store Product',
        default=False,
        copy=False,
    )

    store_stock_qty = fields.Integer(
        string='Stock Quantity',
        default=0,
    )

    _default_code_unique = models.Constraint(
        'unique(default_code)',
        'Product Reference must be unique!',
    )

    # Only Store Managers can change the store flag (enforced on the server).
    @api.model
    def _has_field_access(self, field, operation):
        if self._is_store_flag_write_denied(field, operation):
            return False
        return super()._has_field_access(field, operation)

    # True when the current user may not change the store flag.
    @api.model
    def _is_store_flag_write_denied(self, field, operation):
        return (
            operation == 'write'
            and field.name == 'is_store_product'
            and not self.env.su
            and not self.env.user.has_group('store_management.group_store_manager')
        )

    # Store products cannot have a negative sales price.
    @api.constrains('list_price', 'is_store_product')
    def _check_list_price(self):
        for product in self:
            if product.is_store_product and product.list_price < 0:
                raise ValidationError(_('Sales Price cannot be negative.'))

    # Check the store Reference after create (not @api.constrains: it fails mid-create).
    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._check_store_reference()
        return templates

    # Re-check the store Reference when it or the store flag changes.
    def write(self, vals):
        res = super().write(vals)
        if {'default_code', 'is_store_product'} & set(vals):
            self._check_store_reference()
        return res

    # Single-variant store products must have a Reference.
    def _check_store_reference(self):
        for product in self:
            if not product.with_context(active_test=False).product_variant_ids:
                continue
            if (
                product.is_store_product
                and product.product_variant_count <= 1
                and not product.default_code
            ):
                raise ValidationError(_('Store products must have a Reference.'))
