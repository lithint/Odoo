# -*- coding: utf-8 -*-

from odoo.exceptions import UserError, ValidationError
from odoo import api, exceptions, fields, models, _
from odoo.tools import config, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, pycompat


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

class hv_account_abstract_payment(models.AbstractModel):
    _inherit = "account.abstract.payment"  
    

class hv_account_register_payment(models.TransientModel):
    _inherit = "account.register.payments"

    @api.multi
    def _prepare_payment_vals(self, invoices):
        values = super(hv_account_register_payment, self)._prepare_payment_vals(invoices)
        if self._context.get('batch_payment_id'):
            values.update({
                'batch_payment_id' : self._context.get('batch_payment_id'),
            })
        return values

    @api.multi
    def create_payments(self):
        if self.payment_method_id.code == 'aba_ct':
            batch_payment = self.env['account.batch.payment'].create({
                'state' : 'draft',
                'batch_type' : 'outbound',
                'journal_id' : self.journal_id.id,
                'payment_method_id' : self.payment_method_id.id,
            })
            self = self.with_context(batch_payment_id=batch_payment.id)

        action_vals = super(hv_account_register_payment, self).create_payments()
        
        if self.payment_method_id.code == 'aba_ct':
            action_vals = {
            'name': _('Batch Payments'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.batch.payment',
            'view_id': False,
            'res_id': batch_payment.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            }
        
        return action_vals

class hv_account_payment(models.Model):
    _inherit = "account.payment"

    email_send = fields.Integer(string='Send Times', default=0, readonly=True)
    email_vendor  = fields.Char(string='Email Address')
    email_cc  = fields.Char(string='CC')
    email_bcc  = fields.Char(string='BCC')
    payment_reference = fields.Char(string='Payment Reference')

    @api.model
    def create(self, vals):
        if self._context.get('batch_payment_id'):
            vals.update({'email_vendor': self.env['res.partner'].browse(vals.get('partner_id')).email})
        return super(hv_account_payment, self).create(vals)
    
    def preview_payments(self):
        default_template = self.env.ref('hv_send_remittance_advice.email_template_batch_payment', False)    
        vendor = {self.partner_id.id:{
            'partner_id': self.partner_id.id,
            'email_vendor': self.email_vendor,
            'email_cc': self.email_cc,
            'payment_ids':[self.id]
        }}
        if self.batch_payment_id.payment_ids:
            for item in self.batch_payment_id.payment_ids:
                if  vendor.get(item.partner_id.id):
                    if not vendor[item.partner_id.id]['email_vendor']:
                        vendor[item.partner_id.id]['email_vendor'] = item.email_vendor
                    if not vendor[item.partner_id.id]['email_cc']:
                        vendor[item.partner_id.id]['emal_cc'] = item.email_cc
                    vendor[item.partner_id.id]['payment_ids'].append(item.id) 
        for item in vendor:
            batch = self.env['batch.payment.email.send'].create({
                'name': self.batch_payment_id.name,
                'date': self.batch_payment_id.date,
                'currency_id': self.batch_payment_id.currency_id.id,
                'partner_id': vendor[item]['partner_id'],
                'email_vendor': vendor[item]['email_vendor'],
                'email_cc': vendor[item]['email_cc'],
                'payment_ids':[(6, 0, vendor[item]['payment_ids'])]
            })
            break  
        ctx = dict(
            active_model='batch.payment.email.send',
            active_id=batch.id,
            default_model='batch.payment.email.send',
            default_res_id=batch.id,
            default_use_template=bool(default_template),
            default_template_id=default_template and default_template.id or False,
            default_composition_mode='comment',
            force_email = True,
            )
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(self.env.ref('mail.email_compose_message_wizard_form').id, 'form')],
            'view_id': self.env.ref('mail.email_compose_message_wizard_form').id,
            'target': 'new',
            # 'res_id': wizard_mail.id,
            'context': ctx,

        }

class hv_batch_email_send_abs(models.AbstractModel):
    _name = "batch.payment.email.send.abstract"

    name = fields.Char(string='Name')
    currency_id = fields.Many2one('res.currency')
    date = fields.Date()
    partner_id = fields.Many2one('res.partner')
    email_vendor  = fields.Char(string='Email Address')
    email_cc  = fields.Char(string='CC')
    payment_ids = fields.Many2many('account.payment')

class hv_batch_email_send(models.TransientModel):
    _name = "batch.payment.email.send"
    _inherit = "batch.payment.email.send.abstract"

    total = fields.Monetary(compute="_total")

    @api.one
    @api.depends('payment_ids')
    def _total(self):
        self.total=0
        if self.payment_ids:
            for item in self.payment_ids:
                self.total += item.amount

