# -*- coding: utf-8 -*-
"""Inherited For Account Invoice for Margin."""

from odoo import api, fields, models


class AccountInvoice(models.Model):
    """Inherited For Account Invoice for Margin."""

    _inherit = "account.invoice"

    margin = fields.Float(compute='_get_invoice_margin_in_percentage',
                          string='Margin Amount',
                          store=True)
    margin_in_per = fields.Float(compute='_get_invoice_margin_in_percentage',
                                 string='Margin (%)',
                                 store=True)

    # @api.multi
    @api.depends('invoice_line_ids', 'invoice_line_ids.quantity',
                 'invoice_line_ids.price_unit', 'invoice_line_ids.discount')
    def _get_invoice_margin_in_percentage(self):
        inv_sal_price = discount = inv_cost = 0.0
        line_cost = line_margin_amount = margin_in_per = 0.0
        for rec in self:
            if rec.invoice_line_ids:
                for inv_line in rec.invoice_line_ids:
                    inv_sal_price = inv_line.price_unit * inv_line.quantity
                    discount = (inv_sal_price * inv_line.discount) / 100
                    std_amt = inv_line.product_id and \
                        inv_line.product_id.standard_price or 0.0
                    inv_cost = std_amt * inv_line.quantity
                    line_cost += inv_cost
                    line_margin_amount += (inv_sal_price - discount) - inv_cost
                if line_cost:
                    margin_in_per = (line_margin_amount / line_cost) * 100
                else:
                    margin_in_per = 100
                rec.margin = line_margin_amount
                rec.margin_in_per = round(margin_in_per, 2)


class AccountInvoiceLine(models.Model):
    """Inherited For Account Invoice Line for Margin."""

    _inherit = 'account.invoice.line'

    margin = fields.Float(compute='_get_invoice_line_margin_in_per',
                          string='Margin Amount',
                          store=True)
    margin_in_per = fields.Float(compute='_get_invoice_line_margin_in_per',
                                 string='Margin (%)',
                                 store=True)

    # @api.multi
    @api.depends('quantity', 'price_unit', 'discount')
    def _get_invoice_line_margin_in_per(self):
        sal_price = discount = line_cost = margin_amt = margin_in_per = 0.0
        for inv_line in self:
            if inv_line.product_id:
                sal_price = inv_line.price_unit * inv_line.quantity
                discount = (sal_price * inv_line.discount) / 100
                std_amt = inv_line.product_id and \
                    inv_line.product_id.standard_price or 0.0
                line_cost = std_amt * inv_line.quantity
                margin_amt = (sal_price - discount) - line_cost
                if line_cost:
                    margin_in_per = (margin_amt / line_cost) * 100
                else:
                    margin_in_per = 100
                inv_line.margin = margin_amt or 0.0
                inv_line.margin_in_per = round(margin_in_per, 2)
