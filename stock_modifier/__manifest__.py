# -*- coding: utf-8 -*-
{
    'name': 'Heritage Foods - Stock Modifier',
    'version': '1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Custom warehouse, locations, and reordering rules for Heritage Foods',
    'description': """
Heritage Foods Stock Configuration
===================================
This module configures:
- Multi-warehouse setup (Lagos HQ, Abuja)
- Stock location hierarchy for each warehouse
- Reordering rules for automated replenishment
    """,
    'depends': ['stock', 'product_expiry'],
    'data': [
        'security/ir.model.access.csv',
        'data/stock_warehouse_data.xml',
        'data/stock_location_data.xml',
        'data/stock_orderpoint_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
