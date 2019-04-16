# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError
from odoo import api, exceptions, fields, models, _


class HaviWarning(models.TransientModel):
    _name = 'havi.message'

    title = fields.Char('Title', readonly=True)
    name = fields.Char('Name', readonly=True)
    @api.multi
    def action_warning(self, message, title):
        self.create({
            'title': title or 'Warning',
            'name': message,
        })
        return {
            'name': self.title,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': self.env.ref('havi.message.warning').id,
            'res_model': 'havi.message',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'target': 'new',
            'context': {},
        }
