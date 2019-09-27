# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    # Module information
    'name': 'Ccleen Australian - Accounting',
    'version': '12.0.1.0.0',
    'category': 'Localization',
    'sequence': 1,
    'description': """
    Ccleen Australian Accounting Module.
    Ccleen Australian accounting basic charts and localizations
    Also:
    - activates a number of regional currencies.
    """,

    # Author
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'http://www.serpentcs.com',

    # Dependencies
    'depends': ['account'],

    # Views
    'data': [
        'data/l10n_ccleen_au_chart_data.xml',
        'data/account.group.csv',
        'data/account.account.template.csv',
        'data/account_chart_template_data.xml',
        'data/account_chart_template_configure_data.xml',
        'data/res_currency_data.xml',
    ]
}
