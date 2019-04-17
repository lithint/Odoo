# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import api, exceptions, fields, models, _


class HaviWarning(models.TransientModel):
    _name = 'havi.message'

    title = fields.Char('Title', readonly=True)
    name = fields.Char('Name', readonly=True)

    @api.multi
    def action_warning(self, message, title):
        m = self.create({
            'title': title or 'Warning',
            'name': message,
        })
        return {
            'name': m.title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('hv_message.warning').id,
            'res_model': 'havi.message',
            'type': 'ir.actions.act_window',
            'res_id': m.id,
            'target': 'new',
            'context': {},
        }

    @api.multi
    def action_confirm(self, message, title):
        m = self.create({
            'title': title or 'Warning',
            'name': message,
        })
        return {
            'name': m.title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('hv_message.confirm').id,
            'res_model': 'havi.message',
            'type': 'ir.actions.act_window',
            'res_id': m.id,
            'target': 'new',
            'context': {},
        }
    
    @api.multi
    def action_confirm_yes(self):
        m = self.create({
            'title': 'Warning',
            'name': 'Please inherit havi.message model and build action_confirm_yes funciton.',
        })
        return {
            'name': m.title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('hv_message.warning').id,
            'res_model': 'havi.message',
            'type': 'ir.actions.act_window',
            'res_id': m.id,
            'target': 'new',
            'context': {},
        }