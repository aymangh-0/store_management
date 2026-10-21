from odoo import http
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