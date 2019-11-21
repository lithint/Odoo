# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
"""Stock Move Line models."""

from odoo import fields, api, models


class StockMoveLine(models.Model):
    """Stock Move Line model."""

    _inherit = 'stock.move.line'

    # Below Fields Only for The Product Moves Report Purpose.

    partner_id = fields.Many2one("res.partner",
                                 compute="_get_partner_for_move_line",
                                 string="Store", store=True)
    parent_id = fields.Many2one("res.partner",
                                compute="_get_partner_for_move_line",
                                string="Customer", store=True)
    return_qty = fields.Float(compute="_get_return_qty_based_on_loc",
                              string="Return QTY", store=True)

    @api.multi
    @api.depends('picking_id', 'move_id', 'state', 'product_id',
                 'location_id', 'location_dest_id')
    def _get_return_qty_based_on_loc(self):
        """Method to calculate return QTY based on location."""
        company_id = self.env.user and self.env.user.company_id and \
            self.env.user.company_id.id or False
        # We Search With static name filter to fullfill the report
        # Requirements.
        parent_loc = self.env['stock.location'].search([
            ('complete_name', 'ilike', 'Partner Locations'),
            ('usage', '=', 'view'),
            ('location_id', '=', False),
            ('company_id', 'in', [company_id, False])], limit=1)
        for line in self:
            if line.location_id and \
                    line.location_id.location_id == parent_loc and\
                    line.location_id.usage == 'customer' and \
                    line.location_id.complete_name == \
                    'Partner Locations/Customers':
                line.return_qty = line.qty_done
            else:
                line.return_qty = 0.0

    @api.multi
    @api.depends('picking_id', 'move_id', 'state', 'product_id',
                 'location_id', 'location_dest_id')
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
