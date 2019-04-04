# -*- coding: utf-8 -*-
import base64
import itertools
import unicodedata
import chardet
import io
import operator

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

class hv_batch_invoice_product(models.Model):
    _inherit = 'res.partner'

    rebate = fields.Integer(string='Rebate %', default=0)

    @api.onchange('rebate')
    def _rebate_onchange(self):
        if self.rebate>100 or self.rebate<0:
            raise UserError(_('Rebate value range must be in (0, 100).'))


class hv_batch_invoice_writeoff(models.Model):
    _name = 'batch.account.writeoff'

    writeoff_account_id = fields.Many2one('account.account', string="Difference Account", domain=[('deprecated', '=', False)], copy=False)
    writeoff_label = fields.Char(
        string='Journal Item Label',
        help='Change label of the counterpart that will hold the payment difference',
        default='Write-Off')
    amount = fields.Float(string='Amount')
    payment_id = fields.Many2one('account.abstract.payment', string='Originator Payment')
    
    @api.onchange('amount')
    def _amount_onchange(self):
        if self.amount==0:
            self.amount = self.payment_id.payment_difference_rest

class hv_batch_invoice_account_abstract_payment(models.AbstractModel):
    _inherit = 'account.abstract.payment'
    
    writeoff_account_ids = fields.One2many('batch.account.writeoff','payment_id')
    payment_difference_rest = fields.Float(string='Payment rest', readonly=True, compute='_compute_rest')
    
    @api.one
    @api.depends('writeoff_account_ids', 'payment_difference')
    def _compute_rest(self):
        self.payment_difference_rest = abs(self.payment_difference)
        for wof in self.writeoff_account_ids:
            self.payment_difference_rest -= wof.amount

    @api.onchange('currency_id')
    def _onchange_currency(self):
        res = super(hv_batch_invoice_account_abstract_payment, self)._onchange_currency()
        if self._context.get('batch_invoice_id') and self.partner_id.rebate:
            self.amount = abs(self._compute_payment_amount() - self._compute_payment_amount() * self.partner_id.rebate / 100)
        return res

    @api.onchange('writeoff_account_ids', 'payment_difference')
    def _writeoff_account_ids_onchange(self):
        if self.payment_difference_rest < 0:
            raise UserError(_('Total Amount value cannot greater than Payment rest value.'))
            
class hv_batch_invoice_account_register_payment(models.TransientModel):
    _inherit = "account.register.payments"

    @api.onchange('journal_id')
    def _onchange_journal(self):
        res = super(hv_batch_invoice_account_register_payment, self)._onchange_journal()
        if self._context.get('batch_invoice_id')and self.partner_id.rebate:
            self.amount = abs(self._compute_payment_amount() - self._compute_payment_amount() * self.partner_id.rebate / 100)
        return res

    @api.multi
    def _prepare_payment_vals(self, invoices):
        values = super(hv_batch_invoice_account_register_payment, self)._prepare_payment_vals(invoices)
        values.update({'writeoff_account_ids' : [(6, 0, self.writeoff_account_ids.ids)]})
        return values

    @api.multi
    def create_payments(self):
        if self._context.get('batch_invoice_id') and self.payment_difference_rest != 0 and self.payment_difference_handling == 'reconcile':
            raise UserError(_('Payment rest value must be 0.'))
        return super(hv_batch_invoice_account_register_payment, self).create_payments()

