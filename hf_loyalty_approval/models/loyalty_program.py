# -*- coding: utf-8 -*-
from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

LOCKED_FIELDS = {
    'program_type', 'rule_ids', 'reward_ids', 'date_from', 'date_to',
    'trigger', 'applies_on', 'pricelist_ids',
}

TIER_HIGH_PCT = 'hf_loyalty_approval.tier_high_pct'
TIER_CRITICAL_PCT = 'hf_loyalty_approval.tier_critical_pct'
TIER_HIGH_FIXED = 'hf_loyalty_approval.tier_high_fixed'
TIER_CRITICAL_FIXED = 'hf_loyalty_approval.tier_critical_fixed'

TIER_DEFAULTS = {
    TIER_HIGH_PCT: '15',
    TIER_CRITICAL_PCT: '30',
    TIER_HIGH_FIXED: '250',
    TIER_CRITICAL_FIXED: '1000',
}


class LoyaltyProgram(models.Model):
    _inherit = ['loyalty.program', 'mail.thread', 'mail.activity.mixin']
    _name = 'loyalty.program'

    approval_request_id = fields.Many2one(
        'loyalty.approval.request', string='Approval Request',
        readonly=True, copy=False, ondelete='set null',
    )
    approval_state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('waiting', 'Waiting Approval'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Approval Status',
        compute='_compute_approval_state',
        store=True, tracking=True, copy=False,
    )
    approval_tier = fields.Selection(
        [('standard', 'Standard'), ('high', 'High'), ('critical', 'Critical')],
        compute='_compute_approval_tier', store=True,
    )
    approval_level_summary = fields.Char(compute='_compute_approval_level_summary')
    can_current_user_act = fields.Boolean(compute='_compute_can_current_user_act')

    # Legacy display fields (kept so existing views/data keep working).
    requested_by_id = fields.Many2one('res.users', string='Requested By', related='approval_request_id.owner_id', store=True, readonly=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', compute='_compute_decided_by', store=True, readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason', compute='_compute_rejection_reason', store=True, readonly=True)
    request_date = fields.Datetime(string='Request Date', related='approval_request_id.create_date', store=True, readonly=True)
    approval_date = fields.Datetime(string='Approval Date', compute='_compute_decided_by', store=True, readonly=True)

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('approval_request_id.state')
    def _compute_approval_state(self):
        mapping = {
            False: 'draft',
            'new': 'draft',
            'pending': 'waiting',
            'approved': 'approved',
            'refused': 'rejected',
            'cancel': 'draft',
        }
        for program in self:
            program.approval_state = mapping.get(program.approval_request_id.state, 'draft')

    @api.depends('program_type', 'reward_ids.discount', 'reward_ids.discount_mode')
    def _compute_approval_tier(self):
        ICP = self.env['ir.config_parameter'].sudo()

        def _f(key):
            return float(ICP.get_param(key, TIER_DEFAULTS[key]) or 0.0)

        high_pct = _f(TIER_HIGH_PCT)
        crit_pct = _f(TIER_CRITICAL_PCT)
        high_fixed = _f(TIER_HIGH_FIXED)
        crit_fixed = _f(TIER_CRITICAL_FIXED)
        for program in self:
            max_pct = 0.0
            max_fixed = 0.0
            for r in program.reward_ids:
                if r.discount_mode == 'percent':
                    max_pct = max(max_pct, r.discount or 0.0)
                else:
                    max_fixed = max(max_fixed, r.discount or 0.0)
            if max_pct > crit_pct or max_fixed > crit_fixed:
                program.approval_tier = 'critical'
            elif max_pct > high_pct or max_fixed > high_fixed:
                program.approval_tier = 'high'
            else:
                program.approval_tier = 'standard'

    @api.depends('approval_request_id.current_level', 'approval_request_id.total_levels', 'approval_request_id.state', 'approval_request_id.approver_ids.level_name')
    def _compute_approval_level_summary(self):
        for program in self:
            req = program.approval_request_id
            if not req or req.state != 'pending' or not req.total_levels:
                program.approval_level_summary = ''
                continue
            levels = sorted(set(req.approver_ids.mapped('sequence')))
            try:
                idx = levels.index(req.current_level) + 1
            except ValueError:
                idx = 0
            current = req.approver_ids.filtered(lambda l: l.sequence == req.current_level)[:1]
            program.approval_level_summary = _("Level %s/%s — %s", idx, req.total_levels, current.level_name or '')

    @api.depends_context('uid')
    @api.depends('approval_request_id.state', 'approval_request_id.current_level', 'approval_request_id.approver_ids.candidate_user_ids', 'approval_request_id.approver_ids.status')
    def _compute_can_current_user_act(self):
        uid = self.env.user.id
        for program in self:
            req = program.approval_request_id
            if not req or req.state != 'pending':
                program.can_current_user_act = False
                continue
            lines = req.approver_ids.filtered(
                lambda l: l.sequence == req.current_level and l.status == 'pending' and uid in l.candidate_user_ids.ids
            )
            program.can_current_user_act = bool(lines)

    @api.depends('approval_request_id.approver_ids.decided_by_id', 'approval_request_id.approver_ids.decided_on', 'approval_request_id.state')
    def _compute_decided_by(self):
        for program in self:
            req = program.approval_request_id
            if req and req.state == 'approved':
                last = req.approver_ids.filtered('decided_on').sorted('decided_on')[-1:]
                program.approved_by_id = last.decided_by_id
                program.approval_date = last.decided_on
            else:
                program.approved_by_id = False
                program.approval_date = False

    @api.depends('approval_request_id.approver_ids.status', 'approval_request_id.approver_ids.comment')
    def _compute_rejection_reason(self):
        for program in self:
            req = program.approval_request_id
            if req and req.state == 'refused':
                refused = req.approver_ids.filtered(lambda l: l.status == 'refused')[:1]
                program.rejection_reason = refused.comment or ''
            else:
                program.rejection_reason = False

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('active', False)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('active') and not self.env.context.get('bypass_approval_lock'):
            for program in self:
                if program.approval_state != 'approved':
                    raise UserError(_(
                        "Program '%s' cannot be activated until it has been approved.",
                        program.display_name,
                    ))
        locked = LOCKED_FIELDS.intersection(vals.keys())
        if locked and not self.env.context.get('bypass_approval_lock'):
            for program in self:
                if program.approval_state in ('waiting', 'approved'):
                    raise UserError(_(
                        "Program '%s' is %s and can no longer be edited. Reset it to draft first.",
                        program.display_name, program.approval_state,
                    ))
        return super().write(vals)

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_request_approval(self):
        for program in self:
            if program.approval_state != 'draft':
                raise UserError(_("Only draft programs can be submitted for approval."))
            if program.approval_request_id and program.approval_request_id.state not in ('cancel', 'refused'):
                raise UserError(_("Program already has an active approval request."))
            mapping = self.env['loyalty.approval.category.mapping']._resolve_for_program(program)
            request = self.env['loyalty.approval.request']._create_for_program(program, mapping.category_id)
            program.approval_request_id = request
            program.message_post(body=_(
                "Submitted for approval (category: %s, tier: %s).",
                mapping.category_id.name, program.approval_tier or '',
            ))
            template = self.env.ref(
                'hf_loyalty_approval.mail_template_loyalty_approval_request',
                raise_if_not_found=False,
            )
            if template:
                template.send_mail(program.id, force_send=False)
        return True

    def action_approve(self):
        for program in self:
            if not program.approval_request_id:
                raise UserError(_("No approval request to act on."))
            program.approval_request_id.action_approve()
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        if self.approval_state != 'waiting':
            raise UserError(_("Only programs awaiting approval can be rejected."))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Reject Loyalty Program"),
            'res_model': 'loyalty.rejection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_program_id': self.id},
        }

    def action_reset_to_draft(self):
        for program in self:
            if program.approval_state not in ('rejected', 'approved'):
                raise UserError(_("Only rejected or approved programs can be reset to draft."))
            if program.approval_request_id and program.approval_request_id.state == 'pending':
                program.approval_request_id.action_cancel()
            program.with_context(bypass_approval_lock=True).write({
                'approval_request_id': False,
                'active': False,
            })
            program.message_post(body=_("Program reset to draft by %s.", self.env.user.display_name))
        return True

    def action_open_approval_request(self):
        self.ensure_one()
        if not self.approval_request_id:
            raise UserError(_("No approval request linked."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'loyalty.approval.request',
            'res_id': self.approval_request_id.id,
            'view_mode': 'form',
        }

    # ------------------------------------------------------------------
    # Callbacks from loyalty.approval.request
    # ------------------------------------------------------------------
    def _on_approval_request_approved(self):
        for program in self:
            program.with_context(bypass_approval_lock=True).write({'active': True})
            program.message_post(body=_("Program activated after full approval."))

    def _on_approval_request_refused(self, reason):
        for program in self:
            program.with_context(bypass_approval_lock=True).write({'active': False})
            program.message_post(body=_("Program rejected. Reason: %s", reason or ''))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _render_approval_summary(self):
        self.ensure_one()
        rewards = ', '.join(
            _("%s%s") % (r.discount, '%' if r.discount_mode == 'percent' else '')
            for r in self.reward_ids
        ) or _("(no rewards defined)")
        return Markup(
            "<p><strong>%s</strong> — %s</p>"
            "<ul>"
            "<li>Type: %s</li>"
            "<li>Company: %s</li>"
            "<li>Validity: %s → %s</li>"
            "<li>Rewards: %s</li>"
            "</ul>"
        ) % (
            self.display_name, self.approval_tier or '',
            self.program_type,
            (self.company_id.name if self.company_id else ''),
            (self.date_from or ''), (self.date_to or ''),
            rewards,
        )
