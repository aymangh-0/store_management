from odoo import Command, _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class StorePortal(CustomerPortal):

    @http.route('/my/store/orders', type='http', auth='user', website=True)
    def portal_my_store_orders(self, **kw):
        partner = request.env.user.partner_id
        orders = request.env['sale.order'].sudo().search([
            ('is_store_order', '=', True),
            ('partner_id', '=', partner.id),
        ], order='date_order desc')
        values = self._prepare_portal_layout_values()
        values.update({
            'orders': orders,
            'page_name': 'store_orders',
        })
        return request.render('store_management.portal_my_store_orders', values)

    def _store_get_order(self, order_id):
        order = request.env['sale.order'].sudo().browse(order_id)
        if (not order.exists()
                or not order.is_store_order
                or order.partner_id != request.env.user.partner_id):
            return None
        return order

    @http.route('/my/store/orders/<int:order_id>', type='http', auth='user', website=True)
    def portal_my_store_order(self, order_id, **kw):
        order = self._store_get_order(order_id)
        if not order:
            return request.redirect('/my/store/orders')
        values = self._prepare_portal_layout_values()
        values.update({
            'order': order,
            'page_name': 'store_order',
        })
        return request.render('store_management.portal_my_store_order', values)

    @http.route('/my/store/orders/<int:order_id>/pdf', type='http', auth='user', website=True)
    def portal_my_store_order_pdf(self, order_id, **kw):
        order = self._store_get_order(order_id)
        if not order:
            return request.redirect('/my/store/orders')
        return self._show_report(
            model=order,
            report_type='pdf',
            report_ref='store_management.action_report_store_order',
            download=True,
        )

    def _store_available_products(self):
        return request.env['product.template'].sudo().search([
            ('store_stock_qty', '>', 0),
            ('sale_ok', '=', True),
        ], order='name')

    def _store_render_new_order(self, error=None):
        values = self._prepare_portal_layout_values()
        values.update({
            'products': self._store_available_products(),
            'error': error,
            'page_name': 'store_new_order',
        })
        return request.render('store_management.portal_store_new_order', values)

    @http.route('/my/store/orders/new', type='http', auth='user', website=True)
    def portal_store_new_order(self, **kw):
        return self._store_render_new_order()

    @http.route('/my/store/orders/submit', type='http', auth='user',
                website=True, methods=['POST'])
    def portal_store_submit_order(self, **post):
        lines = []
        for product in self._store_available_products():
            try:
                quantity = int(post.get('qty_%s' % product.id) or 0)
            except ValueError:
                quantity = 0
            if quantity > 0:
                lines.append(Command.create({
                    'product_id': product.product_variant_id.id,
                    'product_uom_qty': quantity,
                }))

        if not lines:
            return self._store_render_new_order(
                _('Enter a quantity for at least one product.')
            )

        try:
            with request.env.cr.savepoint():
                order = request.env['sale.order'].sudo().create({
                    'partner_id': request.env.user.partner_id.id,
                    'is_store_order': True,
                    'order_line': lines,
                })
                order.action_store_confirm()
        except UserError as error:
            return self._store_render_new_order(error.args[0])

        return request.redirect('/my/store/orders/%s' % order.id)