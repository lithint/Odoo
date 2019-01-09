# -*- coding: utf-8 -*-
# Copyright 2018 Mahmoud Abdel Latif (<http://www.mah007.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, api


class SaleOrderConfirmWizard(models.TransientModel):
    _name = "sale.order.confirm.wizard"
    _description = "Wizard - Sale Order Action"

    @api.multi
    def confirm_sale_orders(self):
        self.ensure_one()
        active_ids = self._context.get('active_ids')
        orders = self.env['sale.order'].browse(active_ids)
        for order in orders:
            if order.state in ['draft', 'sent']:
                order.action_confirm()

    @api.multi
    def draft_sale_orders(self):
        self.ensure_one()
        active_ids = self._context.get('active_ids')
        orders = self.env['sale.order'].browse(active_ids)
        for order in orders:
            order.action_cancel()
            order.action_draft()
