# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class wiz_mass_sale_order(models.TransientModel):
    _name = 'wiz.mass.sale.order'
    
    @api.multi 
    def mass_sale_order_email_send(self):
        context = self._context
        active_ids = context.get('active_ids')
        super_user = self.env['res.users'].browse(SUPERUSER_ID)
        for a_id in active_ids:
            sale_order_brw = self.env['sale.order'].browse(a_id)
            for partner in sale_order_brw.partner_id:
                partner_email = partner.email
                if not partner_email:
                    raise UserError(_('%s customer has no email id please enter email address')
                            % (sale_order_brw.partner_id.name)) 
                else:
                    template_id = self.env['ir.model.data'].get_object_reference(
                                                                      'sale', 
                                                                      'email_template_edi_sale')[1]
                    email_template_obj = self.env['mail.template'].browse(template_id)
                    if template_id:
                        values = email_template_obj.generate_email(a_id, fields=None)
                        #values['email_from'] = super_user.email
                        values['email_to'] = partner.email
                        values['res_id'] = False
                        ir_attachment_obj = self.env['ir.attachment']
                        vals = {
                                'name' : sale_order_brw.name,
                                'type' : 'binary',
                                'datas_fname': values['attachments'][0][0],
                                'datas' : values['attachments'][0][1],
                                'res_id' : a_id,
                                'res_model' : 'sale.order',
                        }
                        attachment_id = ir_attachment_obj.create(vals)
                        # Set boolean field true after mass sale order email sent
                        sale_order_brw.write({
                                                    'is_sale_order_sent' : True
                                                 })
                        mail_mail_obj = self.env['mail.mail']
                        msg_id = mail_mail_obj.create(values)
                        msg_id.attachment_ids=[(6,0,[attachment_id.id])]
                        if msg_id:
                            mail_mail_obj.send([msg_id])
                                                     
        return True

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    is_sale_order_sent = fields.Boolean('Is Order Sent',default=False)
    
class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    @api.multi
    def send_mail(self, auto_commit=False):
        context = self._context
        if context.get('default_model') == 'sale.order' and \
                context.get('default_res_id') and context.get('mark_so_as_sent'):
            order = self.env['sale.order'].browse(context['default_res_id'])
            # Set boolean field true after mass sale order email sent
            order.write({
                            'is_sale_order_sent' : True
                         })
            order = order.with_context(mail_post_autofollow=True)
            order.sent = True
            order.message_post(body=_("Sale Order sent"))
        return super(MailComposeMessage, self).send_mail(auto_commit=auto_commit)
                    
        
            
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
