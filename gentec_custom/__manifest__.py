# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Gentec - Custom',
    'version': '1.1',
    'category': 'Customization',
    'description': """
Gentec Customization Module
    """,
    'author': "Havi Technology",
    'website': "havi.com.au",
    'depends': ['sale', 'account', 'mrp'],
    'data': [
        'views/custom_sale_order.xml',
        'views/custom_invoice.xml',
        'views/product_views.xml',
    ],
}
