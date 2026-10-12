from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import StoreTestCommon


@tagged('post_install', '-at_install')
class TestStoreProductFlag(StoreTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.regular = cls._create_product('Regular Product', 'TST-SM-REG', 5.0)
        cls.regular_tmpl = cls.regular.product_tmpl_id

    def _assert_flag(self, record, expected):
        self.env.invalidate_all()
        self.assertEqual(record.sudo().is_store_product, expected)

    def test_store_manager_can_set_and_clear_flag(self):
        tmpl = self.regular_tmpl.with_user(self.store_manager)
        tmpl.write({'is_store_product': True})
        self._assert_flag(self.regular_tmpl, True)
        tmpl.write({'is_store_product': False})
        self._assert_flag(self.regular_tmpl, False)

        self.regular.with_user(self.store_manager).write({'is_store_product': True})
        self._assert_flag(self.regular_tmpl, True)

        created = self.env['product.template'].with_user(self.store_manager).with_context(
            default_is_store_product=True,
        ).create({'name': 'Manager Store Product', 'default_code': 'TST-SM-MGR'})
        self.assertTrue(created.is_store_product)

    def test_product_manager_cannot_change_flag_on_template(self):
        Template = self.env['product.template'].with_user(self.product_manager)
        with self.assertRaises(AccessError):
            self.regular_tmpl.with_user(self.product_manager).write({'is_store_product': True})
        with self.assertRaises(AccessError):
            self.product_a.product_tmpl_id.with_user(self.product_manager).write({'is_store_product': False})
        with self.assertRaises(AccessError):
            Template.create({'name': 'PM Flagged', 'default_code': 'TST-SM-PM1', 'is_store_product': True})
        with self.assertRaises(AccessError):
            Template.with_context(default_is_store_product=True).create({'name': 'PM Context'})

        self._assert_flag(self.regular_tmpl, False)
        self._assert_flag(self.product_a.product_tmpl_id, True)
        self.assertFalse(self.env['product.template'].search([('name', 'in', ['PM Flagged', 'PM Context'])]))

    def test_product_manager_cannot_change_flag_on_variant(self):
        with self.assertRaises(AccessError):
            self.regular.with_user(self.product_manager).write({'is_store_product': True})
        with self.assertRaises(AccessError):
            self.env['product.product'].with_user(self.product_manager).create({
                'name': 'PM Variant Flagged', 'is_store_product': True,
            })
        self._assert_flag(self.regular_tmpl, False)
        self.assertFalse(self.env['product.product'].search([('name', '=', 'PM Variant Flagged')]))

    def test_product_manager_cannot_import_flag(self):
        Template = self.env['product.template'].with_user(self.product_manager)
        result = Template.load(['name', 'is_store_product'], [['PM Imported', 'True']])
        self.assertFalse(result['ids'])
        errors = ' '.join(m['message'] for m in result['messages'] if m['type'] == 'error')
        self.assertIn('is_store_product', errors, "The import must fail on the store flag access check")
        self.assertFalse(self.env['product.template'].search([('name', '=', 'PM Imported')]))

    def test_product_manager_normal_flows_still_work(self):
        pm = self.product_manager
        tmpl = self.env['product.template'].with_user(pm).create({'name': 'PM Template'})
        variant = self.env['product.product'].with_user(pm).create({'name': 'PM Variant'})
        quick_id, _name = self.env['product.product'].with_user(pm).name_create('PM Quick')
        copied = self.product_a.product_tmpl_id.with_user(pm).copy()
        self.product_a.product_tmpl_id.with_user(pm).write({'list_price': 12.0})

        self.assertFalse(tmpl.is_store_product)
        self.assertFalse(variant.is_store_product)
        self.assertFalse(self.env['product.product'].browse(quick_id).is_store_product)
        self.assertFalse(copied.is_store_product)
        self.assertEqual(self.product_a.list_price, 12.0)
        self._assert_flag(self.product_a.product_tmpl_id, True)

    def test_store_user_and_salesman_have_no_product_write_acl(self):
        # Denied by the ACL before the field guard is reached.
        for user in (self.store_user, self.salesman):
            with self.assertRaises(AccessError):
                self.regular_tmpl.with_user(user).write({'is_store_product': True})
        self._assert_flag(self.regular_tmpl, False)

    def test_store_user_reads_flag_and_store_domains(self):
        Template = self.env['product.template'].with_user(self.store_user)
        Product = self.env['product.product'].with_user(self.store_user)

        self.assertTrue(self.product_a.product_tmpl_id.with_user(self.store_user).is_store_product)
        store_templates = Template.search([('is_store_product', '=', True)])
        self.assertIn(self.product_a.product_tmpl_id, store_templates)
        self.assertNotIn(self.regular_tmpl, store_templates)

        picker_domain = [('is_store_product', '=', True), ('sale_ok', '=', True)]
        store_variants = Product.search(picker_domain)
        self.assertIn(self.product_a, store_variants)
        self.assertNotIn(self.regular, store_variants)
        found = Product.name_search('Store Product A', domain=picker_domain)
        self.assertIn(self.product_a.id, [res[0] for res in found])

    def test_fields_get_readonly_by_group(self):
        for model in ('product.template', 'product.product'):
            for user, readonly in (
                (self.store_manager, False),
                (self.product_manager, True),
                (self.store_user, True),
            ):
                desc = self.env[model].with_user(user).fields_get(['is_store_product'], ['readonly'])
                self.assertEqual(
                    desc['is_store_product']['readonly'], readonly,
                    f"{model} / {user.login}",
                )

    def test_checkbox_visible_to_store_manager_only(self):
        views = (
            ('product.template', 'product.product_template_only_form_view'),
            ('product.template', 'store_management.product_template_form_view_inherit_store'),
            ('product.product', 'product.product_normal_form_view'),
        )
        for model, xmlid in views:
            view_id = self.env.ref(xmlid).id
            for user, visible in (
                (self.store_manager, True),
                (self.product_manager, False),
                (self.store_user, False),
                (self.salesman, False),
            ):
                arch = self.env[model].with_user(user).get_view(view_id, 'form')['arch']
                self.assertEqual('store_option' in arch, visible, f"{xmlid} / {user.login}")

    def test_superuser_can_change_flag(self):
        self.regular_tmpl.sudo().write({'is_store_product': True})
        self._assert_flag(self.regular_tmpl, True)
        self.regular.sudo().write({'is_store_product': False})
        self._assert_flag(self.regular_tmpl, False)
