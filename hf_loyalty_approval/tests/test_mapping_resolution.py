# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import tagged
from .common import LoyaltyApprovalCase


@tagged('post_install', '-at_install', 'hf_loyalty_approval')
class TestMappingResolution(LoyaltyApprovalCase):

    def test_standard_resolves_to_default(self):
        program = self._make_program(discount=5.0)
        mapping = self.Mapping._resolve_for_program(program)
        self.assertEqual(mapping.category_id, self.cat_standard)

    def test_high_resolves(self):
        program = self._make_program(discount=20.0)
        mapping = self.Mapping._resolve_for_program(program)
        self.assertEqual(mapping.category_id, self.cat_high)

    def test_critical_resolves(self):
        program = self._make_program(discount=40.0)
        mapping = self.Mapping._resolve_for_program(program)
        self.assertEqual(mapping.category_id, self.cat_critical)

    def test_missing_default_raises(self):
        program = self._make_program(discount=5.0)
        self.env.ref('hf_loyalty_approval.mapping_default').active = False
        with self.assertRaises(UserError):
            self.Mapping._resolve_for_program(program)
