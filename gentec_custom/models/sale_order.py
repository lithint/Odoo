# -*- coding: utf-8 -*-
"""Product Sale Order Line."""

from odoo import fields, models


class SaleOrderLine(models.Model):
    """Sale order Line."""

    _inherit = "sale.order.line"

    x_studio_available_qty = fields.Text(
        related='product_id.x_studio_quantity',
        string='Available Quantity',
        readonly=True)
    potential_qty = fields.Text(
        related='product_id.potential_qty',
        string='Potential Quantity',
        readonly=True)
