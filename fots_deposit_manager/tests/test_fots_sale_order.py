# -*- coding: utf-8 -*-

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
