# -*- coding: utf-8 -*-
import base64
import itertools
import unicodedata
import chardet
import io
import operator

from datetime import datetime, date, timedelta
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

class hv_customer_account_invoice(models.Model):
    _inherit = 'account.invoice'

    client_order_ref = fields.Char(compute='get_client_order_ref')
    
    @api.one
    def get_client_order_ref(self):
        if self.origin:
            self.client_order_ref = self.env['sale.order'].search([('name', '=', self.origin)]).client_order_ref
        else:
            self.client_order_ref = ""

    def _search_id(self, query):
        if not query:
            return []
        self._cr.execute(query)
        res = self._cr.fetchall()
        if not res:
            return []
        return [[r[0], r[1], r[2]] for r in res]

class hv_customer_statement_line(models.Model):
    _name = 'hv.customer.statement.line'

    customer_id = fields.Many2one('res.partner', string='Customer', domain="[('parent_id', '=', False), ('customer', '=', True)]")
    invoice_ids = fields.Many2many('account.invoice')
    email_address = fields.Char(string='Email')
    total = fields.Float(string='Balance', readonly=True, compute='_compute_values')
    balance = fields.Float(string='Balance', readonly=True, compute='_compute_values')
    overdue = fields.Float(string='Overdue', readonly=True, compute='_compute_values')
    statement_id = fields.Many2one('hv.customer.statement')
    email_send = fields.Integer(string = 'Send Times', default=0, readonly=True)
    send_check = fields.Boolean(string='Send', default=False)
    parent_id = fields.Many2one('hv.customer.statement.line', index=True, ondelete='cascade')
    child_ids = fields.One2many('hv.customer.statement.line','parent_id', index=True, ondelete='cascade')
    consolidatedsm = fields.Boolean(default=lambda self: self.get_consolidatedsm())

    _sql_constraints = [
        ('unique_customer_id', 'unique (customer_id,statement_id,parent_id)', 'A Customer can be added only once !'),
    ]

    def get_consolidatedsm(self):
        if not self._context.get('default_statement_id'):
            return True
        return self.env['hv.customer.statement'].browse(self._context.get('default_statement_id')).consolidatedsm

    @api.onchange('customer_id')
    def onchange_customer_id(self):
        if self.customer_id:
            self.email_address = self.customer_id.email

    @api.one
    @api.depends('customer_id')
    def _compute_values(self):
        if self.customer_id:
            if self.consolidatedsm:
                self.search_all_invoice()
            else:
                self.search_invoice()
        self.balance = 0
        self.overdue = 0
        if self.invoice_ids:
            # self.write({'invoice_ids': [(6, 0, [inv.id for inv in self.invoice_ids])]})
            self.total += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.amount_total_signed for i in self.invoice_ids])
            self.balance += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.residual_signed for i in self.invoice_ids])
            self.overdue += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.residual_signed for i in self.invoice_ids if i.date_due < fields.Date.today()])
        return True

    def search_invoice(self):
        if self.customer_id:
            start_date = self.statement_id.start_date
            statement_date = self.statement_id.statement_date
            if start_date == statement_date:
                start_date = start_date - timedelta(days=3650)
            query = """
                        SELECT ac.id, right(ac.number,5) number, right(ac.number,5) number1
                            FROM account_invoice ac left join res_partner pa on ac.partner_id = pa.id 
                            where ac.state = 'open' 
                                and ac.type in ('out_invoice','out_refund') 
                                and ac.date_invoice >= '%s' and ac.date_invoice <= '%s'
                                and (pa.id = %s)
                                """ % (start_date, statement_date + timedelta(days=1), self.customer_id.id)
            invoice_ids = self.env['account.invoice']._search_id(query)
            self.invoice_ids = [(6, 0, [r[0] for r in invoice_ids])]


    def search_all_invoice(self):
        if self.customer_id:
            start_date = self.statement_id.start_date
            statement_date = self.statement_id.statement_date
            if start_date == statement_date:
                start_date = start_date - timedelta(days=3650)
            query = """
                        SELECT ac.id, right(ac.number,5) number, right(ac.number,5) number1
                            FROM account_invoice ac left join res_partner pa on ac.partner_id = pa.id 
                            where ac.state = 'open' 
                                and ac.type in ('out_invoice','out_refund') 
                                and ac.date_invoice >= '%s' and ac.date_invoice <= '%s'
                                and (pa.id = %s or pa.parent_id = %s)
                                """ % (start_date, statement_date + timedelta(days=1), self.customer_id.id, self.customer_id.id)
            invoice_ids = self.env['account.invoice']._search_id(query)
            self.invoice_ids = [(6, 0, [r[0] for r in invoice_ids])]

    def print_customer_statement(self):
        if self.consolidatedsm:
            self.search_all_invoice()
        else:
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
    consolidatedsm = fields.Boolean(string='Consolidated Statement', default=True, readonly=True)
    
    line_ids = fields.One2many('hv.customer.statement.line', 'statement_id', string='Customers', domain=lambda self: [('consolidatedsm', '=', self.consolidatedsm)])
    selectall = fields.Boolean(default=False, compute="check_select")
    
    @api.depends("consolidatedsm")
    def check_select(self):
        self.selectall = True
        for l in self.line_ids:
            if not l.send_check:
                self.selectall = False
                break

    def set_consolidated(self):
        if self.consolidatedsm:
            self.get_detail()
        self.consolidatedsm = not self.consolidatedsm
    
    def select_all(self):
        self.selectall = not self.selectall
        for l in self.line_ids:
            l.send_check = self.selectall

    def get_detail(self):
        if self.line_ids:
            for l in self.line_ids:
                if not l.consolidatedsm:
                    continue
                l.search_all_invoice()
                for dt in l.child_ids:
                    ex = False
                    for item in groupby(l.invoice_ids, lambda i: i.partner_id):
                        if item[0].id == dt.customer_id.id:
                            ex = True
                            break
                    if not ex:
                        dt.unlink()
                for item in groupby(l.invoice_ids, lambda i: i.partner_id):
                    ex = False
                    for dt in l.child_ids:
                        if item[0].id == dt.customer_id.id:
                            ex = True
                            break
                    if not ex:
                        self.env['hv.customer.statement.line'].create({
                            'customer_id': item[0].id,
                            'email_address': item[0].email,
                            'parent_id': l.id,
                            'statement_id': l.statement_id.id,
                            'consolidatedsm': False,
                        })        
        # return self.env['havi.message'].action_warning('General Details was completed', 'Customer Statement')
    
    def partner_by_invoice(self):
        if self.statement_date and self.consolidatedsm:
            start_date = self.start_date
            statement_date = self.statement_date
            if start_date == statement_date:
                start_date = start_date - timedelta(days=3650)
            query = """
                        select id, email,1 from res_partner where id in
                        (select COALESCE(pa.parent_id,pa.id)
                            FROM account_invoice ac left join res_partner pa on ac.partner_id = pa.id 
                            where ac.state = 'open' 
                                and ac.type in ('out_invoice','out_refund') 
                                and ac.date_invoice >= '%s' and ac.date_invoice <= '%s')
                                """ % (start_date, statement_date + timedelta(days=1))
            partner_ids = self.env['account.invoice']._search_id(query)
            for l in self.line_ids:
                if not l.consolidatedsm:
                    continue
                ex = False
                for dt in partner_ids:
                    if l.customer_id.id == dt[0]:
                        ex = True
                        break
                if not ex:
                    l.unlink()

            for item in partner_ids:
                ex = False
                for dt in self.line_ids:
                    if item[0] == dt.customer_id.id:
                        ex = True
                        break
                if not ex:
                    self.env['hv.customer.statement.line'].create({
                        'customer_id': item[0],
                        'email_address': item[1],
                        'statement_id': self.id,
                        'consolidatedsm': True,
                    })   
        return self.env['havi.message'].action_warning('Update Partner List completed', 'Customer Statement')

    def send_mail_customer_statement(self):
        default_template = self.env.ref('hv_customer_statement.email_template_customer_statement', False) 
        for item in self.line_ids:
            if not item.send_check:
                continue
            if self.consolidatedsm:
                item.search_all_invoice()
            else:
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

