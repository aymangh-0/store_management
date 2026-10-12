import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Flag products used in non-cancelled store orders as store products.

    ``is_store_product`` was added in 19.0.1.0.0 (commit 1add442) without a
    version bump and defaults to False, so products created before it would
    disappear from the Store Products menu and from the store order line
    product picker.

    Raw SQL on purpose: writing through the ORM runs the store product
    constraints (required reference, non-negative price), and one legacy
    product without a reference would abort the whole upgrade. Products that
    break those rules are logged instead, so they can be fixed from the form.
    """
    if not version:
        return

    Template = api.Environment(cr, SUPERUSER_ID, {})['product.template']
    Template.flush_model(['is_store_product'])

    cr.execute("""
        UPDATE product_template pt
           SET is_store_product = TRUE
          FROM product_product pp
          JOIN sale_order_line sol ON sol.product_id = pp.id
          JOIN sale_order so ON so.id = sol.order_id
         WHERE pp.product_tmpl_id = pt.id
           AND so.is_store_order
           AND so.state != 'cancel'
           AND pt.is_store_product IS NOT TRUE
     RETURNING pt.id
    """)
    flagged_ids = sorted({row[0] for row in cr.fetchall()})
    Template.invalidate_model(['is_store_product'])
    _logger.info("Flagged %s product template(s) as store products: %s",
                 len(flagged_ids), flagged_ids)
    if not flagged_ids:
        return

    # Same scope as _check_store_reference: single-variant templates only.
    cr.execute("""
        SELECT pt.id
          FROM product_template pt
         WHERE pt.id IN %s
           AND (pt.default_code IS NULL OR pt.default_code = '')
           AND (SELECT count(*)
                  FROM product_product pp
                 WHERE pp.product_tmpl_id = pt.id
                   AND pp.active) <= 1
    """, [tuple(flagged_ids)])
    missing_reference = [row[0] for row in cr.fetchall()]
    if missing_reference:
        _logger.warning("Store products without a Reference (the store product form will require one): %s",
                        missing_reference)

    cr.execute("""
        SELECT id
          FROM product_template
         WHERE id IN %s
           AND list_price < 0
    """, [tuple(flagged_ids)])
    negative_price = [row[0] for row in cr.fetchall()]
    if negative_price:
        _logger.warning("Store products with a negative Sales Price: %s", negative_price)
