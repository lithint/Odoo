# -*- coding: utf-8 -*-
"""Account Invoice Model."""

from odoo import api, fields, models


class AccountInvoice(models.Model):
    """Account Invoice Model."""

    _inherit = "account.invoice"

    state = fields.Selection(selection_add=[('on_hold', 'On Hold')])

    @api.model
    def default_get(self, default_fields):
        """Overridden Default Get to remove the Bank account."""
        res = super(AccountInvoice, self).default_get(default_fields)
        if res.get('partner_bank_id', False):
            res['partner_bank_id'] = False
        return res

    @api.multi
    def action_invoice_on_hold(self):
        """Method to make bill on hold."""
        for bill in self:
            bill.state = 'on_hold'

    def _search_id(self, query):
        if not query:
            return []
        self._cr.execute(query)
        res = self._cr.fetchall()
        if not res:
            return []
        return [[r[0], r[1], r[2]] for r in res]
