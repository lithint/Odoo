# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo import api, exceptions, fields, models, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    x_studio_foc = fields.Selection([('Sample', 'Sample'),
                                     ('Marketing', 'Marketing'),
                                     ('After Sales & Services', 'After Sales & Services'),
                                     ('Special Arrangement', 'Special Arrangement'),
                                     ('Swap Product', 'Swap Product'),
                                     ('Kit items', 'Kit items'),
                                     ('Not Applicable', 'Not Applicable'),], string='FOC', default='Not Applicable')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Warehouse',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=False)
