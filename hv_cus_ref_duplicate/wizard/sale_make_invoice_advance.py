# -*- coding: utf-8 -*-
"""Initialize Python files."""

from odoo import api, models


class SaleAdvancePaymentInv(models.TransientModel):
    """Inherited Sale Advance Payment Inv."""

    _inherit = "sale.advance.payment.inv"

    @api.multi
    def create_invoices(self):
        """Overridden method to remove the bank account from invoice."""
        sale_obj = self.env['sale.order']
        res = super(SaleAdvancePaymentInv, self).create_invoices()
        if self._context and self._context.get('active_ids', []):
            sale_orders = sale_obj.browse(self._context['active_ids'])
            invoices = sale_orders.mapped('invoice_ids')
            if invoices:
                invoices.write({'partner_bank_id': False})
        return res
