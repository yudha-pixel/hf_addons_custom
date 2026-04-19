# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class LoyaltyRejectionWizard(models.TransientModel):
    _name = 'loyalty.rejection.wizard'
    _description = 'Loyalty Program Rejection Wizard'

    program_id = fields.Many2one('loyalty.program', required=True, ondelete='cascade')
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            raise UserError(_("A rejection reason is required."))
        request = self.program_id.approval_request_id
        if not request:
            raise UserError(_("No approval request is linked to this program."))
        request.action_refuse(self.reason.strip())
        return {'type': 'ir.actions.act_window_close'}
