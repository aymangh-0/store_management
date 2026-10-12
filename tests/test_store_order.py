import re

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import StoreTestCommon


@tagged('post_install', '-at_install')
class TestStoreOrder(StoreTestCommon):

    def test_store_user_creates_order_with_sequence_prices_and_total(self):
        order = self._create_store_order(self.store_user, [(self.product_a, 2), (self.product_b, 1)])

        year = fields.Date.today().year
        self.assertRegex(order.name, r'^CMD/%s/\d{4}$' % year)
        self.assertTrue(order.is_store_order)
        self.assertEqual(order.store_state, 'draft')
        line_a = order.order_line.filtered(lambda l: l.product_id == self.product_a)
        self.assertEqual(line_a.price_unit, 10.0, "Unit price is filled from the product")
        self.assertEqual(line_a.price_subtotal, 20.0)
        self.assertEqual(order.store_total, 45.0)

    def test_sequence_numbers_increase(self):
        first = self._create_store_order(self.store_user, [(self.product_a, 1)])
        second = self._create_store_order(self.store_user, [(self.product_a, 1)])
        first_num = int(re.search(r'(\d{4})$', first.name).group(1))
        second_num = int(re.search(r'(\d{4})$', second.name).group(1))
        self.assertEqual(second_num, first_num + 1)

    def test_regular_sale_order_keeps_sale_sequence(self):
        order = self.env['sale.order'].with_user(self.store_manager).create({
            'partner_id': self.customer.id,
        })
        self.assertFalse(order.is_store_order)
        self.assertFalse(order.name.startswith('CMD/'))

    @mute_logger('odoo.sql_db')
    def test_quantity_must_be_positive(self):
        for qty in (0, -1):
            with self.assertRaises(ValidationError):
                self._create_store_order(self.store_user, [(self.product_a, qty)])
        order = self._create_store_order(self.store_user, [(self.product_a, 1)])
        with self.assertRaises(ValidationError):
            order.order_line.with_user(self.store_user).write({'product_uom_qty': 0})
        self.assertEqual(order.order_line.product_uom_qty, 1)

    def test_total_follows_lines(self):
        order = self._create_store_order(self.store_user, [(self.product_a, 1)])
        order.order_line.with_user(self.store_user).write({'product_uom_qty': 3})
        self.assertEqual(order.store_total, 30.0)

    def test_workflow_confirm_cancel_reset(self):
        order = self._create_store_order(self.store_user, [(self.product_a, 1)])
        order = order.with_user(self.store_user)

        order.action_store_confirm()
        self.assertEqual(order.store_state, 'confirmed')

        order.action_store_cancel()
        self.assertEqual(order.store_state, 'cancel')

        with self.assertRaises(UserError):
            order.action_store_confirm()
        self.assertEqual(order.store_state, 'cancel')

        order.action_store_reset_draft()
        self.assertEqual(order.store_state, 'draft')

    def test_reset_to_draft_only_from_cancelled(self):
        order = self._create_store_order(self.store_user, [(self.product_a, 1)]).with_user(self.store_user)
        with self.assertRaises(UserError):
            order.action_store_reset_draft()
        order.action_store_confirm()
        with self.assertRaises(UserError):
            order.action_store_reset_draft()
        self.assertEqual(order.store_state, 'confirmed')

    def test_cannot_confirm_without_products(self):
        order = self._create_store_order(self.store_user, [])
        with self.assertRaises(UserError):
            order.with_user(self.store_user).action_store_confirm()
        self.assertEqual(order.store_state, 'draft')

    def test_cancelled_order_cannot_be_confirmed_by_core_method(self):
        order = self._create_store_order(self.store_user, [(self.product_a, 1)]).with_user(self.store_user)
        order.action_store_cancel()
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, 'cancel')

    def test_confirmed_order_is_locked_on_order_and_lines(self):
        order = self._create_store_order(self.store_user, [(self.product_a, 2)])
        order.with_user(self.store_user).action_store_confirm()
        order_u = order.with_user(self.store_user)
        line_u = order.order_line.with_user(self.store_user)
        other_customer = self.env['res.partner'].create({'name': 'Other', 'is_store_customer': True})

        with self.assertRaises(UserError):
            order_u.write({'partner_id': other_customer.id})
        with self.assertRaises(UserError):
            order_u.write({'order_line': [(0, 0, {'product_id': self.product_b.id, 'product_uom_qty': 1})]})
        with self.assertRaises(UserError):
            line_u.write({'product_uom_qty': 5})
        with self.assertRaises(UserError):
            line_u.write({'price_unit': 1.0})
        with self.assertRaises(UserError):
            self.env['sale.order.line'].with_user(self.store_user).create({
                'order_id': order.id,
                'product_id': self.product_b.id,
                'product_uom_qty': 1,
            })
        with self.assertRaises(UserError):
            line_u.unlink()

        self.env.invalidate_all()
        self.assertEqual(order.partner_id, self.customer)
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line.product_uom_qty, 2)
        self.assertEqual(order.order_line.price_unit, 10.0)
        self.assertEqual(order.store_total, 20.0)

    def test_regular_confirmed_order_lines_stay_editable(self):
        order = self.env['sale.order'].with_user(self.store_manager).create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {'product_id': self.product_a.id, 'product_uom_qty': 1})],
        })
        order.action_confirm()
        order.order_line.with_user(self.store_manager).write({'product_uom_qty': 4})
        self.assertEqual(order.order_line.product_uom_qty, 4)

    def test_store_user_cannot_delete_orders(self):
        order = self._create_store_order(self.store_user, [(self.product_a, 1)])
        with self.assertRaises(AccessError):
            order.with_user(self.store_user).unlink()
        self.assertTrue(order.exists())

    def test_store_user_cannot_edit_products_or_customers(self):
        with self.assertRaises(AccessError):
            self.product_a.product_tmpl_id.with_user(self.store_user).write({'list_price': 1.0})
        with self.assertRaises(AccessError):
            self.customer.with_user(self.store_user).write({'name': 'Hacked'})
        self.assertEqual(self.product_a.list_price, 10.0)
        self.assertEqual(self.customer.name, 'Store Customer Test')

    def test_store_manager_can_delete_draft_order(self):
        order = self._create_store_order(self.store_manager, [(self.product_a, 1)])
        order.with_user(self.store_manager).unlink()
        self.assertFalse(order.exists())

    def test_customer_orders_relation(self):
        store_order = self._create_store_order(self.store_user, [(self.product_a, 1)])
        regular_order = self.env['sale.order'].create({'partner_id': self.customer.id})
        self.assertIn(store_order, self.customer.store_order_ids)
        self.assertNotIn(regular_order, self.customer.store_order_ids)
        self.assertEqual(self.customer.store_order_count, len(self.customer.store_order_ids))

    def test_report_renders(self):
        order = self._create_store_order(self.store_user, [(self.product_a, 2)])
        html, _ = self.env['ir.actions.report']._render_qweb_html(
            'store_management.action_report_store_order', order.ids)
        html = html.decode()
        self.assertIn(order.name, html)
        self.assertIn('Grand Total', html)
        self.assertIn('Store Product A', html)


