from odoo.modules.module import load_script
from odoo.tests import tagged
from odoo.tools import file_path

from .common import StoreTestCommon

LOGGER = 'odoo.upgrade.store_management.19.0.1.1.0.post-migrate'


@tagged('post_install', '-at_install')
class TestMigration19011(StoreTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        path = file_path('store_management/migrations/19.0.1.1.0/post-migrate.py')
        cls.migration = load_script(path, LOGGER)

        cls.p_draft = cls._create_product('Mig Draft', 'TST-MIG-A', 1.0)
        cls.p_confirmed = cls._create_product('Mig Confirmed', 'TST-MIG-B', 1.0)
        cls.p_cancelled = cls._create_product('Mig Cancelled', 'TST-MIG-C', 1.0)
        cls.p_regular = cls._create_product('Mig Regular', 'TST-MIG-D', 1.0)
        cls.p_no_ref = cls.env['product.product'].create({'name': 'Mig No Ref', 'list_price': 1.0})
        cls.p_negative = cls._create_product('Mig Negative', 'TST-MIG-F', -3.0)

        Order = cls.env['sale.order'].with_context(default_is_store_order=True)

        def store_order(*products):
            return Order.create({
                'partner_id': cls.customer.id,
                'order_line': [(0, 0, {'product_id': p.id, 'product_uom_qty': 1}) for p in products],
            })

        store_order(cls.p_draft, cls.p_no_ref, cls.p_negative)
        store_order(cls.p_confirmed).action_confirm()
        store_order(cls.p_cancelled).action_cancel()
        cls.env['sale.order'].create({
            'partner_id': cls.customer.id,
            'order_line': [(0, 0, {'product_id': cls.p_regular.id, 'product_uom_qty': 1})],
        })
        Order.create({
            'partner_id': cls.customer.id,
            'order_line': [(0, 0, {'display_type': 'line_section', 'name': 'Section only'})],
        })
        cls.env.flush_all()

    def _flag(self, product):
        return product.product_tmpl_id.is_store_product

    def test_flags_products_of_non_cancelled_store_orders(self):
        with self.assertLogs(LOGGER, level='INFO') as logs:
            self.migration.migrate(self.env.cr, '19.0.1.0.0')
        output = '\n'.join(logs.output)

        for product in (self.p_draft, self.p_confirmed, self.p_no_ref, self.p_negative):
            self.assertTrue(self._flag(product), product.name)
        for product in (self.p_cancelled, self.p_regular):
            self.assertFalse(self._flag(product), product.name)

        self.assertIn('without a Reference', output)
        self.assertIn(str(self.p_no_ref.product_tmpl_id.id), output.split('without a Reference')[1].splitlines()[0])
        self.assertIn('negative Sales Price', output)
        self.assertIn(str(self.p_negative.product_tmpl_id.id), output.split('negative Sales Price')[1].splitlines()[0])

    def test_second_run_is_noop(self):
        self.migration.migrate(self.env.cr, '19.0.1.0.0')
        with self.assertLogs(LOGGER, level='INFO') as logs:
            self.migration.migrate(self.env.cr, '19.0.1.0.0')
        self.assertTrue(any('Flagged 0 product template(s)' in line for line in logs.output))

    def test_no_version_does_nothing(self):
        self.migration.migrate(self.env.cr, '')
        self.assertFalse(self._flag(self.p_draft))
