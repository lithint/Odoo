# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import api, exceptions, fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    internal_reference = fields.Char(string='Internal Reference')
    def write(self, vals):
        if len(self)==1 and self.state == 'assigned' and not vals.get('internal_reference'):
            for move in self.move_ids_without_package:
                if move.product_tmpl_id.bom_count or not self.internal_reference:
                    self.internal_reference = move.product_tmpl_id.default_code
        return super(StockPicking, self).write(vals)

# class tttt(models.Model):
# 	_name = 'res.rrr'

# 	name = fields.Char(string='Reference', default='123')

