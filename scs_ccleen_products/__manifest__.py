# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    # Module information
    'name': 'Ccleen Products',
    'version': '12.0.1.0.0',
    'category': 'product',
    'sequence': 1,
    'summary': """Ccleen Products.""",
    'description': """Ccleen Products.""",

    # Author
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'http://www.serpentcs.com',

    # Dependencies
    'depends': ['stock'],

    # Views
    'data': [
        'data/product_data.xml'
    ],

    # Techical
    'installable': True,
    'auto_install': False
}
