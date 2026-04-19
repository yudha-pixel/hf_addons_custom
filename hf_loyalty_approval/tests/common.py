# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class LoyaltyApprovalCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Program = cls.env['loyalty.program']
        cls.Category = cls.env['loyalty.approval.category']
        cls.Mapping = cls.env['loyalty.approval.category.mapping']
        cls.cat_standard = cls.env.ref('hf_loyalty_approval.category_loyalty_standard')
        cls.cat_high = cls.env.ref('hf_loyalty_approval.category_loyalty_high')
        cls.cat_critical = cls.env.ref('hf_loyalty_approval.category_loyalty_critical')

    def _make_program(self, *, discount=10.0, discount_mode='percent', program_type='promotion'):
        program = self.Program.create({
            'name': f'Test {discount}{discount_mode}',
            'program_type': program_type,
        })
        # Replace default reward with a controlled one.
        if program.reward_ids:
            program.reward_ids.sudo().write({
                'discount': discount,
                'discount_mode': discount_mode,
            })
        else:
            self.env['loyalty.reward'].create({
                'program_id': program.id,
                'discount': discount,
                'discount_mode': discount_mode,
            })
        program.invalidate_recordset(['approval_tier'])
        return program
