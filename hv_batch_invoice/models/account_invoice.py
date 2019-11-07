# -*- coding: utf-8 -*-
"""Account Invoice Model."""

from odoo import api, fields, models


class AccountInvoice(models.Model):
    """Account Invoice Model."""

    _inherit = "account.invoice"

    state = fields.Selection(selection_add=[('on_hold', 'On Hold')])
    previous_state = fields.Selection([
        ('draft', 'Draft'), ('on_hold', 'On Hold'),
        ('open', 'Open'), ('paid', 'Paid'),
        ('in_payment', 'In Payment'), ('cancel', 'Cancelled')],
        string="Previous State", default="draft")

    # @api.model
    # def default_get(self, default_fields):
    #     """Overridden Default Get to remove the Bank account."""
    #     res = super(AccountInvoice, self).default_get(default_fields)
    #     if res.get('partner_bank_id', False):
    #         res['partner_bank_id'] = False
    #     return res

    # @api.model
    # def create(self, vals):
       # """Overridden Create method to remove the default bank account."""
        # bank_account = self._get_default_bank_id(vals.get('type'),
        #                                         vals.get('company_id'))
        # if bank_account and not vals.get('partner_bank_id'):
        #     vals['partner_bank_id'] = bank_account.id
        # inv = super(AccountInvoice, self).create(vals)
        # inv.partner_bank_id = False
        # return inv

    @api.multi
    def action_invoice_on_hold(self):
        """Method to make bill on hold."""
        for bill in self:
            previous_state = bill.state
            bill.write({'state': 'on_hold', 'previous_state': previous_state})

    @api.multi
    def action_invoice_un_hold(self):
        """Method to make bill un hold."""
        for bill in self:
            re_state = bill.previous_state
            bill.write({'state': re_state, 'previous_state': re_state})

    def _search_id(self, query):
        if not query:
            return []
        self._cr.execute(query)
        res = self._cr.fetchall()
        if not res:
            return []
        return [[r[0], r[1], r[2]] for r in res]
