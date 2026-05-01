# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo.tests import TransactionCase, tagged
from odoo.exceptions import ValidationError


@tagged('post_install', '-at_install', 'fots')
class TestFotsSaleOrder(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({'name': 'Test Agent Customer'})

        cls.warehouse = cls.env['stock.warehouse'].search([], limit=1)
        cls.team = cls.env['fots.team'].create({
            'name': 'Test Team',
            'manager_id': cls.env.user.id,
            'warehouse_id': cls.warehouse.id,
        })

        cls.agent = cls.env['fots.agent'].create({
            'name': 'Test Agent',
            'team_id': cls.team.id,
            'partner_id': cls.partner.id,
        })

        cls.product = cls.env['product.product'].search([('sale_ok', '=', True)], limit=1)
        if not cls.product:
            cls.product = cls.env['product.product'].create({
                'name': 'G-Flakes Test',
                'type': 'consu',
                'sale_ok': True,
                'lst_price': 100.0,
            })

    def test_fots_agent_id_auto_sets_partner(self):
        """Setting fots_agent_id should auto-set partner_id via onchange."""
        order = self.env['sale.order'].new({'fots_agent_id': self.agent.id})
        order._onchange_fots_agent_id()
        self.assertEqual(order.partner_id, self.agent.partner_id,
                         'partner_id should be auto-set from agent.partner_id')

    def test_sale_order_agent_link(self):
        """sale.order with fots_agent_id stores agent and team correctly."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'fots_agent_id': self.agent.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5,
                'price_unit': 100.0,
            })],
        })
        self.assertEqual(order.fots_agent_id, self.agent)
        self.assertEqual(order.fots_team_id, self.team)

    def test_agent_partner_mismatch_raises(self):
        """Creating a sale.order with mismatched partner and agent should raise."""
        other_partner = self.env['res.partner'].create({'name': 'Other Partner'})
        with self.assertRaises(ValidationError):
            self.env['sale.order'].create({
                'partner_id': other_partner.id,
                'fots_agent_id': self.agent.id,
                'order_line': [(0, 0, {
                    'product_id': self.product.id,
                    'product_uom_qty': 1,
                    'price_unit': 100.0,
                })],
            })

    def test_sale_order_count_on_agent(self):
        """Agent sale_order_count should reflect linked sale orders."""
        before = self.agent.sale_order_count
        self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'fots_agent_id': self.agent.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            })],
        })
        self.agent.invalidate_recordset(['sale_order_count'])
        self.assertEqual(self.agent.sale_order_count, before + 1)

    def test_sale_order_without_agent_allowed(self):
        """A sale.order without fots_agent_id should be allowed (agent is optional)."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        self.assertFalse(order.fots_agent_id)

    def test_buy_and_go_validates_delivery_with_signature_bypass_context(self):
        """Buy & Go should pass the HF bypass context into delivery validation."""
        dozen_uom = self.env.ref('uom.product_uom_dozen', raise_if_not_found=False)
        if not dozen_uom:
            self.skipTest('Dozen UoM is not installed.')

        product = self.env['product.product'].create({
            'name': 'FOTS Dozen Test Product',
            'type': 'consu',
            'sale_ok': True,
            'uom_id': dozen_uom.id,
            'uom_po_id': dozen_uom.id,
            'lst_price': 100.0,
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'fots_agent_id': self.agent.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'product_uom': dozen_uom.id,
                'price_unit': 100.0,
            })],
        })
        captured = {}

        class FakeInvoices:
            ids = [1]

            def __bool__(self):
                return True

            def action_post(self):
                return True

        class FakePaymentRegister:

            def action_create_payments(self):
                return True

        def fake_button_validate(pickings):
            captured['hf_bypass_signature'] = pickings.env.context.get('hf_bypass_signature')
            vals = {'state': 'done'}
            if captured['hf_bypass_signature'] and 'hf_signature_bypassed' in pickings._fields:
                vals['hf_signature_bypassed'] = True
            pickings.write(vals)
            return True

        def fake_create(payment_register_model, vals):
            return FakePaymentRegister()

        with patch.object(type(self.env['stock.picking']), 'button_validate', new=fake_button_validate), \
             patch.object(type(self.env['sale.order']), '_create_invoices', return_value=FakeInvoices()), \
             patch.object(type(self.env['account.payment.register']), 'create', new=fake_create):
            order.action_fots_buy_and_go()

        self.assertEqual(order.state, 'sale')
        self.assertTrue(order.picking_ids)
        self.assertEqual(order.picking_ids.filtered(lambda p: p.state == 'done'), order.picking_ids)
        self.assertTrue(captured.get('hf_bypass_signature'))
        if 'hf_progress_state' in order.picking_ids._fields:
            self.assertEqual(order.picking_ids[:1].hf_progress_state, 'delivered')
