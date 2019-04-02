# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo import api, exceptions, fields, models, _
MAP_INVOICE_TYPE_PAYMENT_SIGN = {
    'out_invoice': 1,
    'in_refund': -1,
    'in_invoice': -1,
    'out_refund': 1,
}

class hv_credit_limit_product(models.Model):
    _inherit = 'res.partner'

    credit_limit = fields.Float(string='Credit Limit', default=0.00)

    @api.onchange('credit_limit')
    def _rebate_onchange(self):
        if self.rebate<0:
            raise UserError(_('Credit Limit must be greater than 0.'))

class hv_credit_limit_sale_order_confirm(models.TransientModel):
    _name = 'sale.order.confirm'

    _message = fields.Text(readonly=True)
    
    @api.multi
    def action_overwrite(self):
        sale = self.env['sale.order'].browse(self._context.get('sale_id'))
        sale.confirm_result = 1
        sale.action_confirm()

class hv_credit_limit_SaleOrder(models.Model):
    _inherit = "sale.order"
    confirm_result = fields.Integer(defalut=0, store=False) 
    @api.multi
    def action_confirm(self):
        if self.confirm_result == 1:
            return super(hv_credit_limit_SaleOrder, self).action_confirm()

        invoice_ids = self.env['account.invoice'].search([('type', 'in', ['out_invoice', 'out_refund']),('state', '=', 'open'),('partner_id', '=', self.partner_id.id)])
        outstanding = 0.0
        if invoice_ids:
            outstanding += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.residual_signed for i in invoice_ids])
        
        if 'rebate' in self.partner_id._fields:
            outstanding -= round(outstanding * self.partner_id.rebate / 100, 2)

        if self.amount_total + outstanding > self.partner_id.credit_limit:
            _message = _('Total amount > Customer credit limit value, Click Confirm button to continue.\n Total amount: %s\n OutStanding: %s\n Credit Limit: %s') % (self.amount_total, outstanding, self.partner_id.credit_limit)
            confirm = self.env['sale.order.confirm'].create({'_message': _message})
            if self.user_has_groups('account.group_account_manager'):
                return {
                'name': 'Confirm Warning',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sale.order.confirm',
                'view_id': self.env.ref('hv_customer_credit_limit.action_confirm_warning').id,
                'res_id': confirm.id,
                'target': 'new',
                'nodestroy': True,
                'context':{'sale_id': self.id}
                }
            else:
                _message = _('Cannot confirm this order: Total amount > Customer credit limit value.\n Total amount: %s\n OutStanding: %s\n Credit Limit: %s') % (self.amount_total, outstanding, self.partner_id.credit_limit)
                raise UserError(_message)
        else:
            return super(hv_credit_limit_SaleOrder, self).action_confirm()
    

# class hv_batch_payment(models.Model):
#     _name = 'batch.payment'

#     name = fields.Char(string='Batch Name', required=True)
#     customer_id = fields.Many2one('res.partner', string='Customer', help="Filter open invoices by selected customer.")
#     invoice_ids = fields.Many2many('account.invoice','batch_account_paymnet_rel', 'batch_id', 'invoice_id', string='Add Invoices to Batch')
#     state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft', copy=False, string="Status")
#     total = fields.Float(string='Total Amount', readonly=True, compute='_compute_total')
#     rebate = fields.Float(string='Rebate Amount', readonly=True, compute='_compute_total')

#     @api.onchange('customer_id')
#     def _onchange_customer_id(self):
#         res = {'domain': {'invoice_ids': [('partner_id', '=', self.customer_id.id), ('state', '=', 'open'), ('type', 'in', ['in_invoice', 'in_refund'])]}}
#         if self.customer_id != self._origin.customer_id and self.invoice_ids:
#             self.invoice_ids = [(6, 0, [])]
#             warning = {
#             'title': 'Change customer warning',
#             'message': 'Once change customer, your selected invoices will be remove.'
#             }
#             res.update({'warning': warning})
#         return res

#     @api.one
#     @api.depends('invoice_ids')
#     def _compute_total(self):
#         self.total = 0.0
#         self.rebate = 0.0
#         if self.invoice_ids:
#             self.total += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.residual_signed for i in self.invoice_ids])
#             # self.rebate += sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.amount_total_signed for i in self.invoice_ids])

#         self.rebate = round(self.total * self.customer_id.rebate / 100, 2)

#     def action_register_payment_hv(self):
#         if not self.invoice_ids:
#             raise UserError(_('You cannot register without any invoice.'))
#         return {
#         'name': 'Register Payment',
#         'type': 'ir.actions.act_window',
#         'view_type': 'form',
#         'view_mode': 'form',
#         'res_model': 'account.register.payments',
#         'src_model': 'account.invoice',
#         'multi': True,
#         'view_id': self.env.ref('hv_batch_payment.view_account_payment_from_invoices').id,
#         'target': 'new',
#         'key2':'client_action_multi',
#         'context': {
#                 'active_model': 'account.invoice',
#                 'active_ids': [x.id for x in self.invoice_ids],
#                 'batch_payment_id': self.id
#                 }
#         }
        
#     def import_statement(self):
#         return {
#         'name': 'Import Invoices',
#         'type': 'ir.actions.act_window',
#         'view_type': 'form',
#         'view_mode': 'form',
#         'res_model': 'batch.payment.import',
#         'view_id': self.env.ref('hv_batch_payment.account_invoice_import_view').id,
#         'target': 'new',
#         'nodestroy': True,
#         'context': {'batch_payment_id': self.id},
#         }

# class InvoiceImport(models.TransientModel):
#     _name = "batch.payment.import"
#     _description = 'Import Invoices'

#     data_file = fields.Binary(string='Invoice Statement File', required=True, help='Get your invoice statements in electronic format from your invoice and select them here.')
#     filename = fields.Char()
#     total_rows = fields.Integer(readonly=True)
#     import_rows = fields.Integer(readonly=True)

#     def _check_csv(self, filename):
#         return filename and filename.lower().strip().endswith('.csv')

#     @api.multi
#     def import_file(self):
#         if not self._check_csv(self.filename):
#             raise UserError(_('Cannot verify your .csv file.'))
#         csv_data = base64.b64decode(self.data_file) or b''
#         if not csv_data:
#             raise UserError(_('No data found in your .csv file.'))
#         rows = self._read_csv(csv_data, OPTIONS)
#         fields = list(itertools.islice(rows, 1))
#         if not fields:
#             raise UserError(_("You must configure any data in csv file."))
#         fields = fields[0]
#         indices = [index for index, field in enumerate(fields) if field]
#         if not indices:
#             raise UserError(_("You must configure any field in csv file."))
#         # If only one index, itemgetter will return an atom rather
#         # than a 1-tuple
#         if len(indices) == 1:
#             mapper = lambda row: [row[indices[0]]]
#         else:
#             mapper = operator.itemgetter(*indices)
#         datas = [
#             list(row) for row in pycompat.imap(mapper, rows)
#             if any(row)
#         ]  
#         number_index = [index for index, data in enumerate(fields) if data.lower()=='number']
#         if not number_index:
#             raise UserError(_("Invoice import need an 'Number' field and data in csv file."))
                
#         batch = self.env['batch.payment'].browse(self._context.get('batch_payment_id'))
#         invoice_ids = self.env['account.invoice'].search([('number', 'in', [data[number_index[0]] for data in datas]),('state', '=', 'open'),('partner_id', '=', batch.customer_id.id)]).ids
#         if invoice_ids:
#             batch.write({'invoice_ids' : [(4,  invoice_id) for invoice_id in invoice_ids]})
#         self.total_rows = len(datas)
#         self.import_rows = len(invoice_ids)
#         return {
#         'name': 'Import Result',
#         'type': 'ir.actions.act_window',
#         'view_type': 'form',
#         'view_mode': 'form',
#         'res_model': 'batch.payment.import',
#         'view_id': self.env.ref('hv_batch_payment.action_account_invoice_change_customer_confirm').id,
#         'res_id': self.id,
#         'target': 'new',
#         'nodestroy': True,
#         'context': {'rows': len(invoice_ids)}
#         }

