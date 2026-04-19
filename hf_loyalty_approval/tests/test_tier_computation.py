# -*- coding: utf-8 -*-
from odoo.tests.common import tagged
from .common import LoyaltyApprovalCase


@tagged('post_install', '-at_install', 'hf_loyalty_approval')
class TestTierComputation(LoyaltyApprovalCase):

    def test_percent_standard(self):
        program = self._make_program(discount=10.0, discount_mode='percent')
        self.assertEqual(program.approval_tier, 'standard')

    def test_percent_high(self):
        program = self._make_program(discount=20.0, discount_mode='percent')
        self.assertEqual(program.approval_tier, 'high')

    def test_percent_critical(self):
        program = self._make_program(discount=40.0, discount_mode='percent')
        self.assertEqual(program.approval_tier, 'critical')

    def test_fixed_standard(self):
        program = self._make_program(discount=200.0, discount_mode='per_order')
        self.assertEqual(program.approval_tier, 'standard')

    def test_fixed_high(self):
        program = self._make_program(discount=500.0, discount_mode='per_order')
        self.assertEqual(program.approval_tier, 'high')

    def test_fixed_critical(self):
        program = self._make_program(discount=1500.0, discount_mode='per_order')
        self.assertEqual(program.approval_tier, 'critical')
