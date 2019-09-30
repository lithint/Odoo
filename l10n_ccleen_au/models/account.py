# -*- coding: utf-8 -*-
"""account model."""

from odoo import api, models, _
from odoo.exceptions import UserError


class Account(models.Model):
    """account model."""

    _inherit = "account.account"

    @api.model
    def _search_new_account_code(self, company, digits, prefix):
        """Overwritten this method to fix the chart of account code issue."""
        for num in range(1, 10000):
            existing_code = str(prefix.ljust(digits - 1, '0'))
            rec = self.search([('code', '=', existing_code),
                               ('company_id', '=', company.id)],
                              limit=1)
            if not rec:
                return existing_code

            new_code = str(prefix.ljust(digits - 1, '0')) + str(num)
            rec = self.search([('code', '=', new_code),
                               ('company_id', '=', company.id)],
                              limit=1)
            if not rec:
                return new_code
        raise UserError(_('Cannot generate an unused account code.'))


class AccountChartTemplate(models.Model):
    """Account Chart Template."""

    _inherit = "account.chart.template"

    @api.model
    def _prepare_transfer_account_template(self):
        """Prepare values to create the transfer account.

        that is an intermediary account used when moving money
        from a liquidity account to another.
        :return:    A dictionary of values to create a new account.account.

        Overwritten this method to fix the chart of account code issue.
        """
        digits = self.code_digits
        prefix = self.transfer_account_code_prefix or ''
        # Flatten the hierarchy of chart templates.
        chart_template = self
        chart_templates = self
        while chart_template.parent_id:
            chart_templates += chart_template.parent_id
            chart_template = chart_template.parent_id
        new_code = ''
        for num in range(1, 100):
            existing_code = str(prefix.ljust(digits - 1, '0'))
            rec = self.env['account.account.template'].search(
                [('code', '=', existing_code),
                 ('chart_template_id', 'in', chart_templates.ids)],
                limit=1)
            if not rec:
                new_code = existing_code
                break

            new_code = str(prefix.ljust(digits - 1, '0')) + str(num)
            rec = self.env['account.account.template'].search([
                ('code', '=', new_code),
                ('chart_template_id', 'in', chart_templates.ids)],
                limit=1)
            if not rec:
                break
        else:
            raise UserError(_('Cannot generate an unused account code.'))
        current_assets_type = self.env.ref(
            'account.data_account_type_current_assets',
            raise_if_not_found=False)
        return {
            'name': _('Liquidity Transfer'),
            'code': new_code,
            'user_type_id': current_assets_type and
            current_assets_type.id or False,
            'reconcile': True,
            'chart_template_id': self.id,
        }
