# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import io
import json

from odoo import api, fields, models, _
from datetime import datetime, date, timedelta

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    # TODO saas-17: remove the try/except to directly import from misc
    import xlsxwriter



class GstReport(models.TransientModel):
    _inherit = "account.report"
    _name = 'hv.gst.report'
    _description = 'GST Report '
    filter_date = {'date_from': '', 'date_to': '', 'filter': 'this_month'}
    filter_unfold_all = False
    MAX_LINES = None


    def _get_templates(self):
        templates = super(GstReport, self)._get_templates()
        # templates['main_template'] = 'hv_gst_report.hv_gst_report_template'
        return templates

    def _get_columns_name(self, options):
        columns = [
            {'name': _('Transaction Type')},
            {'name': _('Tax Code')},
            {'name': _('Transaction Date') , 'class': 'date'},
            {'name': _('Document Number')},
            {'name': _('Net Amount'), 'class': 'number'},
            {'name': _('Tax Amount'), 'class': 'number'}]

        return columns

    def get_xlsx(self, options, response):
        if self._name != 'hv.gst.report':
            super(GstReport, self).get_xlsx(options, response)
            return True
        saveunfold = options['unfold_all']
        options['unfold_all'] = True
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet(options.get('reportname')[:31])

        def_style = workbook.add_format({'font_name': 'Arial'})
        title_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2})
        super_col_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'align': 'center'})
        level_0_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_0_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2, 'pattern': 1, 'font_color': '#FFFFFF'})
        level_1_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2})
        level_1_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'left': 2})
        level_1_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'bottom': 2, 'top': 2, 'right': 2})
        level_2_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2})
        level_2_style_left = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'left': 2})
        level_2_style_right = workbook.add_format({'font_name': 'Arial', 'bold': True, 'top': 2, 'right': 2})
        level_3_style = def_style
        level_3_style_left = workbook.add_format({'font_name': 'Arial', 'left': 2})
        level_3_style_right = workbook.add_format({'font_name': 'Arial', 'right': 2})
        domain_style = workbook.add_format({'font_name': 'Arial', 'italic': True})
        domain_style_left = workbook.add_format({'font_name': 'Arial', 'italic': True, 'left': 2})
        domain_style_right = workbook.add_format({'font_name': 'Arial', 'italic': True, 'right': 2})
        upper_line_style = workbook.add_format({'font_name': 'Arial', 'top': 2})

        sheet.set_column(0, 0, 20) #  Set the first column width to 60
        sheet.set_column(1, 2, 50) #  Set the first column width to 60
        sheet.set_column(2, 3, 20) #  Set the first column width to 20
        sheet.set_column(4, 5, 15) #  Set the first column width to 15

        super_columns = self._get_super_columns(options)
        y_offset = bool(super_columns.get('columns')) and 1 or 0
        
        f16_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 18,'align': 'center'})
        f14_style = workbook.add_format({'font_name': 'Arial', 'bold': True, 'font_size': 16,'align': 'center'})
        sheet.write(0, 2, self.env.user.company_id.name, f14_style)
        sheet.write(1, 2, options.get('reportname'), f16_style)
        sheet.write(2, 2, options.get('date').get('date_from')+ ' - ' + options.get('date').get('date_to'), f14_style)
        y_offset = 4

        sheet.write(y_offset, 0, '', title_style)
        # Todo in master: Try to put this logic elsewhere
        x = super_columns.get('x_offset', 0)
        for super_col in super_columns.get('columns', []):
            cell_content = super_col.get('string', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
            x_merge = super_columns.get('merge')
            if x_merge and x_merge > 1:
                sheet.merge_range(0, x, 0, x + (x_merge - 1), cell_content, super_col_style)
                x += x_merge
            else:
                sheet.write(0, x, cell_content, super_col_style)
                x += 1
        
        for row in self.get_header(options):
            x = 0
            for column in row:
                colspan = column.get('colspan', 1)
                header_label = column.get('name', '').replace('<br/>', ' ').replace('&nbsp;', ' ')
                if colspan == 1:
                    sheet.write(y_offset, x, header_label, title_style)
                else:
                    sheet.merge_range(y_offset, x, y_offset, x + colspan - 1, header_label, title_style)
                x += colspan
            y_offset += 1
        ctx = self._set_context(options)
        ctx.update({'no_format':True, 'print_mode':True})
        lines = self.with_context(ctx)._get_lines(options)

        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines)

        if lines:
            max_width = max([len(l['columns']) for l in lines])

        for y in range(0, len(lines)):
            if lines[y].get('level') == 0:
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_0_style_left
                style_right = level_0_style_right
                style = level_0_style
            elif lines[y].get('level') == 1:
                for x in range(0, len(lines[y]['columns']) + 1):
                    sheet.write(y + y_offset, x, None, upper_line_style)
                y_offset += 1
                style_left = level_1_style_left
                style_right = level_1_style_right
                style = level_1_style
            elif lines[y].get('level') == 2:
                style_left = level_2_style_left
                style_right = level_2_style_right
                style = level_2_style
            elif lines[y].get('level') == 3:
                style_left = level_3_style_left
                style_right = level_3_style_right
                style = level_3_style
            # elif lines[y].get('type') != 'line':
            #     style_left = domain_style_left
            #     style_right = domain_style_right
            #     style = domain_style
            else:
                style = def_style
                style_left = def_style
                style_right = def_style
            sheet.write(y + y_offset, 0, lines[y]['name'], style_left)
            for x in range(1, max_width - len(lines[y]['columns']) + 1):
                sheet.write(y + y_offset, x, None, style)
            for x in range(1, len(lines[y]['columns']) + 1):
                # if isinstance(lines[y]['columns'][x - 1], tuple):
                    # lines[y]['columns'][x - 1] = lines[y]['columns'][x - 1][0]
                if x < len(lines[y]['columns']):
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1].get('name', ''), style)
                else:
                    sheet.write(y + y_offset, x + lines[y].get('colspan', 1) - 1, lines[y]['columns'][x - 1].get('name', ''), style_right)
            if 'total' in lines[y].get('class', '') or lines[y].get('level') == 0:
                for x in range(len(lines[0]['columns']) + 1):
                    sheet.write(y + 1 + y_offset, x, None, upper_line_style)
                y_offset += 1
        if lines:
            for x in range(max_width + 1):
                sheet.write(len(lines) + y_offset, x, None, upper_line_style)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
        options['unfold_all'] = saveunfold

    @api.model
    def _get_lines(self, options, line_id=None):
        convert_date = self.env['ir.qweb.field.date'].value_to_html
        lines = []
        if not line_id:
            select = """select c.id, c.name,sum(a.tax_base_amount) as net, sum(abs(a.balance)) tax 
                    from account_move_line a, account_journal c, account_tax b
                    where a.tax_line_id is not null and a.create_date>'%s'  and a.create_date<'%s'
                    and a.tax_line_id=b.id and b.account_id is not null and b.type_tax_use = '%s' and a.journal_id=c.id
                    group by c.id, c.name order by c.name
                """  % (options.get('date').get('date_from'), datetime.strptime(options.get('date').get('date_to'), '%Y-%m-%d').date()+timedelta(days=1), options.get('reporttype'))
        else:
            select = """select c.id, c.name,sum(a.tax_base_amount) as net, sum(abs(a.balance)) tax 
                    from account_move_line a, account_journal c, account_tax b
                    where a.tax_line_id is not null and a.create_date>'%s'  and a.create_date<'%s'
                    and a.tax_line_id=b.id and b.account_id is not null and b.type_tax_use = '%s'
                    and a.journal_id=c.id and c.id=%s
                    group by c.id, c.name order by c.name
                """  % (options.get('date').get('date_from'), datetime.strptime(options.get('date').get('date_to'), '%Y-%m-%d').date()+timedelta(days=1), options.get('reporttype'), line_id.split('_')[1])

        self.env.cr.execute(select, [])
        results = self.env.cr.dictfetchall()
        if not results:
            return lines
        # 3.Build report lines
        current_id = 0
        total_net = 0
        total_tax = 0

        for values in results:
            total_net += values['net']
            total_tax += values['tax']
            current_id = values['id']
            lines.append({
                    'id': 'journal_%s' % (current_id),
                    'name': '%s' % (values['name']),
                    'level': 2,
                    'columns': [{'name': n} for n in ['', '', '', self.format_value(values['net']), self.format_value(values['tax'])]],
                    'unfoldable': True,
                    'unfolded': 'journal_%s' % (current_id)  in options.get('unfolded_lines') or options.get('unfold_all'),
                })

            if 'journal_%s' % (current_id) in options.get('unfolded_lines') or options.get('unfold_all'):
                select = """select a.id, a.name, a.create_date, a.tax_base_amount net, abs(a.balance) tax,
                    case when trim(a.ref)='' or a.ref is null then d.name else a.ref end as ref
                    from account_move_line a, account_journal c ,account_tax b, account_move d
                    where a.tax_line_id is not null and a.create_date>'%s'  and a.create_date<'%s'
                    and a.tax_line_id=b.id and b.account_id is not null and b.type_tax_use = '%s'
                    and a.move_id=d.id and a.journal_id=c.id and c.id =%s order by a.create_date
                """  % (options.get('date').get('date_from'), datetime.strptime(options.get('date').get('date_to'), '%Y-%m-%d').date()+timedelta(days=1), options.get('reporttype'), current_id)

                self.env.cr.execute(select, [])
                results1 = self.env.cr.dictfetchall()
                for values1 in results1:
                    # # First, we add the total of the previous account line, if there was one
                    # if lines and lines[-1]['id'].startswith('month'):
                    #     lines.append(self._get_total(current_journal, current_account, results))
                    lines.append({
                        'id':  'line_%s' % (values1['id']),
                        'name': '',
                        'level': 4,
                        'parent_id': 'journal_%s' % (current_id) ,
                        'columns': [{'name': n} for n in [values1['name'], convert_date('%s-01' % (values1['create_date']), {'format': 'YYYY-MM-dd'}), values1['ref'], self.format_value(values1['net']), self.format_value(values1['tax'])]],
                    })

        if not line_id:
            total_columns = ['', '', '', self.format_value(total_net), self.format_value(total_tax)]
            lines.append({
                'id': 'grouped_total',
                'name': _('Total'),
                'level': 0,
                'class': 'o_account_reports_domain_total',
                'columns': [{'name': v} for v in total_columns],
            })
        # # Append the total value for the last generated account line, if it was unfolded
        # if self._need_to_unfold('account_%s_%s' % (current_account, current_journal), options):
        #     lines.append(self._get_total(current_journal, current_account, results))

        # # Append detail per month section
        # if not line_id:
        #     lines.extend(self._get_line_total_per_month(options, values['company_id'], results))
        return lines

        
        # total_initial_balance = total_debit = total_credit = total_balance = 0.0

    def _build_options(self, previous_options=None):
        options = super(GstReport, self)._build_options(previous_options)
        if self._context.get('reporttype') == 'sale':
            options['reportname'] =  _('GST on Sales')
            options['reporttype'] =  'sale'
        else:
            options['reportname'] =  _('GST on Purchases')
            options['reporttype'] =  'purchase'
        return options

    def get_report_filename(self, options):
        if self._name != 'hv.gst.report':
            return super(GstReport, self).get_report_filename(options)
        return options['reportname'].lower().replace(' ', '_')

    @api.model
    def _get_report_name(self):
        if self._context.get('reporttype') == 'sale':
            return _('GST on Sales')
        else:
            return _('GST on Purchases')
