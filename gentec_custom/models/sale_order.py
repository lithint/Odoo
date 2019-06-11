# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_per_warehouse = fields.Text(related='product_id.qty_per_warehouse' ,string='Available Quantity', readonly=True)