# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""Sale Order Related models."""

from odoo import fields, models, api, _


class SaleOrder(models.Model):
    """Sale Order model."""

    _inherit = 'sale.order'

    quote_number = fields.Char(string="Quotation Number", copy=False,
                               default=lambda self: _('New'))
    client_order_ref = fields.Char(string="Customer Reference")

    @api.model
    def create(self, vals):
        """Override create method to update the name (sequence)."""
        seq_obj = self.env['ir.sequence']
        quote_sequence = \
            self.env.ref('scs_ccleen_products.seq_gentec_quotation_order')
        sale_order = super(SaleOrder, self).create(vals)
        if quote_sequence and \
                vals.get('quote_sequence', _('New')) == _('New'):

            if 'company_id' in vals:
                sale_order.quote_number = seq_obj.\
                    with_context(force_company=vals['company_id']).\
                    next_by_code('quotation.order.sequence') or _('New')
            else:
                sale_order.quote_number = seq_obj.\
                    next_by_code('quotation.order.sequence') or _('New')
        return sale_order
