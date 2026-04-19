# -*- coding: utf-8 -*-
{
    'name': 'Heritage Foods - Loyalty Approval Matrix',
    'version': '1.1.1',
    'category': 'Sales/Loyalty',
    'summary': 'Configurable approval matrix for loyalty and promotion programs.',
    'description': """
Heritage Foods Loyalty Approval
===============================
Multi-level configurable approval workflow on loyalty.program:
* Approval categories + per-level approver pools
* Routing by tier (max reward discount % or fixed value)
* Delegation / out-of-office substitution at level activation
* Programs cannot be active until fully approved
""",
    'author': 'Yudha/Heritage Foods Development Team',
    'website': 'https://www.heritagefoods.ltd',
    'depends': ['loyalty', 'website_sale_loyalty', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/approval_category_data.xml',
        'data/approval_mapping_data.xml',
        'data/mail_template_data.xml',
        'views/approval_category_views.xml',
        'views/approval_mapping_views.xml',
        'views/approval_request_views.xml',
        'views/res_users_views.xml',
        'wizards/loyalty_rejection_wizard_views.xml',
        'views/loyalty_program_views.xml',
        'views/loyalty_program_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
