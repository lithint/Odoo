# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    potential_qty = fields.Text(compute='_compute_potential_qty', string='Potential Qty')
    x_studio_quantity = fields.Text(compute='_compute_x_studio_quantity' ,string='Quantity')
    @api.multi
    def _compute_potential_qty(self):
        for template in self:
            bom_id = self.env['mrp.bom'].search([('product_tmpl_id', '=', template.id)], limit=1)
            if bom_id:
                total_potential_qty = 0.0
                qty_per_warehouse_list = []
                for warehouse in self.env['stock.warehouse'].search([]):
                    raw_potential_qty = []
                    for line in bom_id.bom_line_ids:
                        product_id = line.product_id
                        qty = product_id.with_context(warehouse=warehouse.id)._compute_quantities_dict(False, False, False)
                        product_qty = qty[product_id.id]['qty_available']
                        component_qty = line.product_qty
                        try:
                            line_potential_qty = math.floor(product_qty / component_qty)
                        except ZeroDivisionError as e:
                            continue
                        raw_potential_qty.append(line_potential_qty)
                    potential_qty_available = raw_potential_qty and min(raw_potential_qty) or 0.0
                    total_potential_qty+=potential_qty_available
                    qty_per_warehouse_list.append('%s (%s)' % (int(potential_qty_available), warehouse.code))
                qty_per_warehouse_text = "%s: " % (int(total_potential_qty))
                qty_per_warehouse_text = qty_per_warehouse_text + ' , '.join(qty_per_warehouse_list)
                template.potential_qty = qty_per_warehouse_text
            
    @api.multi
    def _compute_x_studio_quantity(self):
        for template in self:
            total_qty = template.qty_available
            qty_per_warehouse_text = "%s: " % (int(total_qty))
            qty_per_warehouse_list = []
            for warehouse in self.env['stock.warehouse'].search([]):
                qty = template.with_context(warehouse=warehouse.id)._compute_quantities_dict()
                qty_available = qty[template.id]['qty_available']
                qty_per_warehouse_list.append('%s (%s)' % (int(qty_available), warehouse.code))
            qty_per_warehouse_text = qty_per_warehouse_text + ' , '.join(qty_per_warehouse_list)
            template.x_studio_quantity = qty_per_warehouse_text