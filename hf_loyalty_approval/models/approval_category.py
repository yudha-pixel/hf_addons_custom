# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class LoyaltyApprovalCategory(models.Model):
    _name = 'loyalty.approval.category'
    _description = 'Loyalty Approval Category'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()
    min_approval = fields.Integer(string='Default Min Approvals', default=1)
    approver_line_ids = fields.One2many(
        'loyalty.approval.category.approver',
        'category_id',
        string='Approval Levels',
        copy=True,
    )
    company_id = fields.Many2one('res.company')
    level_count = fields.Integer(compute='_compute_level_count')

    @api.depends('approver_line_ids.sequence')
    def _compute_level_count(self):
        for rec in self:
            rec.level_count = len(set(rec.approver_line_ids.mapped('sequence')))

    @api.constrains('approver_line_ids')
    def _check_levels(self):
        for rec in self:
            if not rec.approver_line_ids:
                raise ValidationError(_("Category '%s' must define at least one approval level.", rec.name))


class LoyaltyApprovalCategoryApprover(models.Model):
    _name = 'loyalty.approval.category.approver'
    _description = 'Loyalty Approval Category Level'
    _order = 'category_id, sequence, id'

    category_id = fields.Many2one('loyalty.approval.category', required=True, ondelete='cascade')
    sequence = fields.Integer(default=1, required=True, help="Level index; rows sharing the same sequence form one parallel level.")
    level_name = fields.Char(required=True)
    user_ids = fields.Many2many('res.users', 'loyalty_approval_category_user_rel', 'line_id', 'user_id', string='Eligible Users')
    group_id = fields.Many2one('res.groups', string='Eligible Group')
    min_approvals = fields.Integer(default=1, required=True)
    required = fields.Boolean(default=True, help="If unchecked, level is skippable.")

    @api.constrains('user_ids', 'group_id')
    def _check_pool(self):
        for rec in self:
            if not rec.user_ids and not rec.group_id:
                raise ValidationError(_("Level '%s' must have at least one user or a group.", rec.level_name or rec.sequence))

    def _resolve_pool(self):
        self.ensure_one()
        users = self.user_ids
        if self.group_id:
            users |= self.group_id.all_user_ids
        return users