class hv_batch_invoice_account_payment(models.Model):
    _inherit = "account.payment"
    writeoff_account_ids = fields.Many2many('batch.account.writeoff', 'account_payment_writeoff_rel', 'payment_id', 'writeoff_id')

    def _create_payment_entry(self, amount):
        """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
            Return the journal entry.
        """
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)
        debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(amount, self.currency_id, self.company_id.currency_id)

        move = self.env['account.move'].create(self._get_move_vals())

        #Write line corresponding to invoice payment
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)

        #Reconcile with the invoices
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            if self.writeoff_account_id:
                writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
                debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(self.payment_difference, self.currency_id, self.company_id.currency_id)
                writeoff_line['name'] = self.writeoff_label
                writeoff_line['account_id'] = self.writeoff_account_id.id
                writeoff_line['debit'] = debit_wo
                writeoff_line['credit'] = credit_wo
                writeoff_line['amount_currency'] = amount_currency_wo
                writeoff_line['currency_id'] = currency_id
                writeoff_line = aml_obj.create(writeoff_line)
                if counterpart_aml['debit'] or (writeoff_line['credit'] and not counterpart_aml['credit']):
                    counterpart_aml['debit'] += credit_wo - debit_wo
                if counterpart_aml['credit'] or (writeoff_line['debit'] and not counterpart_aml['debit']):
                    counterpart_aml['credit'] += debit_wo - credit_wo
                counterpart_aml['amount_currency'] -= amount_currency_wo
            if self.writeoff_account_ids:
                for wreteoff in self.writeoff_account_ids:
                    writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
                    debit_wo, credit_wo, amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date)._compute_amount_fields(wreteoff.amount, self.currency_id, self.company_id.currency_id)
                    writeoff_line['name'] = wreteoff.writeoff_label
                    writeoff_line['account_id'] = wreteoff.writeoff_account_id.id
                    writeoff_line['debit'] = debit_wo
                    writeoff_line['credit'] = credit_wo
                    writeoff_line['amount_currency'] = amount_currency_wo
                    writeoff_line['currency_id'] = currency_id
                    writeoff_line = aml_obj.create(writeoff_line)
                    if counterpart_aml['debit'] or (writeoff_line['credit'] and not counterpart_aml['credit']):
                        counterpart_aml['debit'] += credit_wo - debit_wo
                    if counterpart_aml['credit'] or (writeoff_line['debit'] and not counterpart_aml['debit']):
                        counterpart_aml['credit'] += debit_wo - credit_wo
                    counterpart_aml['amount_currency'] -= amount_currency_wo

        #Write counterpart lines
        if not self.currency_id.is_zero(self.amount):
            if not self.currency_id != self.company_id.currency_id:
                amount_currency = 0
            liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
            liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
            aml_obj.create(liquidity_aml_dict)

        #validate the payment
        if not self.journal_id.post_at_bank_rec:
            move.post()

        #reconcile the invoice receivable/payable line(s) with the payment
        if self.invoice_ids:
            self.invoice_ids.register_payment(counterpart_aml)

        return move    

class hv_account_invoice(models.Model):
    _inherit = "account.invoice"
    
    def _search_id(self, query):
        if not query:
            return []
        self._cr.execute(query)
        res = self._cr.fetchall()
        if not res:
            return []
        return [r[0] for r in res]

class hv_batch_invoice(models.Model):
    _name = 'batch.invoice'

    name = fields.Char(string='Batch Name', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', help="Filter open invoices by selected customer.")
    invoice_ids = fields.Many2many('account.invoice','batch_account_invoice_rel', 'batch_id', 'invoice_id', string='Add Invoices to Batch')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', copy=False, string="Status")
    total = fields.Float(string='Total Amount', readonly=True, compute='_compute_total')
    rebate = fields.Float(string='Rebate Amount', readonly=True, compute='_compute_total')

    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        # res = {'domain': {'invoice_ids': [('partner_id', '=', self.customer_id.id), ('state', '=', 'open'), ('type', 'in', ['out_invoice', 'out_refund'])]}}
        res = {}
        if self.customer_id != self._origin.customer_id and self.invoice_ids:
            self.invoice_ids = [(6, 0, [])]
            warning = {
            'title': 'Change customer warning',
            'message': 'Once change customer, your selected invoices will be remove.'
            }
            res.update({'warning': warning})
        return res

    @api.one
    @api.depends('invoice_ids', 'customer_id')
    def _compute_total(self):
        self.total = 0.0
        self.rebate = 0.0
        if self.invoice_ids:
            self.total += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.residual_signed for i in self.invoice_ids])
            # self.rebate += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.amount_total_signed for i in self.invoice_ids])
        self.rebate = round(self.total * self.customer_id.rebate / 100, 2)

    def action_register_payment_hv(self):
        if not self.invoice_ids:
            raise UserError(_('You cannot register without any invoice.'))
        return {
        'name': 'Register Payment',
        'type': 'ir.actions.act_window',
        'view_type': 'form',
        'view_mode': 'form',
        'res_model': 'account.register.payments',
        'src_model': 'account.invoice',
        'multi': True,
        'view_id': self.env.ref('hv_batch_invoice.view_account_payment_from_invoices').id,
        'target': 'new',
        'key2':'client_action_multi',
        'context': {
                'active_model': 'account.invoice',
                'active_ids': [x.id for x in self.invoice_ids],
                'batch_invoice_id': self.id
                }
        }
        
    def import_statement(self):
        return {
        'name': 'Import Invoices',
        'type': 'ir.actions.act_window',
        'view_type': 'form',
        'view_mode': 'form',
        'res_model': 'batch.invoice.import',
        'view_id': self.env.ref('hv_batch_invoice.account_invoice_import_view').id,
        'target': 'new',
        'nodestroy': True,
        'context': {'batch_invoice_id': self.id},
        }

