# -*- coding: utf-8 -*-
"""Account Invoice Model."""

from odoo import api, fields, models


class AccountInvoice(models.Model):
    """Account Invoice Model."""

    _inherit = "account.invoice"

    state = fields.Selection(selection_add=[('on_hold', 'On Hold')])

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
