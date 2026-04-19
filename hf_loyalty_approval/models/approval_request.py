# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LoyaltyApprovalRequest(models.Model):
    _name = 'loyalty.approval.request'
    _description = 'Loyalty Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(compute='_compute_name', store=True)
    program_id = fields.Many2one('loyalty.program', required=True, ondelete='cascade', index=True)
    category_id = fields.Many2one('loyalty.approval.category', required=True, ondelete='restrict')
    owner_id = fields.Many2one('res.users', string='Requested By', default=lambda s: s.env.user, required=True)
    state = fields.Selection(
        [
            ('new', 'New'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('refused', 'Refused'),
            ('cancel', 'Cancelled'),
        ],
        default='new', tracking=True, required=True,
    )
    current_level = fields.Integer(default=0, tracking=True)
    approver_ids = fields.One2many('loyalty.approval.request.approver', 'request_id', copy=False)
    reason = fields.Html()
    total_levels = fields.Integer(compute='_compute_total_levels')

    _code_unique = models.Constraint(
        'unique(program_id)',
        'A loyalty program can have only one approval request at a time.',
    )

    @api.depends('program_id.name')
    def _compute_name(self):
        for rec in self:
            rec.name = _("Loyalty Approval: %s", rec.program_id.display_name or '')

    @api.depends('approver_ids.sequence')
    def _compute_total_levels(self):
        for rec in self:
            rec.total_levels = len(set(rec.approver_ids.mapped('sequence'))) if rec.approver_ids else 0

    # --------------------------------------------------------------
    # Creation helper
    # --------------------------------------------------------------
    @api.model
    def _create_for_program(self, program, category):
        request = self.create({
            'program_id': program.id,
            'category_id': category.id,
            'owner_id': self.env.user.id,
            'state': 'pending',
            'current_level': 0,
            'reason': program._render_approval_summary(),
        })
        lines = []
        for cat_line in category.approver_line_ids.sorted(lambda l: (l.sequence, l.id)):
            lines.append((0, 0, {
                'sequence': cat_line.sequence,
                'level_name': cat_line.level_name,
                'required_approvals': cat_line.min_approvals or 1,
                'candidate_user_ids': [(6, 0, cat_line._resolve_pool().ids)],
                'status': 'new',
            }))
        request.approver_ids = lines
        first_level = min(request.approver_ids.mapped('sequence'))
        request.current_level = first_level
        request._activate_level(first_level)
        return request

    # --------------------------------------------------------------
    # Level activation + delegation substitution
    # --------------------------------------------------------------
    def _activate_level(self, level):
        self.ensure_one()
        today = fields.Date.today()
        lines = self.approver_ids.filtered(lambda l: l.sequence == level)
        for line in lines:
            pool = line.candidate_user_ids
            substituted = self.env['res.users']
            delegated_from = False
            for user in pool:
                if (user.loyalty_delegation_active
                        and user.loyalty_delegate_from
                        and user.loyalty_delegate_to
                        and user.loyalty_delegate_from <= today <= user.loyalty_delegate_to
                        and user.loyalty_delegate_id):
                    substituted |= user.loyalty_delegate_id
                    delegated_from = delegated_from or user.id
                else:
                    substituted |= user
            line.candidate_user_ids = [(6, 0, substituted.ids)]
            if delegated_from:
                line.delegated_from_id = delegated_from
            line.status = 'pending'
            for candidate in substituted:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=candidate.id,
                    summary=_("Loyalty approval needed (Level %s)", level),
                    note=_("Please review '%s'.", self.program_id.display_name),
                )
        self.message_post(body=_("Level %s activated.", level))

    def action_refresh_approvers(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_("Can only refresh approvers while the request is pending."))
        # Re-resolve pool from category and re-apply delegation for current level lines.
        cat_lines = self.category_id.approver_line_ids.filtered(lambda l: l.sequence == self.current_level)
        pool_users = self.env['res.users']
        for cl in cat_lines:
            pool_users |= cl._resolve_pool()
        for line in self.approver_ids.filtered(lambda l: l.sequence == self.current_level and l.status == 'pending'):
            line.candidate_user_ids = [(6, 0, pool_users.ids)]
        self._activate_level(self.current_level)

    # --------------------------------------------------------------
    # Approve / Refuse / Cancel
    # --------------------------------------------------------------
    def _current_lines(self):
        self.ensure_one()
        return self.approver_ids.filtered(lambda l: l.sequence == self.current_level)

    def _user_line(self):
        self.ensure_one()
        user = self.env.user
        return self._current_lines().filtered(
            lambda l: l.status == 'pending' and user in l.candidate_user_ids
        )[:1]

    def action_approve(self, comment=None):
        for request in self:
            if request.state != 'pending':
                raise UserError(_("Only pending requests can be approved."))
            line = request._user_line()
            if not line:
                raise UserError(_("You are not an eligible approver for the current level."))
            line.write({
                'status': 'approved',
                'decided_by_id': self.env.user.id,
                'decided_on': fields.Datetime.now(),
                'comment': comment or False,
            })
            request.message_post(body=_("Approved by %s at level %s.", self.env.user.display_name, request.current_level))
            request._maybe_advance()
        return True

    def _maybe_advance(self):
        self.ensure_one()
        current = self._current_lines()
        approved = current.filtered(lambda l: l.status == 'approved')
        required = sum(current.mapped('required_approvals')) or len(current)
        if len(approved) < required:
            return
        next_levels = [s for s in set(self.approver_ids.mapped('sequence')) if s > self.current_level]
        if next_levels:
            nxt = min(next_levels)
            self.current_level = nxt
            self._activate_level(nxt)
        else:
            self.state = 'approved'
            self.activity_feedback(['mail.mail_activity_data_todo'])
            self.program_id.sudo()._on_approval_request_approved()
            self.message_post(body=_("Request fully approved."))

    def action_refuse(self, reason=None):
        for request in self:
            if request.state != 'pending':
                raise UserError(_("Only pending requests can be refused."))
            line = request._user_line() or request._current_lines()[:1]
            if line:
                line.write({
                    'status': 'refused',
                    'decided_by_id': self.env.user.id,
                    'decided_on': fields.Datetime.now(),
                    'comment': reason or False,
                })
            request.state = 'refused'
            request.activity_feedback(['mail.mail_activity_data_todo'])
            request.program_id.sudo()._on_approval_request_refused(reason or '')
            request.message_post(body=_("Refused by %s. Reason: %s", self.env.user.display_name, reason or ''))
        return True

    def action_cancel(self):
        for request in self:
            if request.state in ('approved', 'refused'):
                raise UserError(_("Finalized requests cannot be cancelled."))
            request.state = 'cancel'
            request.activity_feedback(['mail.mail_activity_data_todo'])
            request.message_post(body=_("Cancelled by %s.", self.env.user.display_name))
        return True

    def action_open_program(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'loyalty.program',
            'res_id': self.program_id.id,
            'view_mode': 'form',
        }


class LoyaltyApprovalRequestApprover(models.Model):
    _name = 'loyalty.approval.request.approver'
    _description = 'Loyalty Approval Request Approver Line'
    _order = 'request_id, sequence, id'

    request_id = fields.Many2one('loyalty.approval.request', required=True, ondelete='cascade')
    sequence = fields.Integer(required=True)
    level_name = fields.Char()
    user_id = fields.Many2one('res.users', string='Decided By')
    candidate_user_ids = fields.Many2many('res.users', 'loyalty_approval_request_approver_user_rel', 'line_id', 'user_id', string='Eligible Users')
    required_approvals = fields.Integer(default=1, required=True)
    status = fields.Selection(
        [
            ('new', 'New'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('refused', 'Refused'),
            ('delegated', 'Delegated'),
        ],
        default='new', required=True,
    )
    decided_by_id = fields.Many2one('res.users', string='Acted By')
    decided_on = fields.Datetime()
    comment = fields.Text()
    delegated_from_id = fields.Many2one('res.users', string='Delegated From')
