# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestFotsTeam(TransactionCase):

    def setUp(self):
        super().setUp()
        self.warehouse = self.env['stock.warehouse'].search(
            [('company_id', '=', self.env.company.id)], limit=1
        )
        if not self.warehouse:
            self.warehouse = self.env['stock.warehouse'].search([], limit=1)

    def test_01_team_creation(self):
        team = self.env['fots.team'].create({
            'name': 'Test Lagos Team',
            'manager_id': self.env.user.id,
            'warehouse_id': self.warehouse.id,
        })
        self.assertTrue(team.id)
        self.assertEqual(team.name, 'Test Lagos Team')
        self.assertEqual(team.warehouse_id, self.warehouse)
        self.assertEqual(team.manager_id, self.env.user)

    def test_02_active_default_is_true(self):
        team = self.env['fots.team'].create({
            'name': 'Active Default Team',
            'manager_id': self.env.user.id,
            'warehouse_id': self.warehouse.id,
        })
        self.assertTrue(team.active)

    def test_03_agents_location_hierarchy_created(self):
        """_ensure_agents_location() must create FOTS > Agents under the warehouse."""
        team = self.env['fots.team'].create({
            'name': 'Hierarchy Team',
            'manager_id': self.env.user.id,
            'warehouse_id': self.warehouse.id,
        })

        fots_location = self.env['stock.location'].search([
            ('name', '=', 'FOTS'),
            ('location_id', 'child_of', self.warehouse.view_location_id.id),
        ], limit=1)
        self.assertTrue(fots_location, "FOTS location should be created under the warehouse")

        agents_location = self.env['stock.location'].search([
            ('name', '=', 'Agents'),
            ('location_id', '=', fots_location.id),
        ], limit=1)
        self.assertTrue(agents_location, "Agents location should be created under FOTS")

    def test_04_second_team_reuses_existing_locations(self):
        """Creating a second team on the same warehouse must not duplicate locations."""
        self.env['fots.team'].create({
            'name': 'Team A',
            'manager_id': self.env.user.id,
            'warehouse_id': self.warehouse.id,
        })
        self.env['fots.team'].create({
            'name': 'Team B',
            'manager_id': self.env.user.id,
            'warehouse_id': self.warehouse.id,
        })

        fots_count = self.env['stock.location'].search_count([
            ('name', '=', 'FOTS'),
            ('location_id', 'child_of', self.warehouse.view_location_id.id),
        ])
        self.assertEqual(fots_count, 1, "FOTS location should not be duplicated for same warehouse")
