
from odoo import api, fields, models, _

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    picking_id = fields.Many2one('stock.picking','Picking')
    sale_id  =  fields.Many2one('sale.order', 'Sale Origin')
    pur_id   =  fields.Many2one('purchase.order', 'Purchase Origin')
