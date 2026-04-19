# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo.tests.common import tagged
from .common import LoyaltyApprovalCase


@tagged('post_install', '-at_install', 'hf_loyalty_approval')
class TestDelegation(LoyaltyApprovalCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_a = cls.env['res.users'].create({
            'name': 'Alice', 'login': 'alice_test', 'email': 'a@test.local',
        })
        cls.user_b = cls.env['res.users'].create({
            'name': 'Bob', 'login': 'bob_test', 'email': 'b@test.local',
        })
        # Replace seeded level 1 of Standard category with an explicit user pool.
        cls.cat_standard.approver_line_ids.unlink()
        cls.env['loyalty.approval.category.approver'].create({
            'category_id': cls.cat_standard.id,
            'sequence': 1,
            'level_name': 'Primary',
            'user_ids': [(6, 0, [cls.user_a.id])],
            'min_approvals': 1,
        })

    def test_active_delegation_substitutes(self):
        today = date.today()
        self.user_a.write({
            'loyalty_delegate_id': self.user_b.id,
            'loyalty_delegate_from': today - timedelta(days=1),
            'loyalty_delegate_to': today + timedelta(days=1),
        })
        program = self._make_program(discount=5.0)
        program.action_request_approval()
        line = program.approval_request_id.approver_ids[:1]
        self.assertIn(self.user_b, line.candidate_user_ids)
        self.assertNotIn(self.user_a, line.candidate_user_ids)
        self.assertEqual(line.delegated_from_id, self.user_a)

    def test_expired_delegation_no_substitution(self):
        today = date.today()
        self.user_a.write({
            'loyalty_delegate_id': self.user_b.id,
            'loyalty_delegate_from': today - timedelta(days=10),
            'loyalty_delegate_to': today - timedelta(days=5),
        })
        program = self._make_program(discount=5.0)
        program.action_request_approval()
        line = program.approval_request_id.approver_ids[:1]
        self.assertIn(self.user_a, line.candidate_user_ids)
        self.assertNotIn(self.user_b, line.candidate_user_ids)
        self.assertFalse(line.delegated_from_id)
