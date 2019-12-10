# -*- coding: utf-8 -*-


{
    'name': 'Auto Invoice from Picking(Shipment/Delivery)',
    'version': '12.0.0.0',
    'category': 'Accounting',
    'summary': 'This apps automatically create invoice from Picking when picking(Shipment/Delivery) get done',
    'description': """
    Automatic invoice from picking
    Automatic invoice from delivery order
    Automatic invoice from shipment
    picking invoice
    invoice picking
    invoice generation when picking get done
    create invoice from picking
    invoice created when picking done
    auto invoice creation when stock transffered.
    Auto invoice generation from picking

    Auto delivery invoice
    Auto invoice delivery order
    Auto invoice generation when delivery get done
    Auto create invoice from delivery order
    Auto invoice created when delivery done
    auto invoice creation when delivery transffered.
    Auto invoice generation from delivery order

    Auto delivery order invoice
    Auto invoice generation when delivery order get done
    Auto invoice created when delivery order done
    auto invoice creation when delivery order transffered.

    Auto shipment invoice
    Auto invoice shipment order
    Auto invoice generation when shipment get done
    Auto create invoice from shipment order
    Auto invoice created when shipment done
    auto invoice creation when shipment transffered.
    Auto invoice generation from shipment order

    Auto incoming shipment order invoice
    Auto invoice generation when shipment order get done
    Auto invoice created when shipment order done
    auto invoice creation when shipment order transffered.

    
""",
    'depends': ['sale','purchase','stock',],
    'data': [
        'views/inherited_account_invoice.xml',
        'views/inherited_stock_picking.xml'
    ],
    'demo': [],
    'js': [],
    'qweb': [],
    'installable': True,
    'auto_install': False,
    "images":['static/description/Banner.png'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
