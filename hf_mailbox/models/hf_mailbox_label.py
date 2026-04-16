# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HfMailboxLabel(models.Model):
    _name = 'hf.mailbox.label'
    _description = 'Mailbox Label'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(default=0)
    sequence = fields.Integer(default=10)
    user_id = fields.Many2one(
        'res.users',
        string='Owner',
        help="Leave empty to share this label with all users.",
        ondelete='cascade',
    )
    active = fields.Boolean(default=True)
    system_key = fields.Char(
        help="Stable key for system labels (waiting_reply, followup, done).",
        index=True,
    )

    _unique_system_key_per_user = models.Constraint(
        'UNIQUE(system_key, user_id)',
        'A system label with this key already exists for this user.',
    )

    @api.model
    def _get_system_label(self, system_key):
        """Return (and lazily create) a shared system label."""
        if not system_key:
            return self.browse()
        return self.sudo().search([
            ('system_key', '=', system_key),
            ('user_id', '=', False),
        ], limit=1)
