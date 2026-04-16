# -*- coding: utf-8 -*-

from odoo import api, fields, models


class FotsTeam(models.Model):
    _name = 'fots.team'
    _description = 'FOTS Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    manager_id = fields.Many2one('res.users', string='Manager', tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, tracking=True)

    active = fields.Boolean(default=True, tracking=True)

    agent_ids = fields.One2many(
        'fots.agent',
        'team_id',
        string='Agents',
    )

    agent_count = fields.Integer(
        compute='_compute_agent_count',
        store=True,
    )

    @api.depends('agent_ids')
    def _compute_agent_count(self):
        for team in self:
            team.agent_count = len(team.agent_ids)

    def action_view_agents(self):
        self.ensure_one()
        action = self.env.ref('fots_deposit_manager.action_fots_agent').read()[0]
        action['domain'] = [('team_id', '=', self.id)]
        action['context'] = {
            **(self.env.context or {}),
            'default_team_id': self.id,
        }
        return action
