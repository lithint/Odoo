# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class wiz_mass_invoice(models.TransientModel):
    _name = 'wiz.mass.invoice'
    
    @api.multi 
    def mass_invoice_email_send(self):
        context = self._context
        active_ids = context.get('active_ids')
        super_user = self.env['res.users'].browse(SUPERUSER_ID)
        for a_id in active_ids:
            account_invoice_brw = self.env['account.invoice'].browse(a_id)
            for partner in account_invoice_brw.partner_id:
                partner_email = partner.email
                if not partner_email:
                    raise UserError(_('%s customer has no email id please enter email address')
                            % (account_invoice_brw.partner_id.name)) 
                else:
                    template_id = self.env['ir.model.data'].get_object_reference(
                                                                      'account', 
                                                                      'email_template_edi_invoice')[1]
                    email_template_obj = self.env['mail.template'].browse(template_id)
                    if template_id:
                        values = email_template_obj.generate_email(a_id, fields=None)
                        #values['email_from'] = super_user.email
                        values['email_to'] = partner.email
                        values['res_id'] = False
                        ir_attachment_obj = self.env['ir.attachment']
                        vals = {
                                'name' : account_invoice_brw.number or "Draft",
                                'type' : 'binary',
                                'datas_fname': values['attachments'][0][0],
                                'datas' : values['attachments'][0][1],
                                'res_id' : a_id,
                                'res_model' : 'account.invoice',
                                'datas_fname' : account_invoice_brw.number or "Draft",
                        }
                        attachment_id = ir_attachment_obj.create(vals)
                        # Set boolean field true after mass invoice email sent
                        account_invoice_brw.write({
                                                    'is_invoice_sent' : True
                                                 })
                        mail_mail_obj = self.env['mail.mail']
                        msg_id = mail_mail_obj.create(values)
                        msg_id.attachment_ids=[(6,0,[attachment_id.id])]
                        if msg_id:
                            mail_mail_obj.send([msg_id])
                                                     
        return True

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    is_invoice_sent = fields.Boolean('Is Invoice Sent',default=False)

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        context = self._context
        if context.get('default_model') == 'account.invoice' and \
                context.get('default_res_id') and context.get('mark_invoice_as_sent'):
            invoice = self.env['account.invoice'].browse(context['default_res_id'])
            # Set boolean field true after mass invoice email sent
            invoice.write({
                            'is_invoice_sent' : True
                         })
            invoice = invoice.with_context(mail_post_autofollow=True)
            invoice.sent = True
            invoice.message_post(body=_("Invoice sent"))
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
            

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
