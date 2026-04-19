# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    loyalty_delegate_id = fields.Many2one(
        'res.users', string='Loyalty Approval Delegate',
        help="When active, new approval levels assigned to this user will route to the delegate instead.",
    )
    loyalty_delegate_from = fields.Date(string='Delegation Start')
    loyalty_delegate_to = fields.Date(string='Delegation End')
    loyalty_delegation_active = fields.Boolean(compute='_compute_loyalty_delegation_active')

    @api.depends('loyalty_delegate_id', 'loyalty_delegate_from', 'loyalty_delegate_to')
    def _compute_loyalty_delegation_active(self):
        today = fields.Date.today()
        for user in self:
            user.loyalty_delegation_active = bool(
                user.loyalty_delegate_id
                and user.loyalty_delegate_from
                and user.loyalty_delegate_to
                and user.loyalty_delegate_from <= today <= user.loyalty_delegate_to
            )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'loyalty_delegate_id', 'loyalty_delegate_from',
            'loyalty_delegate_to', 'loyalty_delegation_active',
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'loyalty_delegate_id', 'loyalty_delegate_from', 'loyalty_delegate_to',
        ]
