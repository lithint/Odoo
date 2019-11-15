# -*- coding: utf-8 -*-
import base64
import itertools
import unicodedata
import chardet
import io
import operator
import csv
import tempfile
import time
import threading

from odoo.addons.web.controllers.main import serialize_exception, content_disposition
from odoo import http
from odoo.http import request
from itertools import groupby
from odoo.exceptions import UserError, ValidationError
from odoo import api, exceptions, fields, models, _, sql_db
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools import config, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat


class Binary(http.Controller):

    @http.route('/web/binary/download_document', type='http', auth="public")
    @serialize_exception
    def download_document(self, model, field, id, filename=None, **kw):
        Model = request.env[model]
        res = Model.browse([int(id)])
        filecontent = base64.b64decode(res.datas)
        if not filecontent:
            res.unlink()
            return request.not_found()
        else:
            res.unlink()
            return request.make_response(
                filecontent,
                [('Content-Type', 'application/octet-stream'),
                 ('Content-Disposition', content_disposition(filename))])


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

OPTIONS = {
    'advanced': False,
    'bank_stmt_import': True,
    'date_format': '', 'datetime_format': '',
    'encoding': 'ascii', 'fields': [],
    'float_decimal_separator': '.',
    'float_thousand_separator': ',',
    'headers': True, 'keep_matches': False,
    'name_create_enabled_fields': {'currency_id': False, 'partner_id': False},
    'quoting': '"', 'separator': ','
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


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _order = "parent_id desc, display_name"

    rebate = fields.Float(string='Rebate %', digits=(3, 1), default=0.0)

    @api.onchange('rebate')
    def _rebate_onchange(self):
        if self.rebate > 100 or self.rebate < 0:
            raise UserError(_('Rebate value range must be in (0, 100).'))

    @api.multi
    def name_get(self):
        res = []
        for partner in sorted(self, key=lambda partner: partner.parent_id,
                              reverse=False):
            name = partner._get_name()
            res.append((partner.id, name))
        return res


class hv_batch_invoice_writeoff(models.Model):
    _name = 'batch.account.writeoff'
    _description = 'Batch Account Writeoff'

    writeoff_account_id = fields.Many2one('account.account',
                                          string="Difference Account",
                                          domain=[('deprecated', '=', False)],
                                          copy=False, required=True)
    writeoff_label = fields.Char(string='Journal Item Label',
                                 help="Change label of the counterpart that"
                                 " will hold the payment difference",
                                 default='Write-Off')
    amount = fields.Float(string='Amount', required=True)
    payment_id = fields.Many2one(
        'account.abstract.payment', string='Originator Payment')

    @api.onchange('amount')
    def _amount_onchange(self):
        if self.amount == 0:
            self.amount = self.payment_id.payment_difference_rest


class AccountAbstractPayment(models.AbstractModel):
    _inherit = 'account.abstract.payment'

    pack_id = fields.Many2one(
        'pack.rebate', string='Payment Model', stored=False)
    writeoff_account_ids = fields.One2many(
        'batch.account.writeoff', 'payment_id')
    payment_difference_rest = fields.Float(
        string='Payment rest', readonly=True, compute='_compute_rest')
    batch_invoice_id = fields.Many2one('batch.invoice')

    @api.onchange('pack_id')
    def _onchange_pack_id(self):
        acc_writeoff_obj = self.env['batch.account.writeoff']
        if not self.pack_id or self.currency_id.round(
                self.payment_difference_rest) == 0:
            return
        rest = self.payment_difference_rest
        for l in self.pack_id.packline_ids:
            self.writeoff_account_ids += acc_writeoff_obj.new({
                'writeoff_account_id': l.account_id.id,
                'amount': self.currency_id.round(rest / l.ratio),
                'payment_id': self.id,
                'writeoff_label': l.descritption
            })

    @api.one
    @api.depends('writeoff_account_ids', 'payment_difference')
    def _compute_rest(self):
        self.payment_difference_rest = abs(self.payment_difference)
        for wof in self.writeoff_account_ids:
            self.payment_difference_rest -= wof.amount
        self.payment_difference_rest = abs(self.payment_difference_rest)

    @api.onchange('currency_id')
    def _onchange_currency(self):
        res = super(AccountAbstractPayment, self)._onchange_currency()
        if 'rebate' in self.partner_id._fields:
            if self._context.get('batch_invoice_id'):
                batch = self.env['batch.invoice'].browse(
                    self._context.get('batch_invoice_id'))
                batch.rebatepercent = batch.customer_id.parent_id.rebate or \
                    batch.customer_id.rebate
                if batch.rebatepercent:
                    self.amount -= self.currency_id.round(
                        self.amount * batch.rebatepercent / 100)
        return res

    # @api.onchange('writeoff_account_ids', 'payment_difference')
    # def _writeoff_account_ids_onchange(self):
    #     if self.payment_difference_rest < 0:
    #         raise UserError(_("Total Amount value cannot greater than"
    #                        " Payment rest value."))


class AccountRegisterPayment(models.TransientModel):
    _inherit = "account.register.payments"

    @api.model
    def default_get(self, fields):
        rec = super(AccountRegisterPayment, self).default_get(fields)
        if 'rebate' in self.partner_id._fields:
            if self._context.get('batch_invoice_id'):
                batch = self.env['batch.invoice'].browse(
                    self._context.get('batch_invoice_id'))
                batch.rebatepercent = batch.customer_id.parent_id.rebate or \
                    batch.customer_id.rebate
                if batch.rebatepercent:
                    currency = self.env['res.currency'].browse(
                        rec['currency_id'])
                    amount = currency.round(
                        rec['amount'] * batch.rebatepercent / 100)
                    rec.update({
                        'amount': abs(rec['amount'] - amount),
                    })
        return rec

    @api.onchange('journal_id')
    def _onchange_journal(self):
        res = super(AccountRegisterPayment, self)._onchange_journal()
        if 'rebate' in self.partner_id._fields:
            if self._context.get('batch_invoice_id'):
                batch = self.env['batch.invoice'].browse(
                    self._context.get('batch_invoice_id'))
                batch.rebatepercent = batch.customer_id.parent_id.rebate or \
                    batch.customer_id.rebate

                if batch.rebatepercent:
                    self.amount -= self.currency_id.round(
                        self.amount * batch.rebatepercent / 100)
        return res

    @api.multi
    def _prepare_payment_vals(self, invoices):
        values = super(AccountRegisterPayment, self).\
            _prepare_payment_vals(invoices)
        if self._context.get('batch_invoice_id'):
            values.update({
                'writeoff_account_ids': [
                    (6, 0, self.writeoff_account_ids.ids)],
                'batch_invoice_id': self._context.get('batch_invoice_id')
            })
        return values

    def _batch_invoice_payment(self):
        try:
            new_cr = sql_db.db_connect(self.env.cr.dbname).cursor()
            uid, context = self.env.uid, self.env.context
            with api.Environment.manage():
                self.env = api.Environment(new_cr, uid, context)
                for reg_pay_wiz in self:
                    reg_pay_wiz.create_payments()
                new_cr.commit()
                return True
        finally:
            self.env.cr.close()

    @api.multi
    def batch_invoice_payment(self):
        thread_start = threading.Thread(target=self._batch_invoice_payment)
        thread_start.start()
        return True

    @api.multi
    def create_payments(self):
        if self._context.get('batch_invoice_id') and \
                self.currency_id.round(self.payment_difference_rest) != 0 and \
                self.payment_difference_handling == 'reconcile':
            raise UserError(_('Payment rest value must be 0.'))
        action_vals = super(AccountRegisterPayment, self).create_payments()
        if self._context.get('batch_invoice_id'):
            batch_invoice = self.env['batch.invoice'].browse(
                self._context.get('batch_invoice_id'))
            batch_invoice.write({'state': 'run'})
        return action_vals


class AccountPayment(models.Model):
    _inherit = "account.payment"

    writeoff_account_ids = fields.Many2many('batch.account.writeoff',
                                            'account_payment_writeoff_rel',
                                            'payment_id', 'writeoff_id')

    def _create_payment_entry(self, amount):
        """Create a journal entry corresponding to a payment,

        if the payment references invoice(s) they are reconciled.
        Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(
            check_move_validity=False)
        debit, credit, amount_currency, currency_id = \
            aml_obj.with_context(date=self.payment_date).\
            _compute_amount_fields(amount, self.currency_id,
                                   self.company_id.currency_id)

        move = self.env['account.move'].create(self._get_move_vals())

        # Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(
            debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(
            self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)

        # Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and \
                self.payment_difference:
            if self.writeoff_account_id:
                writeoff_line = self._get_shared_move_line_vals(
                    0, 0, 0, move.id, False)
                debit_wo, credit_wo, amount_currency_wo, currency_id = \
                    aml_obj.with_context(date=self.payment_date).\
                    _compute_amount_fields(self.payment_difference,
                                           self.currency_id,
                                           self.company_id.currency_id)
                writeoff_line['name'] = self.writeoff_label
                writeoff_line['account_id'] = self.writeoff_account_id.id
                writeoff_line['debit'] = debit_wo
                writeoff_line['credit'] = credit_wo
                writeoff_line['amount_currency'] = amount_currency_wo
                writeoff_line['currency_id'] = currency_id
                writeoff_line = aml_obj.create(writeoff_line)
                if counterpart_aml['debit'] or (writeoff_line['credit'] and
                                                not counterpart_aml['credit']):
                    counterpart_aml['debit'] += credit_wo - debit_wo
                if counterpart_aml['credit'] or (writeoff_line['debit'] and
                                                 not counterpart_aml['debit']):
                    counterpart_aml['credit'] += debit_wo - credit_wo
                counterpart_aml['amount_currency'] -= amount_currency_wo
            if self.writeoff_account_ids:
                for wreteoff in self.writeoff_account_ids:
                    writeoff_line = self._get_shared_move_line_vals(
                        0, 0, 0, move.id, False)
                    debit_wo, credit_wo, amount_currency_wo, currency_id = \
                        aml_obj.with_context(date=self.payment_date).\
                        _compute_amount_fields(wreteoff.amount,
                                               self.currency_id,
                                               self.company_id.currency_id)
                    writeoff_line['name'] = wreteoff.writeoff_label
                    writeoff_line[
                        'account_id'] = wreteoff.writeoff_account_id.id
                    writeoff_line['debit'] = debit_wo
                    writeoff_line['credit'] = credit_wo
                    writeoff_line['amount_currency'] = amount_currency_wo
                    writeoff_line['currency_id'] = currency_id
                    writeoff_line = aml_obj.create(writeoff_line)
                    if counterpart_aml['debit'] or \
                        (writeoff_line['credit'] and
                            not counterpart_aml['credit']):
                        counterpart_aml['debit'] += credit_wo - debit_wo
                    if counterpart_aml['credit'] or \
                        (writeoff_line['debit'] and
                            not counterpart_aml['debit']):
                        counterpart_aml['credit'] += debit_wo - credit_wo
                    counterpart_aml['amount_currency'] -= amount_currency_wo

        # Write counterpart lines
        if not self.currency_id.is_zero(self.amount):
            if not self.currency_id != self.company_id.currency_id:
                amount_currency = 0
            liquidity_aml_dict = self._get_shared_move_line_vals(
                credit, debit, -amount_currency, move.id, False)
            liquidity_aml_dict.update(
                self._get_liquidity_move_line_vals(-amount))
            aml_obj.create(liquidity_aml_dict)

        # validate the payment
        if not self.journal_id.post_at_bank_rec:
            move.post()

        # reconcile the invoice receivable/payable line(s) with the payment
        if self.invoice_ids:
            self.invoice_ids.register_payment(counterpart_aml)

        return move


class hv_batch_invoice(models.Model):
    _name = 'batch.invoice'
    _description = 'Batch Invoice'

    name = fields.Char(string='Batch Name', required=True)
    customer_id = fields.Many2one('res.partner',
                                  string='Customer',
                                  domain=[('customer', '=', True)],
                                  help="Filter open invoices by"
                                  " selected customer.",)
    invoice_ids_domain = fields.Many2many('account.invoice',
                                          'batch_account_invoice_rel',
                                          'batch_id', 'invoice_id',
                                          string='Add Invoices to Batch',
                                          compute='get_domain')
    invoice_ids = fields.Many2many('account.invoice',
                                   'batch_account_invoice_rel',
                                   'batch_id', 'invoice_id',
                                   string='Add Invoices to Batch',)

    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'),
                              ('run', 'Registered')],
                             readonly=True, default='draft',
                             copy=False, string="Status")
    total = fields.Float(string='Total Amount', readonly=True,
                         compute='_compute_total', store=True)
    rebate = fields.Float(string='Rebate Amount',
                          readonly=True, compute='_compute_total', store=True)
    rebatepercent = fields.Float(string='Rebate %',
                                 digits=(3, 1), readonly=True,
                                 compute='_compute_total', store=True)

    import_ids = fields.One2many('batch.invoice.import.result', 'batch_id')
    payment_ids = fields.One2many('account.abstract.payment',
                                  'batch_invoice_id')
    company_id = fields.Many2one('res.company',
                                 string='Company', change_default=True,
                                 default=lambda self: self.env['res.company'].
                                 _company_default_get('batch.invoice'))

    @api.multi
    @api.depends('invoice_ids', 'customer_id')
    def _compute_total(self):
        for batch_iv in self:
            if batch_iv.state == 'draft':
                batch_iv.rebatepercent = batch_iv.customer_id and \
                    batch_iv.customer_id.parent_id and \
                    batch_iv.customer_id.parent_id.rebate or \
                    batch_iv.customer_id and batch_iv.customer_id.rebate
                batch_iv.total = 0.0
                batch_iv.rebate = 0.0
                if batch_iv.invoice_ids:
                    batch_iv.total = \
                        sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] *
                             i.residual_signed for i in batch_iv.invoice_ids])
                    # self.rebate += \
                    #    sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * \
                    #       i.amount_total_signed for i in self.invoice_ids])
                    batch_iv.rebate = batch_iv.invoice_ids[0].\
                        currency_id.round(
                            batch_iv.total * batch_iv.rebatepercent / 100)

    @api.multi
    @api.depends('customer_id')
    def get_domain(self):
        inv_obj = self.env['account.invoice']
        for batch_inv in self:
            customer = batch_inv.customer_id and \
                batch_inv.customer_id.id or False
            if batch_inv.customer_id:
                iv = inv_obj.search([
                    ('state', '=', 'open'),
                    ('type', 'in', ['out_invoice', 'out_refund']),
                    '|', ('partner_id.id', '=', customer),
                    ('partner_id.parent_id.id', '=', customer)])
            else:
                iv = inv_obj.search([
                    ('state', '=', 'open'),
                    ('type', 'in', ['out_invoice', 'out_refund'])])
            batch_inv.invoice_ids_domain = [i.id for i in iv]

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        res = {}
        if self.customer_id != self._origin.customer_id and self.invoice_ids:
            self.invoice_ids = [(6, 0, [])]
            warning = {
                'title': "Change customer warning",
                'message': "Once change customer, your selected"
                "invoices will be remove."
            }
            res.update({'warning': warning})
        return res

    def action_confirm(self):
        """Method will move the state in open."""
        return self.write({'state': 'open'})

    def action_cancel(self):
        """Method will move the state in draft."""
        return self.write({'state': 'draft'})

    def action_register_payment_hv(self):
        move_l_obj = self.env['account.move.line']
        inv_obj = self.env['account.invoice']
        if not self.invoice_ids:
            raise UserError(_('You cannot register without any invoice.'))
        out_refund_invs = inv_obj.search([('id', 'in', self.invoice_ids.ids),
                                          ('type', '=', 'out_refund'),
                                          ('state', '=', 'open')])
        for refund_inv in out_refund_invs:
            out_invs = inv_obj.search([('id', 'in', self.invoice_ids.ids),
                                       ('type', '=', 'out_invoice'),
                                       ('state', '=', 'open')])
            for out_iv in out_invs:
                lines = move_l_obj.search([
                    ('invoice_id', '=', out_iv.id),
                    ('credit', '=', 0),
                    ('debit', '>', 0)])
                refund_inv.assign_outstanding_credit(lines.id)
                if refund_inv.state == 'paid':
                    break
        ctx = {
            'active_model': 'account.invoice',
            'active_ids': [x.id for x in self.invoice_ids
                           if x.state == 'open' and x.type == 'out_invoice'],
            'batch_invoice_id': self.id
        }
        payment_ref = \
            self.env.ref('hv_batch_invoice.view_account_payment_from_invoices')
        return {
            'name': 'Register Payment',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.register.payments',
            # 'src_model': 'account.invoice',
            # 'multi': True,
            'view_id': payment_ref and payment_ref.id or False,
            'target': 'new',
            # 'key2':'client_action_multi',
            'context': ctx
        }

    def import_statement(self):
        return self.env['havi.message'].with_context(
            active_model='batch.invoice', batch_invoice_id=self.id).\
            action_import('Select Remittance Advice file to import',
                          'Import Invoices', 'hv_batch_invoice')


class InvoiceImportResultLine(models.Model):
    _name = "batch.invoice.import.result.line"
    _description = 'Batch Invoice Import Result Line'

    tranno = fields.Char(string='Number Import', required=True)
    state = fields.Selection([('imported', 'Imported'),
                              ('no', 'Not Imported')],
                             default='imported', copy=False, string="Status")
    import_id = fields.Many2one('batch.invoice.import.result')


class InvoiceImportResult(models.Model):
    _name = "batch.invoice.import.result"
    _description = 'Batch Invoice Import Result'

    batch_id = fields.Many2one('batch.invoice')
    importreuslt_ids = fields.One2many(
        'batch.invoice.import.result.line', 'import_id')

    filename = fields.Char(string='File Name')
    total_rows = fields.Integer(string='Total row(s)', readonly=True)
    import_rows = fields.Integer(string='Imported row(s)', readonly=True)

    def download_ir(self):
        if self.importreuslt_ids:
            data = [['.TranNo', 'Status', ]]
            for line in self.importreuslt_ids:
                data.append([line.tranno, line.state, ])
            file_name = tempfile.gettempdir() + '/text.csv'
            with open(file_name, 'w') as fp:
                a = csv.writer(fp, delimiter=',')
                a.writerows(data)
            with open(file_name, 'rb') as fp:
                attach = self.env['ir.attachment'].create({
                    'name': file_name,
                    'res_name': file_name,
                    'res_model': 'batch.invoice.import.result',
                    'res_id': self.id,
                    'datas': base64.encodestring(fp.read()),
                    'datas_fname': file_name,
                })
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/web/binary/download_document?model=ir.attachment&field=datas&id=%s&filename=%s' % (
                        attach.id, 'IRS_%s_%s.csv' % (self.filename, self.write_date.strftime('%Y%m%d%H%M'))),
                    'target': 'current',
                }
        return self.env['havi.message'].action_warning('No data found.', 'Download Import Result')


class hv_message(models.TransientModel):
    _name = 'havi.message'
    _inherit = 'havi.message'

    def import_file(self):
        if self.module == 'hv_batch_invoice' and self.title == 'Import Invoices':
            fields, datas = self.get_data()
            number_index = [index for index, data in enumerate(
                fields) if data.lower() == 'tran no.']
            if not number_index:
                raise UserError(
                    _("Invoice import need an 'Tran No.' field and data in csv file."))

            batch_invoice = self.env['batch.invoice'].browse(
                self._context.get('batch_invoice_id'))
            numbers = ""
            for data in datas:
                numbers = numbers + "'" + data[number_index[0]] + "',"
            if len(numbers) == 0:
                raise UserError(_("No data found."))
            numbers = numbers[0:len(numbers) - 1]
            if 'x_studio_jcurve_invoice' in self.env['account.invoice']._fields:
                query = """
                        SELECT ac.id, right(ac.number,5) number, right(ac.x_studio_jcurve_invoice,5) x_studio_jcurve_invoice
                            FROM account_invoice ac left join res_partner pa on ac.partner_id = pa.id 
                            where (right(ac.number,5) in (%s) or right(ac.x_studio_jcurve_invoice,5) in (%s))
                                and ac.state = 'open' 
                                and ac.type in ('out_invoice','out_refund') 
                                and (pa.id = %s or pa.parent_id = %s)
                                """ % (numbers, numbers, batch_invoice.customer_id.id, batch_invoice.customer_id.id)
            else:
                query = """
                        SELECT ac.id, right(ac.number,5) number, right(ac.number,5) number1
                            FROM account_invoice ac left join res_partner pa on ac.partner_id = pa.id 
                            where right(ac.number,5) in (%s) 
                                and ac.state = 'open' 
                                and ac.type in ('out_invoice','out_refund') 
                                and (pa.id = %s or pa.parent_id = %s)
                                """ % (numbers, batch_invoice.customer_id.id, batch_invoice.customer_id.id)
            invoice_ids = self.env['account.invoice']._search_id(query)
            if invoice_ids:
                batch_invoice.write({'invoice_ids': [(5,)]})
                batch_invoice.write(
                    {'invoice_ids': [(4,  invoice_id[0]) for invoice_id in invoice_ids]})

            result = self.env['batch.invoice.import.result'].new({
                'batch_id': batch_invoice.id,
                'filename': self.filename,
                'total_rows': len(datas),
                'import_rows': len(invoice_ids),
            })
            batch_invoice.import_ids += result
            for data in datas:
                f = False
                if 'x_studio_jcurve_invoice' in self.env['account.invoice']._fields:
                    for match in invoice_ids:
                        if data[number_index[0]] == match[1] or data[number_index[0]] == match[2]:
                            f = True
                            break
                else:
                    for match in invoice_ids:
                        if data[number_index[0]] == match[1]:
                            f = True
                            break
                if not f:
                    batch_invoice.import_ids[len(batch_invoice.import_ids) - 1].importreuslt_ids += self.env['batch.invoice.import.result.line'].new({
                        'import_id': result.id,
                        'tranno': data[number_index[0]],
                        'state': 'no',
                    })

            return self.env['havi.message'].action_warning('- Total invoices in file: %s invoice(s).\n\n- Import was successfull with %s row(s).' % (len(datas), len(invoice_ids)), 'Import Result')
        else:
            return super(hv_message, self).import_file()


class PackRebateLine(models.Model):
    _name = "pack.rebate.line"
    _description = 'Pack Rebate Line'

    account_id = fields.Many2one(
        'account.account', string='Account', required=True)
    descritption = fields.Char(string='Description')
    ratio = fields.Float(string='Ratio /', digits=(3, 1), default=0.0)
    pack_id = fields.Many2one('pack.rebate')


class PackRebate(models.Model):
    _name = "pack.rebate"
    _description = 'Pack Rebate'

    name = fields.Char(string='Payment Model', required=True)
    default = fields.Boolean(string='Payment Default', default=False)
    packline_ids = fields.One2many(
        'pack.rebate.line', 'pack_id', string='Account Ratio')
