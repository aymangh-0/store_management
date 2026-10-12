from odoo.tests import TransactionCase, new_test_user


class StoreTestCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store_manager = new_test_user(
            cls.env, login='store_mgr_test',
            groups='store_management.group_store_manager',
        )
        cls.store_user = new_test_user(
            cls.env, login='store_user_test',
            groups='store_management.group_store_user',
        )
        cls.product_manager = new_test_user(
            cls.env, login='product_mgr_test',
            groups='base.group_user,product.group_product_manager',
        )
        cls.salesman = new_test_user(
            cls.env, login='salesman_test',
            groups='sales_team.group_sale_salesman',
        )

        cls.customer = cls.env['res.partner'].create({
            'name': 'Store Customer Test',
            'is_store_customer': True,
        })
        cls.product_a = cls._create_product('Store Product A', 'TST-SM-A', 10.0, store=True)
        cls.product_b = cls._create_product('Store Product B', 'TST-SM-B', 25.0, store=True)

    @classmethod
    def _create_product(cls, name, code, price, store=False):
        return cls.env['product.product'].create({
            'name': name,
            'default_code': code,
            'list_price': price,
            'is_store_product': store,
        })

    def _create_store_order(self, user, lines):
        Order = self.env['sale.order'].with_user(user).with_context(default_is_store_order=True)
        return Order.create({
            'partner_id': self.customer.id,
            'order_line': [
                (0, 0, {'product_id': product.id, 'product_uom_qty': qty})
                for product, qty in lines
            ],
        })
