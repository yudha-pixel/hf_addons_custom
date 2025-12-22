# -*- coding: utf-8 -*-
{
    'name': 'Heritage Foods - Sales Modifier',
    'version': '1.0',
    'category': 'Sales/Sales',
    'summary': 'Custom sales teams and access restrictions for Heritage Foods',
    'description': """
Heritage Foods Sales Configuration
===================================
This module configures:
- Sales teams for Field Sales Agents and Student Ambassadors
- Access restrictions for salespersons to see only their own customers and quotes
    """,
    'depends': ['sale', 'sales_team'],
    'data': [
        'security/ir.model.access.csv',
        'security/sales_security.xml',
        'data/crm_team_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
