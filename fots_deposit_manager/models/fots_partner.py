# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    fots_agent_ids = fields.One2many(
        'fots.agent',
        'partner_id',
        string='FOTS Agents',
        help='FOTS agent records linked to this partner. Used to filter FOTS-scoped invoices and payments.',
    )
