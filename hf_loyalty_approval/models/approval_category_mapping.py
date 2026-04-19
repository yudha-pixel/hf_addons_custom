# -*- coding: utf-8 -*-
import ast

from odoo import _, fields, models
from odoo.exceptions import UserError


class LoyaltyApprovalCategoryMapping(models.Model):
    _name = 'loyalty.approval.category.mapping'
    _description = 'Loyalty Approval Routing'
    _order = 'sequence, id'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=100)
    active = fields.Boolean(default=True)
    match_domain = fields.Char(string='Match Domain', default='[]', help="Domain over loyalty.program. Program matches if it satisfies this domain.")
    category_id = fields.Many2one('loyalty.approval.category', required=True, ondelete='restrict')
    is_default = fields.Boolean(help="Used when no other mapping matches. Should exist on exactly one record.")

    def _parse_domain(self):
        self.ensure_one()
        try:
            domain = ast.literal_eval(self.match_domain or '[]')
        except (ValueError, SyntaxError) as exc:
            raise UserError(_("Invalid match domain on '%s': %s", self.name, exc)) from exc
        if not isinstance(domain, list):
            raise UserError(_("Match domain on '%s' must be a list of tuples.", self.name))
        return domain

    def action_test_match(self):
        self.ensure_one()
        domain = self._parse_domain()
        count = self.env['loyalty.program'].search_count(domain)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': _("Match Preview"),
                'message': _("%s program(s) match this routing rule.", count),
                'sticky': False,
            },
        }

    @classmethod
    def _resolve_for_program(cls, program):
        env = program.env
        mappings = env['loyalty.approval.category.mapping'].search([
            ('active', '=', True),
            ('is_default', '=', False),
        ], order='sequence')
        for mapping in mappings:
            domain = mapping._parse_domain() + [('id', '=', program.id)]
            if env['loyalty.program'].search_count(domain):
                return mapping
        default = env['loyalty.approval.category.mapping'].search([
            ('active', '=', True),
            ('is_default', '=', True),
        ], limit=1)
        if not default:
            raise UserError(_(
                "No approval routing matches program '%s' and no default mapping is configured.",
                program.display_name,
            ))
        return default
