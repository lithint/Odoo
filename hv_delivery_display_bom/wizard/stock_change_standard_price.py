# -*- coding: utf-8 -*-
"""Change Standard Price."""

from odoo import api, models


class StockChangeStandardPrice(models.TransientModel):
    """Change Standard Price."""

    _inherit = "stock.change.standard.price"
    _description = "Change Standard Price"

    @api.multi
    def change_price(self):
        """Ovewrite the method to fix active ids issue."""
        self.ensure_one()
        products = self.env['product.product']
        if self._context['active_model'] == 'product.template':
            for prod_temp in self.env['product.template'].browse(
                    self._context['active_ids']):
                products |= prod_temp.product_variant_ids
        else:
            products = self.env['product.product'].browse(
                self._context['active_ids'])

        if products:
            products.do_change_standard_price(
                self.new_price, self.counterpart_account_id.id)
        return {'type': 'ir.actions.act_window_close'}
