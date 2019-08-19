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

class HaviResult(models.Model):
    _name = 'havi.result'

    column0 = fields.Text(string='')
    column1 = fields.Text(string='')
    column2 = fields.Text(string='')
    column3 = fields.Text(string='')
    column4 = fields.Text(string='')
    column5 = fields.Text(string='')
    column6 = fields.Text(string='')
    column7 = fields.Text(string='')
    column8 = fields.Text(string='')
    column9 = fields.Text(string='')
    query_id = fields.Many2one('havi.query')

class HaviQuery(models.Model):
    _name = 'havi.query'
   
    name = fields.Text(string='Query')
    result = fields.One2many('havi.result', 'query_id', string='Result')
    f1  = fields.Char()

    @api.model
    def create(self, values):
        if 'f1' not in values:
            values['f1']='1'
        return super(HaviQuery, self).create(values)

    def action_query(self):
        self.result.unlink()
        query = self.name
        if not query:
            return []
        self._cr.execute(query)
        res = self._cr.fetchall()
        if not res:
            return
        result = {}
        for r in res:
            for x in range(0, len(r)):
                result['column%s' % x] = str(r[x])
            self.result += self.env['havi.result'].create(result)

   