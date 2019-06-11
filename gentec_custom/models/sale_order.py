# -*- coding: utf-8 -*-
import math
from odoo.exceptions import UserError, ValidationError
from odoo import api, exceptions, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _default_warehouse_id(self):
        result = super(SaleOrder, self)._default_warehouse_id()
        return []

    x_studio_foc = fields.Selection([('Sample', 'Sample'),
                                     ('Marketing', 'Marketing'),
                                     ('After Sales & Services', 'After Sales & Services'),
                                     ('Special Arrangement', 'Special Arrangement'),
                                     ('Swap Product', 'Swap Product'),
                                     ('Kit items', 'Kit items'),
                                     ('Not Applicable', 'Not Applicable'),], string='FOC', default='Not Applicable', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_default_warehouse_id)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_per_warehouse = fields.Text(related='product_id.qty_per_warehouse' ,string='Available Quantity', readonly=True)
