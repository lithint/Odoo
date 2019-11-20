# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""Stock Move Line models."""

from odoo import fields, api, models


class StockMoveLine(models.Model):
    """Stock Move Line model."""

    _inherit = 'stock.move.line'

    partner_id = fields.Many2one("res.partner",
                                 compute="_get_partner_for_move_line",
                                 string="Store", store=True)
    parent_id = fields.Many2one("res.partner",
                                compute="_get_partner_for_move_line",
                                string="Customer", store=True)

    @api.multi
    @api.depends('picking_id', 'move_id')
    def _get_partner_for_move_line(self):
        """Method to add the partner id in stock move line."""
        for line in self:
            partner_id = False
            parent_id = False
            if line.picking_id and line.picking_id.partner_id:
                partner_id = line.picking_id.partner_id.id
                parent_id = line.picking_id.partner_id.parent_id and\
                    line.picking_id.partner_id.parent_id.id or False
            elif line.move_id and line.move_id.picking_id and \
                    line.move_id.picking_id.partner_id:
                partner_id = line.move_id.picking_id.partner_id.id
                parent_id = line.move_id.picking_id.partner_id.parent_id and\
                    line.move_id.picking_id.partner_id.parent_id.id or False
            elif line.move_id and line.move_id.partner_id:
                partner_id = line.move_id.partner_id.id
                parent_id = line.move_id.partner_id.parent_id and \
                    line.move_id.partner_id.parent_id.id or False
            elif line.move_id and line.move_id.group_id and \
                    line.move_id.group_id.partner_id:
                partner_id = line.move_id.group_id.partner_id.id
                parent_id = line.move_id.group_id.partner_id.parent_id and \
                    line.move_id.group_id.partner_id.parent_id.id or False
            line.partner_id = partner_id
            line.parent_id = parent_id
