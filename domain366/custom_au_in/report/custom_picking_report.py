# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError

class StockPickingReport(models.AbstractModel):
    _name = 'report.custom_au_in.report_custom_picking_order'
    _description = 'Stock Picking report'

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('custom_au_in.report_custom_picking_order')
        picking = self.env[report.model].browse(docids)
        sale_move_prod = {}
        for sale_lines in self.env['sale.order.line'].search([('order_id','=',picking.origin)]):
            # key = (sale_lines.product_id.,sale_lines.name,sale_lines.product_uom_qty,sale_lines.product_id.qty_available)
            key = (sale_lines.product_id.default_code,sale_lines.product_id.name,sale_lines.product_uom_qty,sale_lines.product_id.qty_available)
            bom_id = sale_lines.product_id.product_tmpl_id.bom_ids
            move_line_kit_list = []
            move_line_non_kit = []
            if bom_id:
                for bom_lines in bom_id.bom_line_ids:
                    for move_line in picking.move_lines:
                        if bom_lines.product_id.id == move_line.product_id.id:
                            # move_line_kit_list.append([move_line.product_id.name,move_line.name,move_line.product_id.qty_available,
                            move_line_kit_list.append([move_line.product_id.default_code,move_line.product_id.name,move_line.product_id.qty_available,
                                move_line.product_uom_qty,move_line.reserved_availability])
                    sale_move_prod.update({key:move_line_kit_list})
            else:
                for move_line in picking.move_lines:
                    if sale_lines.product_id.id == move_line.product_id.id:
                        #move_line_non_kit.append([move_line.product_id.name,move_line.name,move_line.product_id.qty_available,
                        move_line_non_kit.append([move_line.product_id.default_code,move_line.product_id.name,move_line.product_id.qty_available,
                                move_line.product_uom_qty,move_line.reserved_availability])
        return {
            'doc_ids': docids,
            'docs': picking,
            'kit_prod' : sale_move_prod,
            'non_kit_prod' : move_line_non_kit,
        }
