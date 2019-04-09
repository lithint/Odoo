# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo import api, exceptions, fields, models, _

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    case_order_ids = fields.Many2many('sale.order', 'helpdesk_ticket_sale_order_multi_rel','ticket_id', 'order_id', string='Case Order')