from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Only Store Managers may change it, see _has_field_access.
    # copy=False so duplicating a product from Sales does not need that right.
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

    @api.model
    def _has_field_access(self, field, operation):
        # Server-side guard for write, create, import and default_* context.
        # Not field groups=: that would also hide the field from Store Users
        # and break the store domains that read it.
        if self._is_store_flag_write_denied(field, operation):
            return False
        return super()._has_field_access(field, operation)

    @api.model
    def _is_store_flag_write_denied(self, field, operation):
        # Shared with product.product, which inherits the field (_inherits).
        return (
            operation == 'write'
            and field.name == 'is_store_product'
            and not self.env.su
            and not self.env.user.has_group('store_management.group_store_manager')
        )

    @api.constrains('list_price', 'is_store_product')
    def _check_list_price(self):
        for product in self:
            if product.is_store_product and product.list_price < 0:
                raise ValidationError(_('Sales Price cannot be negative.'))

    # Not @api.constrains: Odoo re-validates constraints when default_code is
    # recomputed, and product.template.create recomputes it from a new variant
    # that has no Reference yet (the Reference is copied to it afterwards).
    # So the check runs once create/write have finished.
    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        templates._check_store_reference()
        return templates

    def write(self, vals):
        res = super().write(vals)
        if {'default_code', 'is_store_product'} & set(vals):
            self._check_store_reference()
        return res

    def _check_store_reference(self):
        for product in self:
            # A template created by product.product.create has no variant yet;
            # product.product checks it once the variant exists.
            if not product.with_context(active_test=False).product_variant_ids:
                continue
            if (
                product.is_store_product
                and product.product_variant_count <= 1
                and not product.default_code
            ):
                raise ValidationError(_('Store products must have a Reference.'))
