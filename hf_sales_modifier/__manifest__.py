# -*- coding: utf-8 -*-
{
    'name': 'Heritage Foods - Sales Modifier',
    'version': '1.0.0',
    'category': 'Sales',
    'summary': 'Read-only access profile for Head of Marketing',
    'author': 'Yudha/Heritage Foods Development Team',
    'website': 'https://www.heritagefoods.ltd',
    'depends': [
        'sale',
        'sales_team',
        'account',
        'stock',
    ],
    'data': [
        'security/hf_sales_security.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/hf_marketing_views.xml',
        'views/hf_marketing_menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