class InvoiceImport(models.TransientModel):
    _name = "batch.invoice.import"
    _description = 'Import Invoices'

    data_file = fields.Binary(string='Invoice Statement File', required=True, help='Get your invoice statements in electronic format from your invoice and select them here.')
    filename = fields.Char()
    total_rows = fields.Integer(readonly=True)
    import_rows = fields.Integer(readonly=True)

    def _check_csv(self, filename):
        return filename and filename.lower().strip().endswith('.csv')

    @api.multi
    def import_file(self):
        if not self._check_csv(self.filename):
            raise UserError(_('Cannot verify your .csv file.'))
        csv_data = base64.b64decode(self.data_file) or b''
        if not csv_data:
            raise UserError(_('No data found in your .csv file.'))
        rows = self._read_csv(csv_data, OPTIONS)
        fields = list(itertools.islice(rows, 1))
        if not fields:
            raise UserError(_("You must configure any data in csv file."))
        fields = fields[0]
        indices = [index for index, field in enumerate(fields) if field]
        if not indices:
            raise UserError(_("You must configure any field in csv file."))
        # If only one index, itemgetter will return an atom rather
        # than a 1-tuple
        if len(indices) == 1:
            mapper = lambda row: [row[indices[0]]]
        else:
            mapper = operator.itemgetter(*indices)
        datas = [
            list(row) for row in pycompat.imap(mapper, rows)
            if any(row)
        ]  
        number_index = [index for index, data in enumerate(fields) if data.lower()=='tran no.']
        if not number_index:
            raise UserError(_("Invoice import need an 'Tran No.' field and data in csv file."))
                
        batch_invoice = self.env['batch.invoice'].browse(self._context.get('batch_invoice_id'))
        numbers=""
        for data in datas:
            numbers = numbers + "'" + data[number_index[0]] + "',"
        if len(numbers)==0:
            raise UserError(_("No data found."))
        numbers = numbers[0:len(numbers)-1]
        query = """
                SELECT ac.id
                    FROM account_invoice ac left join res_partner pa on ac.partner_id = pa.id 
                    where right(ac.number,5) in (%s) 
                        and ac.state = 'open' 
                        and ac.type in ('out_invoice','out_refund') 
                        and (pa.id = %s or pa.parent_id = %s)
                        """ % (numbers, batch_invoice.customer_id.id, batch_invoice.customer_id.id)
        invoice_ids = self.env['account.invoice']._search_id(query)
        if invoice_ids:
            batch_invoice.write({'invoice_ids' : [(4,  invoice_id) for invoice_id in invoice_ids]})

        self.total_rows = len(datas)
        self.import_rows = len(invoice_ids)
        return {
        'name': 'Import Result',
        'type': 'ir.actions.act_window',
        'view_type': 'form',
        'view_mode': 'form',
        'res_model': 'batch.invoice.import',
        'view_id': self.env.ref('hv_batch_invoice.action_account_invoice_change_customer_confirm').id,
        'res_id': self.id,
        'target': 'new',
        'nodestroy': True,
        'context': {'rows': len(invoice_ids)}
        }

    def _read_csv(self, csv_data, options):
        """ Returns a CSV-parsed iterator of all non-empty lines in the file
            :throws csv.Error: if an error is detected during CSV parsing
        """
        encoding = options.get('encoding')
        if not encoding:
            encoding = options['encoding'] = chardet.detect(csv_data)['encoding'].lower()

        if encoding != 'utf-8':
            csv_data = csv_data.decode(encoding).encode('utf-8')

        separator = options.get('separator')
        if not separator:
            # default for unspecified separator so user gets a message about
            # having to specify it
            separator = ','
            for candidate in (',', ';', '\t', ' ', '|', unicodedata.lookup('unit separator')):
                # pass through the CSV and check if all rows are the same
                # length & at least 2-wide assume it's the correct one
                it = pycompat.csv_reader(io.BytesIO(csv_data), quotechar=options['quoting'], delimiter=candidate)
                w = None
                for row in it:
                    width = len(row)
                    if w is None:
                        w = width
                    if width == 1 or width != w:
                        break # next candidate
                else: # nobreak
                    separator = options['separator'] = candidate
                    break

        csv_iterator = pycompat.csv_reader(
            io.BytesIO(csv_data),
            quotechar=options['quoting'],
            delimiter=separator)

        return (
            row for row in csv_iterator
            if any(x for x in row if x.strip())
        )