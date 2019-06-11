# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    x_studio_available_qty = fields.Text(related='product_id.x_studio_quantity' ,string='Available Quantity', readonly=True)