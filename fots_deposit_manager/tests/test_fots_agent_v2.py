# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestFotsAgentV2(TransactionCase):

    def setUp(self):
        super().setUp()

        self.warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not self.warehouse:
            self.warehouse = self.env['stock.warehouse'].search([], limit=1)

        self.team = self.env['fots.team'].create({
            'name': 'Lagos Street Team',
            'manager_id': self.env.user.id,
            'warehouse_id': self.warehouse.id,
        })

        self.partner = self.env['res.partner'].create({'name': 'Test Agent Partner'})

        self.agent_user = self.env['res.users'].create({
            'name': 'Test Agent User',
            'login': 'agent_user@test.com',
        })

        self.agent = self.env['fots.agent'].create({
            'name': 'Test Agent',
            'phone': '08012345678',
            'team_id': self.team.id,
            'partner_id': self.partner.id,
            'user_id': self.agent_user.id,
        })

    def test_01_agent_creation(self):
        self.assertTrue(self.agent.id)
        self.assertNotEqual(self.agent.code, 'New')
        self.assertEqual(self.agent.team_id, self.team)

    def test_04_agent_related_fields_from_team(self):
        self.assertEqual(self.agent.manager_id, self.env.user)

    def test_05_auto_create_customer_when_partner_empty(self):
        agent = self.env['fots.agent'].create({
            'name': 'Auto Customer Agent',
            'team_id': self.team.id,
        })
        self.assertTrue(agent.partner_id, 'partner_id should be auto-created when empty')
        self.assertEqual(agent.partner_id.name, 'Auto Customer Agent')
        self.assertGreaterEqual(agent.partner_id.customer_rank, 1)

    def test_06_auto_create_customer_copies_contact_address(self):
        country = self.env.ref('base.ng', raise_if_not_found=False) or self.env['res.country'].search([], limit=1)
        state = self.env['res.country.state'].search([
            ('country_id', '=', country.id),
        ], limit=1) if country else self.env['res.country.state']

        agent = self.env['fots.agent'].create({
            'name': 'Auto Copy Agent',
            'team_id': self.team.id,
            'phone': '08000000000',
            'email': 'auto.copy.agent@test.com',
            'street': '123 Agent Street',
            'street2': 'Block B',
            'city': 'Lagos',
            'zip': '100001',
            'country_id': country.id if country else False,
            'state_id': state.id if state else False,
        })

        self.assertEqual(agent.partner_id.phone, '08000000000')
        self.assertEqual(agent.partner_id.email, 'auto.copy.agent@test.com')
        self.assertEqual(agent.partner_id.street, '123 Agent Street')
        self.assertEqual(agent.partner_id.street2, 'Block B')
        self.assertEqual(agent.partner_id.city, 'Lagos')
        self.assertEqual(agent.partner_id.zip, '100001')
        if country:
            self.assertEqual(agent.partner_id.country_id, country)
        if state:
            self.assertEqual(agent.partner_id.state_id, state)

    def test_07_manual_partner_allowed_when_unused(self):
        partner = self.env['res.partner'].create({'name': 'Unique Partner'})
        agent = self.env['fots.agent'].create({
            'name': 'Unique Partner Agent',
            'team_id': self.team.id,
            'partner_id': partner.id,
        })
        self.assertEqual(agent.partner_id, partner)

    def test_08_manual_partner_conflict_with_active_agent_blocked(self):
        conflict_partner = self.env['res.partner'].create({'name': 'Conflict Partner Active'})
        self.env['fots.agent'].create({
            'name': 'Owner Agent Active',
            'team_id': self.team.id,
            'partner_id': conflict_partner.id,
        })

        with self.assertRaises(ValidationError):
            self.env['fots.agent'].create({
                'name': 'Second Agent Active Conflict',
                'team_id': self.team.id,
                'partner_id': conflict_partner.id,
            })

    def test_09_manual_partner_conflict_with_archived_agent_blocked(self):
        archived_partner = self.env['res.partner'].create({'name': 'Conflict Partner Archived'})
        owner_agent = self.env['fots.agent'].create({
            'name': 'Owner Agent Archived',
            'team_id': self.team.id,
            'partner_id': archived_partner.id,
        })
        owner_agent.active = False

        with self.assertRaises(ValidationError):
            self.env['fots.agent'].create({
                'name': 'Second Agent Archived Conflict',
                'team_id': self.team.id,
                'partner_id': archived_partner.id,
            })
