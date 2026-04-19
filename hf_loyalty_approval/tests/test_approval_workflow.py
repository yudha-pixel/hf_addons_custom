# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from .common import LoyaltyApprovalCase


@tagged('post_install', '-at_install', 'hf_loyalty_approval')
class TestApprovalWorkflow(LoyaltyApprovalCase):

    def test_create_is_draft_inactive(self):
        program = self._make_program()
        self.assertEqual(program.approval_state, 'draft')
        self.assertFalse(program.active)

    def test_cannot_activate_while_draft(self):
        program = self._make_program()
        with self.assertRaises(UserError):
            program.write({'active': True})

    def test_single_level_full_flow(self):
        program = self._make_program(discount=5.0)
        program.action_request_approval()
        self.assertEqual(program.approval_state, 'waiting')
        self.assertTrue(program.approval_request_id)
        program.approval_request_id.action_approve()
        self.assertEqual(program.approval_state, 'approved')
        self.assertTrue(program.active)

    def test_two_level_sequential(self):
        program = self._make_program(discount=20.0)
        program.action_request_approval()
        req = program.approval_request_id
        self.assertEqual(req.total_levels, 2)
        req.action_approve()
        self.assertEqual(req.state, 'pending')
        self.assertEqual(req.current_level, 2)
        req.action_approve()
        self.assertEqual(req.state, 'approved')
        self.assertTrue(program.active)

    def test_refuse_at_level_one(self):
        program = self._make_program(discount=20.0)
        program.action_request_approval()
        program.approval_request_id.action_refuse('No budget.')
        self.assertEqual(program.approval_state, 'rejected')
        self.assertFalse(program.active)
        self.assertIn('budget', program.rejection_reason or '')

    def test_reset_reruns_mapping(self):
        program = self._make_program(discount=10.0)
        program.action_request_approval()
        self.assertEqual(program.approval_request_id.category_id, self.cat_standard)
        program.approval_request_id.action_refuse('Retry')
        program.action_reset_to_draft()
        self.assertEqual(program.approval_state, 'draft')
        program.with_context(bypass_approval_lock=True).reward_ids.write({'discount': 40.0})
        program.invalidate_recordset(['approval_tier'])
        program.action_request_approval()
        self.assertEqual(program.approval_request_id.category_id, self.cat_critical)
