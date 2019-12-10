# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd. (<http://devintellecs.com>).
#
##############################################################################

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError

class purchase_confirm(models.TransientModel):
    """
    This wizard will confirm the all the selected draft supplier invoices
    """
    _name = "bulk.purchase.confirm"
    _description = "Confirm the selected purchase"
    
    @api.multi
    def send_purchase_mail(self,active_id):
        template_pool = self.env['mail.template']
        mail_template_id = self.env['ir.model.data'].get_object_reference('purchase', 'email_template_edi_purchase')[1]
        if mail_template_id:
            mtp = template_pool.browse(mail_template_id)
            mtp.send_mail(active_id,force_send=True)
        return True
    
    @api.multi
    def purchase_confirm(self):
        active_id = self._context.get('active_ids')
        purchase_obj = self.env['purchase.order']
        for purchase in purchase_obj.browse(active_id):
            if purchase.state not in('draft'):
                raise UserError(_('this record is not draft : %s') %(purchase.state))
            purchase.button_confirm()
            self.send_purchase_mail(purchase.id)
        return True
        




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