class hv_account_batch_payment(models.Model):
    _inherit = 'account.batch.payment'

    payment_ids = fields.One2many('account.payment', 'batch_payment_id', string="Payments", required=False, readonly=False)
    
    @api.constrains('batch_type', 'journal_id', 'payment_ids')
    def _check_payments_constrains(self):
        for record in self:
            if record.payment_ids:
                all_companies = set(record.payment_ids.mapped('company_id'))
                if len(all_companies) > 1:
                    raise ValidationError(_("All payments in the batch must belong to the same company."))
                all_journals = set(record.payment_ids.mapped('journal_id'))
                if len(all_journals) > 1 or record.payment_ids[0].journal_id != record.journal_id:
                    raise ValidationError(_("The journal of the batch payment and of the payments it contains must be the same."))
                all_types = set(record.payment_ids.mapped('payment_type'))
                if len(all_types) > 1:
                    raise ValidationError(_("All payments in the batch must share the same type."))
                if all_types and record.batch_type not in all_types:
                    raise ValidationError(_("The batch must have the same type as the payments it contains."))
                all_payment_methods = set(record.payment_ids.mapped('payment_method_id'))
                if len(all_payment_methods) > 1:
                    raise ValidationError(_("All payments in the batch must share the same payment method."))
                if all_payment_methods and record.payment_method_id not in all_payment_methods:
                    raise ValidationError(_("The batch must have the same payment method as the payments it contains."))
    
    def validate_batch(self):
        records = self.filtered(lambda x: x.state == 'draft')
        for rec in records:
            if rec.payment_ids:
                i = 1
                group_partner = []
                for pm in rec.payment_ids:
                    if pm.partner_id.id not in group_partner:
                        group_partner.append(pm.partner_id.id)
                
                for g in group_partner:
                    for pm in rec.payment_ids:
                        if pm.partner_id.id == g:
                            pm.write({'state':'sent', 'payment_reference' : 'BO' + rec.name[-10:] + '/' + str(i)})
                    i += 1  

        records.write({'state': 'sent'})
        records = self.filtered(lambda x: x.file_generation_enabled)
        if records:
            return self.export_batch_payment()

    @api.model
    def create(self, vals):
        rec = super(hv_account_batch_payment, self).create(vals)
        if rec.payment_ids:
            for pm in rec.payment_ids:
                if not pm.email_vendor:
                    pm.write({'email_vendor' : pm.partner_id.email})    
        return rec

    @api.multi
    def write(self, vals):
        rec = super(hv_account_batch_payment, self).write(vals)
        if 'payment_ids' in vals:
            rec = self
            for pm in rec.payment_ids:
                if not pm.email_vendor:
                    pm.write({'email_vendor' : pm.partner_id.email})          
        return rec

    def action_send_remittance_advice(self):
        vendor = {}
        for item in self.payment_ids:
            if not vendor.get(item.partner_id.id):
                vendor.update({item.partner_id.id:{
                    'partner_id': item.partner_id.id,
                    'email_vendor': item.email_vendor,
                    'email_cc': item.email_cc,
                    'payment_ids':[item.id]
                }})
            else:
                if not vendor[item.partner_id.id]['email_vendor']:
                    vendor[item.partner_id.id]['email_vendor'] = item.email_vendor
                if not vendor[item.partner_id.id]['email_cc']:
                    vendor[item.partner_id.id]['emal_cc'] = item.email_cc
                vendor[item.partner_id.id]['payment_ids'].append(item.id) 
        if not vendor:
            return self.env['havi.message'].action_warning('Payment to send not found.','Send Remittance Advice')

        default_template = self.env.ref('hv_send_remittance_advice.email_template_batch_payment', False)      
        for item in vendor:
            batch = self.env['batch.payment.email.send'].create({
                'name': self.name,
                'date': self.date,
                'currency_id': self.currency_id.id,
                'partner_id': vendor[item]['partner_id'],
                'email_vendor': vendor[item]['email_vendor'],
                'email_cc': vendor[item]['email_cc'],
                'payment_ids':[(6, 0, vendor[item]['payment_ids'])]
            })
            # batch._cr.commit()
            ctx = dict(
                active_model='batch.payment.email.send',
                active_id=batch.id,
                default_model='batch.payment.email.send',
                default_res_id=batch.id,
                default_use_template=bool(default_template),
                default_template_id=default_template and default_template.id or False,
                # default_composition_mode='comment',
                default_composition_mode='mass_mail',

            )
            wizard_mail = self.env['mail.compose.message'].with_context(ctx).create({})
            wizard_mail.onchange_template_id_wrapper()
            wizard_mail.send_mail()
            for pid in batch.payment_ids:
                pid.email_send += 1
        return self.env['havi.message'].action_warning('Send remittance advice completed.','Send Remittance Advice')

    def cancel_payments(self):
        if self.payment_ids:
            self.payment_ids.cancel()
            self.payment_ids = [(5, 0, 0)]
        return self.env['havi.message'].action_warning('Payments cancel is completed.','Payments Cancel')
    