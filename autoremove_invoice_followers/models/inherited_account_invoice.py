
from odoo import api, fields, models, _

class MailFollowers(models.Model):
    _inherit = "mail.followers"
    
    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals in vals_list:
            if vals.get('res_model') != 'account.invoice':
                new_vals_list.append(vals)
        
    return super(MailFollowers, self).create(new_vals_list)


@api.model
    def create(self, vals):
        if vals.get('res_model') != 'account.invoice':
            return super(MailFollowers, self).create(vals)
        else:
            return self.env['mail.followers']
