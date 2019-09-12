# -*- coding: utf-8 -*-
import os
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
OPTIONS = {
    'advanced': False, 
    'bank_stmt_import': True, 'date_format': '', 'datetime_format': '', 'encoding': 'ascii', 'fields': [], 'float_decimal_separator': '.', 'float_thousand_separator': ',', 'headers': True, 'keep_matches': False, 'name_create_enabled_fields': {'currency_id': False, 'partner_id': False}, 'quoting': '"', 'separator': ','}

module = os.path.dirname(__file__)
module = module[module.rfind('/')+1:]


class HaviDialog(models.TransientModel):
    _name = 'havi.message'

    module= fields.Char()
    title = fields.Char('Title', readonly=True)
    name = fields.Text('Name', readonly=True)
    data_file = fields.Binary(string='Select file to import', help='Get your file to import and select them here.')
    filename = fields.Char(string='File Name')

    def get_module(self):
        module = os.path.dirname(__file__)
        return module[module.rfind('/')+1:]

    @api.multi
    def action_warning(self, message, title=None):
        m = self.create({
            'module': self.get_module(),
            'title': title or 'Warning',
            'name': message,
        })
        return {
            'name': m.title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('hv_message.warning').id,
            'res_model': 'havi.message',
            'type': 'ir.actions.act_window',
            'res_id': m.id,
            'target': 'new',
        }

    @api.multi
    def action_confirm(self, message, title=None, module=None):
        if not module or not title:
            m = self.create({
            'title': 'Warning',
            'name': "To use Confirm dialog box, you must enter Title and Module values:\n\
self.env['havi.message'].with_context(active_model='Your model',batch_invoice_id='Your model id').action_confirm('Message', 'Title', 'Your module name')",
            })
            return {
                'name': m.title,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('hv_message.warning').id,
                'res_model': 'havi.message',
                'type': 'ir.actions.act_window',
                'res_id': m.id,
                'target': 'new',
            }
        m = self.create({
            'module': module,
            'title': title,
            'name': message,
        })
        return {
            'name': m.title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('hv_message.confirm').id,
            'res_model': 'havi.message',
            'type': 'ir.actions.act_window',
            'res_id': m.id,
            'target': 'new',
            'context': self._context,
        }

    @api.multi
    def action_import(self, message, title=None, module=None):
        if not module or not title:
            m = self.create({
            'title': 'Warning',
            'name': "To use Import dialog box, you must enter Title and Module values:\n\
self.env['havi.message'].with_context(active_model='Your model',batch_invoice_id='Your model id').action_import('Message', 'Title', 'Your module name')",
            })
            return {
                'name': m.title,
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('hv_message.warning').id,
                'res_model': 'havi.message',
                'type': 'ir.actions.act_window',
                'res_id': m.id,
                'target': 'new',
            }
        m = self.create({
            'module': module,
            'title': title,
            'name': message,
        })
        return {
            'name': m.title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('hv_message.import').id,
            'res_model': 'havi.message',
            'type': 'ir.actions.act_window',
            'res_id': m.id,
            'target': 'new',
            'context': self._context,
        }

    @api.multi
    def action_confirm_yes(self):
        m = self.create({
            'title': 'Warning',
            'name': "Copy this function to your code:\n\
class hv_message(models.TransientModel):\n\
    _name = 'havi.message'\n\
    _inherit = 'havi.message'\n\
\n\
    def action_confirm_yes(self):\n\
        if self.module=='%s' and self.title=='%s': \n\
            Your action code here!!!\n\
        else:\n\
            return super(hv_message, self).action_confirm_yes()" % (self.module, self.title),
        })
        return {
            'name': m.title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('hv_message.warning').id,
            'res_model': 'havi.message',
            'type': 'ir.actions.act_window',
            'res_id': m.id,
            'target': 'new',
        }

    @api.multi
    def action_confirm_no(self):
        m = self.create({
            'title': 'Warning',
            'name': "Copy this function to your code:\n\
class hv_message(models.TransientModel):\n\
    _name = 'havi.message'\n\
    _inherit = 'havi.message'\n\
\n\
    def action_confirm_no(self):\n\
        if self.module=='%s' and self.title=='%s': \n\
            Your action code here!!!\n\
        else:\n\
            return super(hv_message, self).action_confirm_no()" % (self.module, self.title),
        })
        return {
            'name': m.title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('hv_message.warning').id,
            'res_model': 'havi.message',
            'type': 'ir.actions.act_window',
            'res_id': m.id,
            'target': 'new',
        }
    @api.multi
    def import_file(self):
        m = self.create({
            'title': 'Warning',
            'name': "Copy this function to your code:\n\
class hv_message(models.TransientModel):\n\
    _name = 'havi.message'\n\
    _inherit = 'havi.message'\n\
\n\
    def import_file(self):\n\
        if self.module=='%s' and self.title=='%s': \n\
            Your action code here!!!\n\
        else:\n\
            return super(hv_message, self).import_file()" % (self.module, self.title),
        })
        return {
            'name': m.title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('hv_message.warning').id,
            'res_model': 'havi.message',
            'type': 'ir.actions.act_window',
            'res_id': m.id,
            'target': 'new',
        }

    def get_data(self):
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
        return fields, datas

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

    def _check_csv(self, filename):
        return filename and filename.lower().strip().endswith('.csv')