@tagged('post_install', '-at_install')
class TestStoreProductRules(StoreTestCommon):

    @mute_logger('odoo.sql_db')
    def test_store_product_requires_reference(self):
        Template = self.env['product.template'].with_user(self.store_manager)
        with self.assertRaises(ValidationError):
            Template.create({'name': 'No Ref', 'is_store_product': True})
        with self.assertRaises(ValidationError):
            self.env['product.product'].with_user(self.store_manager).create({
                'name': 'No Ref Variant', 'is_store_product': True,
            })
        with self.assertRaises(ValidationError):
            self.product_a.product_tmpl_id.with_user(self.store_manager).write({'default_code': False})
        with self.assertRaises(ValidationError):
            self.product_a.with_user(self.store_manager).write({'default_code': False})
        self.env.invalidate_all()
        self.assertEqual(self.product_a.default_code, 'TST-SM-A')
        self.assertFalse(self.env['product.template'].search([('name', 'in', ['No Ref', 'No Ref Variant'])]))

    def test_store_product_created_as_variant_with_reference(self):
        variant = self.env['product.product'].with_user(self.store_manager).create({
            'name': 'Variant With Ref', 'default_code': 'TST-SM-VAR', 'is_store_product': True,
        })
        self.assertTrue(variant.is_store_product)
        self.assertEqual(variant.product_tmpl_id.default_code, 'TST-SM-VAR')

    def test_regular_product_does_not_require_reference(self):
        product = self.env['product.template'].with_user(self.product_manager).create({'name': 'Regular'})
        self.assertFalse(product.default_code)

    @mute_logger('odoo.sql_db')
    def test_reference_is_unique(self):
        with self.assertRaises(IntegrityError):
            self.env['product.template'].with_user(self.store_manager).create({
                'name': 'Duplicate',
                'default_code': 'TST-SM-A',
                'is_store_product': True,
            })
            self.env.flush_all()

    @mute_logger('odoo.sql_db')
    def test_store_sales_price_not_negative(self):
        with self.assertRaises(ValidationError):
            self.product_a.product_tmpl_id.with_user(self.store_manager).write({'list_price': -1})
        self.assertEqual(self.product_a.list_price, 10.0)
        regular = self.env['product.template'].create({'name': 'Regular', 'list_price': -1})
        self.assertEqual(regular.list_price, -1)

    def test_stock_quantity_defaults_to_zero(self):
        product = self.env['product.template'].with_user(self.store_manager).create({
            'name': 'Fresh', 'default_code': 'TST-SM-FRESH', 'is_store_product': True,
        })
        self.assertEqual(product.store_stock_qty, 0)
