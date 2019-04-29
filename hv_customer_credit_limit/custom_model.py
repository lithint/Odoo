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
    account_manager = fields.Boolean(compute='get_account_manager')

    @api.onchange('credit_limit')
    def _rebate_onchange(self):
        if self.credit_limit<0:
            raise UserError(_('Credit Limit must be greater than 0.'))
            
    def get_account_manager(self):
        self.account_manager = self.user_has_groups('account.group_account_manager')

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

        sale_ids = self.env['sale.order'].search([('state', 'in', ['sale']),('invoice_status', '!=', 'invoiced'),('partner_id', '=', self.partner_id.id)])
        sale = 0.00
        if sale_ids:
            sale += round(sum(i.amount_total for i in sale_ids),2)
        invoice_ids = self.env['account.invoice'].search([('type', 'in', ['out_invoice', 'out_refund']),('state', '=', 'open'),('partner_id', '=', self.partner_id.id)])
        outstanding = 0.0
        if invoice_ids:
            outstanding += round(sum([MAP_INVOICE_TYPE_PAYMENT_SIGN[i.type] * i.residual_signed for i in invoice_ids]),2)
        
        if 'rebate' in self.partner_id._fields:
            outstanding -= round(outstanding * self.partner_id.rebate / 100, 2)

        if self.amount_total + sale + outstanding > self.partner_id.credit_limit:
            _message = _('Total amount + OutStanding > Customer credit limit value, Click Confirm button to continue.\n Total amount: %s\n OutStanding: %s\n Credit Limit: %s') % (self.amount_total, outstanding, self.partner_id.credit_limit)
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
                _message = _('Cannot confirm this order: Total amount + OutStanding > Customer credit limit value.\n Total amount: %s\n OutStanding: %s\n Credit Limit: %s') % (self.amount_total, outstanding, self.partner_id.credit_limit)
                raise UserError(_message)
        else:
            return super(hv_credit_limit_SaleOrder, self).action_confirm()
    

