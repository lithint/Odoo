
from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def action_done(self):
        res = super(StockPicking, self).action_done()
        sale_order  =  self.env['sale.order'].search([('name', '=',self.origin )])
        if sale_order:
            inv = self.env['account.invoice'].search([('sale_id','=',self.origin)],limit=1)
            for sale_line in self.move_lines:
                if sale_line.product_id.property_account_income_id:
                    account = sale_line.product_id.property_account_income_id
                elif sale_line.product_id.categ_id.property_account_income_categ_id:
                    account = sale_line.product_id.categ_id.property_account_income_categ_id
                else:
                    account_search = self.env['ir.property'].search([('name', '=', 'property_account_income_categ_id')])
                    account = account_search.value_reference
                    account = account.split(",")[1]
                    account = self.env['account.account'].browse(account)
            for inv_line in inv.invoice_line_ids:
                inv_line.unlink()
            for sale_lines in sale_order.order_line:
                inv_line_id = inv_line.create({'product_id': sale_lines.product_id.id, 
                                    'name':sale_lines.name,
                                    'price_unit':sale_lines.price_unit,
                                    'quantity' : sale_lines.product_uom_qty,
                                    'account_id':account.id,
                                    'invoice_id':inv.id})
                sale_lines.write({'qty_invoiced': inv_line_id.quantity})
            return res
        else:
            return res
