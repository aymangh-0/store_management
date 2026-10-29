from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase
from odoo import Command

class TestStoreOrder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'is_store_customer': True,
        })
        cls.product = cls.env['product.template'].create({
            'name': 'Test Mouse',
            'default_code': 'TEST-MOUSE',
            'list_price': 100,
            'store_stock_qty': 10,
        })

    def _create_order(self, quantity, paid=True):
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'is_store_order': True,
            'order_line': [(0, 0, {
                'product_id': self.product.product_variant_id.id,
                'product_uom_qty': quantity,
            })],
        })
        if paid:
            order._store_register_payment()
        return order

    def _history(self, move_type):
        return self.env['store.stock.history'].search([
            ('product_id', '=', self.product.id),
            ('move_type', '=', move_type),
        ])

    def test_duplicate_product_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['sale.order'].create({
                'partner_id': self.customer.id,
                'is_store_order': True,
                'order_line': [
                    (0, 0, {'product_id': self.product.product_variant_id.id,
                            'product_uom_qty': 1}),
                    (0, 0, {'product_id': self.product.product_variant_id.id,
                            'product_uom_qty': 1}),
                ],
            })

    def test_confirm_more_than_stock_is_rejected(self):
        order = self._create_order(quantity=20)
        with self.assertRaises(UserError):
            order.action_store_confirm()
        self.assertEqual(self.product.store_stock_qty, 10)
        self.assertEqual(order.state, 'draft')

    def test_confirm_deducts_stock(self):
        order = self._create_order(quantity=3)
        order.action_store_confirm()
        self.assertEqual(order.state, 'sale')
        self.assertEqual(self.product.store_stock_qty, 7)

    def test_cancel_confirmed_order_restores_stock(self):
        order = self._create_order(quantity=3)
        order.action_store_confirm()
        order.action_store_cancel()
        self.assertEqual(order.state, 'cancel')
        self.assertEqual(self.product.store_stock_qty, 10)

    def test_cancel_draft_order_keeps_stock(self):
        order = self._create_order(quantity=3)
        order.action_store_cancel()
        self.assertEqual(order.state, 'cancel')
        self.assertEqual(self.product.store_stock_qty, 10)

    def test_new_product_logs_initial_stock(self):
        history = self._history('initial')
        self.assertEqual(len(history), 1)
        self.assertEqual(history.quantity, 10)
        self.assertEqual(history.stock_after, 10)

    def test_confirm_logs_movement(self):
        order = self._create_order(quantity=3)
        order.action_store_confirm()
        history = self._history('order_confirm')
        self.assertEqual(len(history), 1)
        self.assertEqual(history.quantity, -3)
        self.assertEqual(history.stock_after, 7)
        self.assertEqual(history.order_id, order)

    def test_manual_change_logs_movement(self):
        self.product.store_stock_qty = 15
        history = self._history('manual')
        self.assertEqual(len(history), 1)
        self.assertEqual(history.quantity, 5)
        self.assertEqual(history.stock_after, 15)
        self.assertFalse(history.order_id)

    def test_low_stock_limit(self):
        self.product.store_stock_qty = 6
        self.assertFalse(self.product.store_is_low_stock)
        self.product.store_stock_qty = 5
        self.assertTrue(self.product.store_is_low_stock)

    def test_confirmed_order_cannot_be_modified(self):
        order = self._create_order(quantity=2)
        order.action_store_confirm()
        with self.assertRaises(UserError):
            order.write({'partner_id': self.customer.id})

    def test_cancel_wizard_saves_reason(self):
        order = self._create_order(quantity=2)
        order.action_store_confirm()
        wizard = self.env['store.order.cancel.wizard'].create({
            'order_id': order.id,
            'reason_type': 'customer_request',
        })
        wizard.action_confirm_cancel()
        self.assertEqual(order.state, 'cancel')
        self.assertEqual(order.store_cancel_reason, 'Customer request')
        self.assertEqual(self.product.store_stock_qty, 10)

    def test_cancel_wizard_other_requires_details(self):
        order = self._create_order(quantity=2)
        wizard = self.env['store.order.cancel.wizard'].create({
            'order_id': order.id,
            'reason_type': 'other',
            'reason': '   ',
        })
        with self.assertRaises(UserError):
            wizard.action_confirm_cancel()
        self.assertEqual(order.state, 'draft')

    def test_restock_adds_stock_and_logs_reference(self):
        wizard = self.env['store.restock.wizard'].with_context(
            active_model='product.template',
            active_ids=self.product.ids,
        ).create({'reference': 'INV-TEST'})
        self.assertEqual(len(wizard.line_ids), 1)
        wizard.line_ids.quantity = 5
        wizard.action_restock()
        self.assertEqual(self.product.store_stock_qty, 15)
        history = self._history('restock')
        self.assertEqual(len(history), 1)
        self.assertEqual(history.quantity, 5)
        self.assertEqual(history.note, 'INV-TEST')

    def test_restock_without_quantity_is_rejected(self):
        wizard = self.env['store.restock.wizard'].with_context(
            active_model='product.template',
            active_ids=self.product.ids,
        ).create({})
        with self.assertRaises(UserError):
            wizard.action_restock()
        self.assertEqual(self.product.store_stock_qty, 10)

    def test_store_confirm_rejects_regular_order(self):
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': self.product.product_variant_id.id,
                'product_uom_qty': 2,
            })],
        })
        with self.assertRaises(UserError):
            order.action_store_confirm()
        self.assertEqual(order.state, 'draft')
        self.assertEqual(self.product.store_stock_qty, 10)

    def test_store_cancel_rejects_regular_order(self):
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [Command.create({
                'product_id': self.product.product_variant_id.id,
                'product_uom_qty': 2,
            })],
        })
        order.action_confirm()
        with self.assertRaises(UserError):
            order.action_store_cancel()
        self.assertEqual(order.state, 'sale')
        self.assertEqual(self.product.store_stock_qty, 10)

    def test_confirmed_line_quantity_cannot_change(self):
        order = self._create_order(quantity=1)
        order.action_store_confirm()
        with self.assertRaises(UserError):
            order.order_line.write({'product_uom_qty': 100})
        self.assertEqual(order.order_line.product_uom_qty, 1)
        self.assertEqual(self.product.store_stock_qty, 9)

    def test_confirmed_order_cannot_get_new_line(self):
        other_product = self.env['product.template'].create({
            'name': 'Test Keyboard',
            'default_code': 'TEST-KEYBOARD',
            'store_stock_qty': 5,
        })
        order = self._create_order(quantity=1)
        order.action_store_confirm()
        with self.assertRaises(UserError):
            self.env['sale.order.line'].create({
                'order_id': order.id,
                'product_id': other_product.product_variant_id.id,
                'product_uom_qty': 1,
            })
        self.assertEqual(len(order.order_line), 1)

    def test_confirmed_line_cannot_be_deleted(self):
        order = self._create_order(quantity=1)
        order.action_store_confirm()
        with self.assertRaises(UserError):
            order.order_line.unlink()
        self.assertEqual(len(order.order_line), 1)

    def test_fractional_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_order(quantity=0.5)
        with self.assertRaises(ValidationError):
            self._create_order(quantity=2.7)
        self.assertEqual(self.product.store_stock_qty, 10)

    def test_standard_confirm_deducts_stock(self):
        order = self._create_order(quantity=3)
        order.action_confirm()
        self.assertEqual(order.state, 'sale')
        self.assertEqual(self.product.store_stock_qty, 7)

    def test_standard_confirm_checks_stock(self):
        order = self._create_order(quantity=11)
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, 'draft')
        self.assertEqual(self.product.store_stock_qty, 10)

    def test_standard_cancel_restores_stock(self):
        order = self._create_order(quantity=3)
        order.action_store_confirm()
        order.with_context(disable_cancel_warning=True).action_cancel()
        self.assertEqual(order.state, 'cancel')
        self.assertEqual(self.product.store_stock_qty, 10)

    def test_store_order_cannot_be_signed_or_paid(self):
        order = self._create_order(quantity=1)
        order.require_signature = True
        self.assertFalse(order._has_to_be_signed())
        self.assertFalse(order._has_to_be_paid())

    def test_payment_marks_order_paid(self):
        order = self._create_order(quantity=1,paid=False)
        order._store_register_payment()
        self.assertEqual(order.store_payment_state, 'paid')
        with self.assertRaises(UserError):
            order._store_register_payment()

    def test_cancel_paid_order_refunds(self):
        order = self._create_order(quantity=1,paid=False)
        order._store_register_payment()
        order.action_store_cancel()
        self.assertEqual(order.store_payment_state, 'refunded')

    def test_cancel_unpaid_order_stays_not_paid(self):
        order = self._create_order(quantity=1,paid=False)
        order.action_store_cancel()
        self.assertEqual(order.store_payment_state, 'not_paid')

    def test_reset_refunded_order_needs_payment_again(self):
        order = self._create_order(quantity=1,paid=False)
        order._store_register_payment()
        order.action_store_cancel()
        order.action_store_reset_draft()
        self.assertEqual(order.store_payment_state, 'not_paid')

    def test_unpaid_order_cannot_be_confirmed(self):
        order = self._create_order(quantity=1, paid=False)
        with self.assertRaises(UserError):
            order.action_store_confirm()
        with self.assertRaises(UserError):
            order.action_confirm()
        self.assertEqual(order.state, 'draft')
        self.assertEqual(self.product.store_stock_qty, 10)
