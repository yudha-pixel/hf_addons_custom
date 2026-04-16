# -*- coding: utf-8 -*-
{
    'name': 'Heritage Foods - FOTS Field Sales Manager',
    'version': '1.1.1',
    'category': 'Sales',
    'summary': 'Field agent stock allocation, sales sessions, and commission tracking for FOTS Team',
    'description': """
Heritage Foods FOTS Field Sales Manager
========================================
Manages field sales operations for FOTS agents: stock allocation, daily sales sessions,
commission computation, and performance reporting.

Features:
---------
* Team and agent management with commission rates
* Security deposit transactions (deposit, refund, deduction)
* Daily sales session workflow (allocate → sell → close)
* Automatic stock moves (warehouse → agent → customer / return)
* Commission calculation per session
* Agent Sales and Team Performance reports
    """,
    'author': 'Yudha/Heritage Foods Development Team',
    'website': 'https://www.heritagefoods.ltd',
    'depends': [
        'base',
        'mail',
        'stock',
        'uom',
        'product',
        'sale',
        'sale_management',
        'sales_team',
        'account',
    ],
    'data': [
        # Security
        'security/fots_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/sequence_data.xml',

        # Views
        'views/fots_team_views.xml',
        'views/fots_agent_views.xml',
        'views/fots_sale_order_views.xml',
        'views/fots_operations_views.xml',
        'views/fots_reports_views.xml',
        'views/fots_menus.xml',
    ],
    # 'demo': [
    #     'data/fots_demo_data.xml'
    # ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
