"""Stock Picking Model."""

from odoo import api, fields, models


class Picking(models.Model):
    """Stock Picking Model."""

    _inherit = "stock.picking"

    @api.depends('state')
    @api.one
    def _get_invoiced(self):
        """Method to get the total invoiced count."""
        for order in self:
            invoice_ids = self.env['account.invoice'].search(
                [('picking_id', '=', order.id)])
            order.invoice_count = len(invoice_ids)

    invoice_count = fields.Integer(
        string='# of Invoices', compute='_get_invoiced',)

    @api.multi
    def button_view_invoice(self):
        """Method to view invoice with filters."""
        mod_obj = self.env['ir.model.data']
        act_obj = self.env['ir.actions.act_window']
        work_order_id = self.env['account.invoice'].search(
            [('picking_id', '=', self.id)])
        inv_ids = []

        for inv_id in work_order_id:
            inv_ids.append(inv_id.id)
            result = mod_obj.get_object_reference(
                'account', 'action_invoice_tree1')
            id = result and result[1] or False
            result = act_obj.browse(id).read()[0]
            res = mod_obj.get_object_reference('account', 'invoice_form')
            result['views'] = [(res and res[1] or False, 'form')]
            result['res_id'] = work_order_id[0].id or False
        return result

    @api.multi
    def action_done(self):
        """Overridden method to generate the invoice based on shipment."""
        super(Picking, self).action_done()
        if self.state == 'done':
            if self.picking_type_id.code == 'incoming':
                account_inv_obj = self.env['account.invoice']
                vals = {
                    'type': 'in_invoice',
                    'origin': self.origin,
                    'pur_id': self.purchase_id.id,
                    'purchase_id': self.purchase_id.id,
                    'partner_id': self.partner_id.id,
                    'picking_id': self.id
                }

                res = account_inv_obj.create(vals)
                res.purchase_order_change()
                res.compute_taxes()
                res._onchange_partner_id()
                for purchase_line in account_inv_obj.invoice_line_ids:
                    if purchase_line.quantity <= 0:
                        purchase_line.unlink()

            if self.picking_type_id.code == 'outgoing':
                inv_obj = self.env['account.invoice']
                sale_order_line_obj = self.env['account.invoice.line']
                sale_order = self.env['sale.order'].search([
                    ('name', '=', self.origin)])
                if sale_order:
                    bank_acc = inv_obj._get_default_bank_id(
                        'out_invoice',
                        self.company_id and self.company_id.id)
                    invoice = inv_obj.create({
                        'origin': self.origin,
                        'picking_id': self.id,
                        'type': 'out_invoice',
                        'reference': False,
                        'sale_id': sale_order.id,
                        'account_id': self.partner_id and
                        self.partner_id.property_account_receivable_id and
                        self.partner_id.property_account_receivable_id.id,
                        'partner_id': self.partner_id.id,
                        'currency_id': sale_order.pricelist_id.currency_id.id,
                        'payment_term_id': sale_order.payment_term_id.id,
                        'fiscal_position_id': sale_order.fiscal_position_id and
                        sale_order.fiscal_position_id.id or
                        sale_order.partner_id and
                        sale_order.partner_id.property_account_position_id.id,
                        'team_id': sale_order.team_id.id,
                        'comment': sale_order.note,
                        'partner_bank_id': bank_acc and bank_acc.id or False
                    })
                    invoice.date_invoice = fields.Datetime.now().date()
                    for sale_line in self.move_lines:
                        if sale_line.product_id.property_account_income_id:
                            account = sale_line.product_id and \
                                sale_line.product_id.property_account_income_id
                        elif sale_line.product_id.categ_id.\
                                property_account_income_categ_id:
                            account = sale_line.product_id and \
                                sale_line.product_id.categ_id.\
                                property_account_income_categ_id
                        else:
                            account_search = \
                                self.env['ir.property'].search(
                                    [('name', '=',
                                        'property_account_income_categ_id')])
                            account = account_search.value_reference
                            account = account.split(",")[1]
                            account = self.env['account.account'].\
                                browse(account)
                        inv_line = sale_order_line_obj.create({
                            'name': sale_line.name,
                            'account_id': account.id,
                            'invoice_id': invoice.id,
                            'price_unit': sale_line.price_unit * -1,
                            'quantity': sale_line.product_uom_qty,
                            'uom_id': sale_line.product_id.uom_id.id,
                            'product_id': sale_line.product_id.id,
                        })
                        order_line = self.env['sale.order.line'].search(
                            [('order_id', '=', sale_order.id),
                             ('product_id', '=', sale_line.product_id.id)])
                        for order_line in order_line:
                            order_line.write({
                                'qty_to_invoice': sale_line.product_uom_qty,
                                'invoice_lines': [(4, inv_line.id)]
                            })

                        tax_ids = []
                        if order_line and order_line[0]:
                            for tax in order_line[0].tax_id:
                                tax_ids.append(tax.id)
                                inv_line.write({
                                    'price_unit': order_line[0].price_unit,
                                    'discount': order_line[0].discount,
                                    'invoice_line_tax_ids': [(6, 0, tax_ids)]
                                })
                    invoice.compute_taxes()
        return True
