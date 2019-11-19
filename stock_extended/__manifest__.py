# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    # Module information
    'name': 'Stock Extended',
    'version': '12.0.1.0.0',
    'category': 'stock',
    'sequence': 1,
    'summary': """Stock Extended.""",
    'description': """
        Stock Extended to improve the Product Moves report.
    """,

    # Author
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'http://www.serpentcs.com',

    # Dependencies
    'depends': ['stock', 'sale_management'],

    # Views
    'data': [
        'views/stock_move_line_views.xml',
    ],

    # Techical
    'installable': True,
    'auto_install': False
}
