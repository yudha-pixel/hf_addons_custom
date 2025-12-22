# -*- coding: utf-8 -*-
{
    'name': 'Heritage Foods - Point of Sale Modifier',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'summary': 'Custom POS configuration for Heritage Foods Traffic Hawkers',
    'description': """
Heritage Foods POS Configuration
=================================
This module configures:
- POS configuration for Traffic Hawkers (FOTS Team)
- Mobile-friendly interface settings
- Warehouse and location assignments
    """,
    'depends': ['point_of_sale', 'stock_modifier'],
    'data': [
        'security/ir.model.access.csv',
        'data/pos_config_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
