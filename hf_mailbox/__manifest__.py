# -*- coding: utf-8 -*-
{
    'name': 'Heritage Foods - Mailbox (Gmail-style)',
    'version': '1.1.1',
    'category': 'Productivity/Discuss',
    'summary': 'Unified Gmail-like Inbox/Outbox with smart chaining and follow-up automation.',
    'description': """
Heritage Foods Mailbox
======================
Unified mailbox built on top of Odoo's mail framework:
* Aggregates messages from installed mail.thread models into hf.mailbox.thread
* Smart incoming-email chaining (normalized subject + participants fallback)
* User labels and follow-up automation via ir.cron
* Owl-powered Gmail-style three-pane client action
Non-invasive: links to mail.message without duplicating content.
""",
    'author': 'Yudha/Heritage Foods Development Team',
    'website': 'https://www.heritagefoods.ltd',
    'depends': ['mail', 'bus'],
    'data': [
        'security/hf_mailbox_security.xml',
        'security/ir.model.access.csv',
        'data/mailbox_label_data.xml',
        'data/ir_cron_data.xml',
        'views/hf_mailbox_label_views.xml',
        'views/hf_mailbox_views.xml',
        'views/hf_mailbox_compose_views.xml',
        'views/hf_mailbox_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hf_mailbox/static/src/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
