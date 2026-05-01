# -*- coding: utf-8 -*-
{
    'name': 'Heritage Foods - Inventory Modifier',
    'version': '1.1.2',
    'category': 'Inventory/Stock',
    'summary': 'Auto-correct internal transfer operation type based on source location warehouse',
    'author': 'Yudha/Heritage Foods Development Team',
    'website': 'https://www.heritagefoods.ltd',
    'depends': [
        'stock',
        'uom',
        'delivery',
        'sale_stock',
    ],
    'data': [
        'views/stock_picking_views.xml',
        'views/uom_uom_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
