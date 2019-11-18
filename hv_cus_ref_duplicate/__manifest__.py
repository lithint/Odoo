# -*- encoding: utf-8 -*-
##############################################################################
#
#    odoo, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Customer Reference Duplicate Check',
    'version': '12.0.1.0.0',
    'category': 'Sale Order',
    'summary': 'Sale Order',
    'description': "",
    'author': "Havi Technology",
    'website': "havi.com.au",
    'depends': [
        'sale_margin',
        'account',
        'hv_message'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_margin_view.xml',
        'views/account_invoice_view.xml'
    ],
    'demo_xml': [],
    'installable': True,
}
