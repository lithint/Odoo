# -*- encoding: utf-8 -*-
{
    'name': 'Gentec Custom',
    'version': '1.0.1',
    'category': 'Gentec Custom',
    'summary': 'Gentec Custom',
    'description': "",
    'author': "Havi Technology",
    'website': "havi.com.au",
    'depends': [
        'mrp', 'sale', 'account',
    ],
    'data': [
        'views/custom_sale_order.xml',
        'views/custom_invoice.xml',
        'views/product_views.xml',
    ],
    'demo_xml': [],
    'installable': True,
}
