# -*- coding: utf-8 -*-
import base64
import itertools
import unicodedata
import chardet
import io
import operator

from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError
from odoo import api, exceptions, fields, models, _

# class CheckValueAbs(models.AbstractModel):
#     _name = 'havi.checkvalue.abs'

#     user_id = fields.Many2one('res.partner')
#     modelname = fields.Char()
#     fieldname = fields.Char()
#     sourceid = fields.Integer()
#     valueid = fields.Integer()
#     valuestr = fields.Char()

# class CheckValue(models.TransientModel):
#     _name = 'havi.checkvalue'
#     _inherit = 'havi.checkvalue.abs'

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # client_order_ref_dup = fields.Integer(store=False)
    # wanttosave = fields.Boolean(string='Save Change Before View', default=True, store=False)

    # @api.multi  
    # def write(self, vals):
    #     if vals.get('wanttosave') and vals['wanttosave']:
    #         return super(SaleOrder, self).create(vals)
    #     return self

    # @api.model
    # def create(self, vals):
    #     if vals.get('client_order_ref'):
    #         res = self.client_order_ref_search(vals.get('client_order_ref'), self.id)
    #         if res:
    #             vals['client_order_ref'] = ''
    #             if vals.get('wanttosave') and vals['wanttosave']:
    #                 return super(SaleOrder, self).create(vals)
    #             return res
    #     return super(SaleOrder, self).create(vals)

    def client_order_ref_search(self, val, id):
        return self.env['sale.order'].search([('client_order_ref', '=ilike', val),('id', '!=', id)], limit=1)

    @api.onchange('client_order_ref')
    def onchange_client_order_ref(self):
        # cv = self.env['havi.checkvalue'].search([('user_id', '=', self.env.user.id), ('modelname', '=', 'sale.order'), ('fieldname', '=', 'client_order_ref')], limit=1)
        # if not cv:
        #     cv.create({'user_id': self.env.user.id, 'modelname': 'sale.order', 'fieldname': 'client_order_ref',})
        #     cv = self.env['havi.checkvalue'].search([('user_id', '=', self.env.user.id), ('modelname', '=', 'sale.order'), ('fieldname', '=', 'client_order_ref')], limit=1)
        
        # cv.write({'valueid': 0})
        # self.client_order_ref_dup = 0
        if self.client_order_ref:
            if self._origin.id:
                res = self.client_order_ref_search(self.client_order_ref, self._origin.id)
            else:
                res = self.client_order_ref_search(self.client_order_ref, 0)
            if res:
                warning = {'warning': {
                'title': _("Duplicated SO Found!!!"),
                'message': _('Values "%s" was duplicated with SO: "%s"' % (self.client_order_ref, res.name)) 
                }}
                if self._origin.id:
                    self.client_order_ref = self._origin.client_order_ref
                else:
                    self.client_order_ref = False
                return warning
        
                # cv.write({'valueid': res.id, 'valuest': self.client_order_ref})
        # cv._cr.commit() 

    @api.depends('client_order_ref')
    def client_order_ref_check(self):
        # cv = self.env['havi.checkvalue'].search([('user_id', '=', self.env.user.id), ('modelname', '=', 'sale.order'), ('fieldname', '=', 'client_order_ref')], limit=1)
        # if not cv:
        #     cv.create({'user_id': self.env.user.id, 'modelname': 'sale.order', 'fieldname': 'client_order_ref',})
        # cv = self.env['havi.checkvalue'].search([('user_id', '=', self.env.user.id), ('modelname', '=', 'sale.order'), ('fieldname', '=', 'client_order_ref')], limit=1)
        # if not self.id:
        #     cv.write({'valueid': 0})
        #     self.client_order_ref_dup = 0
        #     if self.client_order_ref:
        #         res = self.client_order_ref_search(self.client_order_ref)
        #         if res:
        #             self.client_order_ref_dup = res.id
        #             cv.write({'valueid': res.id, 'valuest': self.client_order_ref})
        #     cv._cr.commit()            
        # else: 
        #     if cv and cv.valueid>0:
        #         self.client_order_ref_dup = cv.valueid
        return True
   
    def show_duplicate(self):
        if self._context.get('cus_ref_check'):
            return self.env['havi.message'].with_context(sale_id=self.id).action_confirm('Cannot open new Duplicated Window by itself.\n\nDo you want to reopen Duplicated Window','Duplicated Warning', 'hv_cus_ref_duplicate')
        
        cv = self.env['havi.checkvalue'].search([('user_id', '=', self.env.user.id), ('modelname', '=', 'sale.order'), ('fieldname', '=', 'client_order_ref')], limit=1)
        if cv.valueid != self.id:
            return {
            'name': 'Duplicated Customer Reference',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('sale.view_order_form').id,
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'res_id': cv.valueid,
            'target': 'new',
            'context': {'cus_ref_check':True},
            }
        return {}
        # return self.env['havi.message'].with_context().action_confirm('Values "%s" was duplicated.\n\nTo view duplicated invoice click on OK' % (self.client_order_ref),'Duplicated found','hv_cus_ref_duplicate')

# class hv_message(models.TransientModel):
#     _name = 'havi.message'
#     _inherit = 'havi.message'

#     def action_confirm_yes(self):
#         if self.module=='hv_cus_ref_duplicate' and self.title=='Duplicated Warning': 
#             return {
#                 'name': 'Duplicated Customer Reference',
#                 'view_type': 'form',
#                 'view_mode': 'form',
#                 'view_id': self.env.ref('sale.view_order_form').id,
#                 'res_model': 'sale.order',
#                 'type': 'ir.actions.act_window',
#                 'res_id': self._context.get('sale_id'),
#                 'target': 'new',
#                 'context': {'cus_ref_check':True},
#             }       
#         else:
#             return super(hv_message, self).action_confirm_yes()