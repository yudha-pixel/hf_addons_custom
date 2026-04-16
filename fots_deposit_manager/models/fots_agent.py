# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FotsAgent(models.Model):
    _name = 'fots.agent'
    _description = 'FOTS Agent'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(
        string='Agent Code',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )

    phone = fields.Char(tracking=True)
    email = fields.Char(tracking=True)
    street = fields.Char(tracking=True)
    street2 = fields.Char(tracking=True)
    city = fields.Char(tracking=True)
    state_id = fields.Many2one('res.country.state', tracking=True)
    zip = fields.Char(tracking=True)
    country_id = fields.Many2one('res.country', tracking=True)

    team_id = fields.Many2one(
        'fots.team',
        string='Team',
        required=True,
        ondelete='restrict',
        tracking=True,
    )

    manager_id = fields.Many2one(
        related='team_id.manager_id',
        store=True,
        readonly=True,
    )

    user_id = fields.Many2one(
        'res.users',
        string='User Account',
        tracking=True,
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        tracking=True,
    )

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Default Pricelist',
        tracking=True,
        help='Pricelist auto-applied on sales orders created for this agent (e.g. wholesale NGN per dozen).',
    )

    active = fields.Boolean(default=True, tracking=True)

    sale_order_count = fields.Integer(
        compute='_compute_sale_order_count',
        string='Sales Orders',
    )

    _code_unique = models.Constraint(
        'unique (code)',
        'Agent code must be unique!',
    )

    @api.model_create_multi
    def create(self, vals_list):
        seen_partner_ids = set()

        for vals in vals_list:
            if vals.get('code', _('New')) == _('New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('fots.agent') or _('New')

            partner_id = vals.get('partner_id')
            if not partner_id:
                partner_vals = self._prepare_partner_vals(vals)
                partner = self.env['res.partner'].create(partner_vals)
                if not partner:
                    raise ValidationError(_('Unable to auto-create customer for this agent.'))
                partner_id = partner.id
                vals['partner_id'] = partner_id
            else:
                self._check_partner_conflict(partner_id)

            if partner_id in seen_partner_ids:
                raise ValidationError(_('The selected customer is already linked to another FOTS agent.'))
            seen_partner_ids.add(partner_id)

        return super().create(vals_list)

    def _compute_sale_order_count(self):
        SaleOrder = self.env['sale.order']
        for agent in self:
            agent.sale_order_count = SaleOrder.search_count([('fots_agent_id', '=', agent.id)])

    @api.constrains('partner_id')
    def _check_partner_unique(self):
        for agent in self:
            if not agent.partner_id:
                continue
            self._check_partner_conflict(agent.partner_id.id, exclude_agent_id=agent.id)

    def _check_partner_conflict(self, partner_id, exclude_agent_id=False):
        conflict = self.with_context(active_test=False).search([
            ('partner_id', '=', partner_id),
            ('id', '!=', exclude_agent_id or 0),
        ], limit=1)
        if conflict:
            raise ValidationError(_(
                'The selected customer is already linked to FOTS agent "%s" (including archived agents).'
            ) % conflict.display_name)

    def _prepare_partner_vals(self, agent_vals):
        partner_vals = {
            'name': agent_vals.get('name'),
            'customer_rank': 1,
        }
        mapped_fields = [
            'phone',
            'email',
            'street',
            'street2',
            'city',
            'state_id',
            'zip',
            'country_id',
        ]
        for field_name in mapped_fields:
            if agent_vals.get(field_name):
                partner_vals[field_name] = agent_vals[field_name]
        return partner_vals

    def action_view_sale_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Orders'),
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('fots_agent_id', '=', self.id)],
            'context': {
                **(self.env.context or {}),
                'default_fots_agent_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }
