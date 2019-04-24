# -*- coding: utf-8 -*-
import base64
import itertools
import unicodedata
import chardet
import io
import operator

from datetime import datetime, date
from itertools import groupby
from odoo.exceptions import UserError, ValidationError
from odoo import api, exceptions, fields, models, _
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools import config, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat

try:
    import xlrd
    try:
        from xlrd import xlsx
    except ImportError:
        xlsx = None
except ImportError:
    xlrd = xlsx = None

try:
    from . import odf_ods_reader
except ImportError:
    odf_ods_reader = None

FILE_TYPE_DICT = {
    'text/csv': ('csv', True, None),
    'application/vnd.ms-excel': ('xls', xlrd, 'xlrd'),
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ('xlsx', xlsx, 'xlrd >= 1.0.0'),
    'application/vnd.oasis.opendocument.spreadsheet': ('ods', odf_ods_reader, 'odfpy')
}

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
}
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': -1,
    'in_invoice': -1,
    'out_refund': 1,
}
OPTIONS = {
    'advanced': False, 
    'bank_stmt_import': True, 'date_format': '', 'datetime_format': '', 'encoding': 'ascii', 'fields': [], 'float_decimal_separator': '.', 'float_thousand_separator': ',', 'headers': True, 'keep_matches': False, 'name_create_enabled_fields': {'currency_id': False, 'partner_id': False}, 'quoting': '"', 'separator': ','}

class hv_customer_statement_line(models.Model):
    _inherit = 'account.invoice'

    client_order_ref = fields.Char(compute='get_client_order_ref')
    
    @api.one
    def get_client_order_ref(self):
        if self.origin:
            self.client_order_ref = self.env['sale.order'].search([('name', '=', self.origin)]).client_order_ref
        else:
            self.client_order_ref = ""

class hv_customer_statement_line(models.Model):
    _name = 'hv.customer.statement.line'

    customer_id = fields.Many2one('res.partner', string='Customer')
    invoice_ids = fields.Many2many('account.invoice')
    email_address = fields.Char(string='Email')
    total = fields.Float(string='Balance', readonly=True, compute='_compute_values')
    balance = fields.Float(string='Balance', readonly=True, compute='_compute_values')
    overdue = fields.Float(string='Overdue', readonly=True, compute='_compute_values')
    statement_id = fields.Many2one('hv.customer.statement')
    email_send = fields.Integer(string = 'Send Times', default=0, readonly=True)

    _sql_constraints = [
        ('unique_customer_id', 'unique (customer_id)', 'A Customer can be added only once !')
    ]
    @api.one
    @api.depends('customer_id')
    def _compute_values(self):
        self.balance = 0
        self.overdue = 0
        self.search_invoice()
        self.email_address = self.customer_id.email
        if self.invoice_ids:
            # self.write({'invoice_ids': [(6, 0, [inv.id for inv in self.invoice_ids])]})
            self.total += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.amount_total_signed for i in self.invoice_ids])
            self.balance += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.residual_signed for i in self.invoice_ids])
            self.overdue += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.residual_signed for i in self.invoice_ids if i.date_due < fields.Date.today()])
        return True

    def search_invoice(self):
        if self.customer_id:
            self.invoice_ids = self.env['account.invoice'].search([('partner_id', '=', self.customer_id.id), ('state', '=', 'open'), ('type', 'in', ['out_invoice', 'out_refund']), ('date_invoice', '>=', self.statement_id.start_date), ('date_invoice', '<=', self.statement_id.statement_date)])

    def print_customer_statement(self):
        self.search_invoice()
        if self.invoice_ids:    
            return self.env.ref('hv_customer_statement.action_report_customer_statement').report_action(self)

class hv_customer_statement(models.Model):
    _name = 'hv.customer.statement'

    statement_date = fields.Date(string='Statement Date', required=True, default=fields.Date.today())
    start_date = fields.Date(string='Start Date', required=True, default=fields.Date.today())
    emailtemplate = fields.Many2one('mail.template', string='Template')
    include0balance = fields.Boolean(string='Include 0 Balance', default=False)
    showonlyopen = fields.Boolean(string='Show Only Open Transaction', default=False)
    consolidatedsm = fields.Boolean(string='Consolidated Statement', default=False)
    
    line_ids = fields.One2many('hv.customer.statement.line', 'statement_id', string='Customers')
        
    def send_mail_customer_statement(self):
        default_template = self.env.ref('hv_customer_statement.email_template_customer_statement', False) 
        for item in self.line_ids:
            # item = self.line_ids[0]
            item.search_invoice()
            if item.invoice_ids:
                ctx = dict(
                    active_model='hv.customer.statement.line',
                    active_id=item.id,
                    default_model='hv.customer.statement.line',
                    default_res_id=item.id,
                    default_use_template=bool(default_template),
                    default_template_id=default_template and default_template.id or False,
                    # default_composition_mode='comment',
                    default_composition_mode='mass_mail',
                )
                wizard_mail = self.env['mail.compose.message'].with_context(ctx).create({})
                wizard_mail.onchange_template_id_wrapper()
                wizard_mail.send_mail()
                item.email_send += 1
        
        return self.env['havi.message'].action_warning('Send customer statement completed', 'Customer Statement')

