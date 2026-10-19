from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase

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

    def _create_order(self, quantity):
        return self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'is_store_order': True,
            'order_line': [(0, 0, {
                'product_id': self.product.product_variant_id.id,
                'product_uom_qty': quantity,
            })],
        })

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
