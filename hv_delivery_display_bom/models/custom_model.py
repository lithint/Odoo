# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    internal_reference = fields.Char(string='Internal Reference')

    @api.multi
    def write(self, vals):
        if len(self) == 1 and self.state == 'assigned' and \
                not vals.get('internal_reference', False):
            for move in self.move_ids_without_package:
                if move.product_tmpl_id and \
                        move.product_tmpl_id.bom_count or \
                        not self.internal_reference:
                    # self.internal_reference = \
                    #     move.product_tmpl_id.default_code
                    vals.update({
                        'internal_reference':
                        move.product_tmpl_id.default_code or ''
                    })
        return super(StockPicking, self).write(vals)
