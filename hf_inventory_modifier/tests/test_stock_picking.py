# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'hf_inventory_modifier')
class TestHfInventoryModifierStockPicking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.vendor_location = cls.env.ref('stock.stock_location_suppliers')
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.transit_location = cls.env.company.internal_transit_location_id

        cls.warehouse_a = cls._get_or_create_warehouse('HFA', 'HF Test Warehouse A')
        cls.warehouse_b = cls._get_or_create_warehouse('HFB', 'HF Test Warehouse B')
        cls.product = cls.env['product.product'].create({
            'name': 'HF Workflow Test Product',
            'is_storable': True,
        })

    @classmethod
    def _get_or_create_warehouse(cls, code, name):
        warehouse = cls.env['stock.warehouse'].search([
            ('code', '=', code),
            ('company_id', '=', cls.env.company.id),
        ], limit=1)
        if warehouse:
            return warehouse
        return cls.env['stock.warehouse'].create({
            'name': name,
            'code': code,
            'company_id': cls.env.company.id,
        })

    def _create_picking(self, picking_type, source_location, dest_location, quantity=0.0, state='draft'):
        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
        })
        if quantity:
            self.env['stock.move'].create({
                'description_picking': self.product.display_name,
                'product_id': self.product.id,
                'product_uom_qty': quantity,
                'product_uom': self.product.uom_id.id,
                'picking_id': picking.id,
                'picking_type_id': picking_type.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'company_id': self.env.company.id,
            })
        if state != 'draft':
            picking.write({'state': state})
        return picking

    def _set_stock(self, location, quantity):
        self.env['stock.quant']._update_available_quantity(self.product, location, quantity)

    def _available_qty(self, location):
        return sum(self.env['stock.quant']._gather(self.product, location).mapped('quantity'))

    def test_receipt_workflow_marks_delivered_on_final_validation(self):
        picking = self._create_picking(
            self.warehouse_a.in_type_id,
            self.vendor_location,
            self.warehouse_a.lot_stock_id,
            quantity=5.0,
        )

        self.assertEqual(picking.hf_progress_state, 'placed')
        picking.action_assign()
        self.assertEqual(picking.hf_progress_state, 'processed')

        picking.action_hf_set_receipt_dispatched()
        self.assertEqual(picking.hf_progress_state, 'dispatched')
        self.assertFalse(picking.hf_delivered_at)
        self.assertEqual(self._available_qty(self.warehouse_a.lot_stock_id), 0.0)

        picking.action_hf_process_receipt()

        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.hf_progress_state, 'delivered')
        self.assertTrue(picking.hf_delivered_at)
        self.assertEqual(self._available_qty(self.warehouse_a.lot_stock_id), 5.0)

    def test_internal_transfer_workflow_uses_transit_receiving_picking(self):
        self._set_stock(self.warehouse_a.lot_stock_id, 6.0)
        picking = self._create_picking(
            self.warehouse_a.int_type_id,
            self.warehouse_a.lot_stock_id,
            self.warehouse_b.lot_stock_id,
            quantity=4.0,
        )
        picking.action_assign()

        picking.action_hf_ship_goods()

        receipt = picking.hf_transit_receipt_picking_id
        self.assertTrue(receipt)
        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.hf_progress_state, 'dispatched')
        self.assertEqual(picking.hf_final_location_dest_id, self.warehouse_b.lot_stock_id)
        self.assertEqual(picking.location_dest_id, self.transit_location)
        self.assertEqual(receipt.hf_transit_source_picking_id, picking)
        self.assertEqual(receipt.location_id, self.transit_location)
        self.assertEqual(receipt.location_dest_id, self.warehouse_b.lot_stock_id)
        self.assertEqual(receipt.hf_progress_state, 'dispatched')
        self.assertEqual(self._available_qty(self.warehouse_a.lot_stock_id), 2.0)
        self.assertEqual(self._available_qty(self.transit_location), 4.0)
        self.assertEqual(self._available_qty(self.warehouse_b.lot_stock_id), 0.0)

        picking.action_hf_confirm_received()

        self.assertEqual(receipt.state, 'done')
        self.assertEqual(receipt.hf_progress_state, 'delivered')
        self.assertEqual(self._available_qty(self.transit_location), 0.0)
        self.assertEqual(self._available_qty(self.warehouse_b.lot_stock_id), 4.0)

    def test_delivery_workflow_requires_pod_before_delivered(self):
        self._set_stock(self.warehouse_a.lot_stock_id, 5.0)
        picking = self._create_picking(
            self.warehouse_a.out_type_id,
            self.warehouse_a.lot_stock_id,
            self.customer_location,
            quantity=3.0,
        )
        picking.action_assign()

        picking.action_hf_out_for_delivery()

        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.hf_progress_state, 'dispatched')
        self.assertEqual(self._available_qty(self.warehouse_a.lot_stock_id), 2.0)
        with self.assertRaises(UserError):
            picking.action_hf_mark_delivered()

        picking.with_context(hf_skip_picking_type_autofix=True).write({'hf_signature_bypassed': True})
        picking.action_hf_mark_delivered()

        self.assertEqual(picking.hf_progress_state, 'delivered')
        self.assertTrue(picking.hf_delivered_at)

    def test_native_validate_fallback_marks_receipt_delivered(self):
        picking = self._create_picking(
            self.warehouse_a.in_type_id,
            self.vendor_location,
            self.warehouse_a.lot_stock_id,
            quantity=2.0,
        )
        picking.action_assign()
        picking.move_ids.quantity = 2.0
        picking.move_ids.picked = True

        picking.button_validate()

        self.assertEqual(picking.state, 'done')
        self.assertEqual(picking.hf_progress_state, 'delivered')
        self.assertTrue(picking.hf_delivered_at)

    def test_native_validate_with_bypass_marks_delivery_delivered(self):
        self._set_stock(self.warehouse_a.lot_stock_id, 2.0)
        picking = self._create_picking(
            self.warehouse_a.out_type_id,
            self.warehouse_a.lot_stock_id,
            self.customer_location,
            quantity=2.0,
        )
        picking.action_assign()
        picking.move_ids.quantity = 2.0
        picking.move_ids.picked = True

        picking.with_context(hf_bypass_signature=True).button_validate()

        self.assertEqual(picking.state, 'done')
        self.assertTrue(picking.hf_signature_bypassed)
        self.assertEqual(picking.hf_progress_state, 'delivered')

    def test_autofix_receipt_uses_destination_warehouse_receipt_type(self):
        picking = self._create_picking(
            self.warehouse_a.in_type_id,
            self.vendor_location,
            self.warehouse_a.lot_stock_id,
        )

        picking.write({
            'picking_type_id': self.warehouse_b.in_type_id.id,
            'location_dest_id': self.warehouse_b.lot_stock_id.id,
        })

        self.assertEqual(picking.picking_type_id, self.warehouse_b.in_type_id)

    def test_autofix_delivery_uses_source_warehouse_delivery_type(self):
        picking = self._create_picking(
            self.warehouse_a.out_type_id,
            self.warehouse_a.lot_stock_id,
            self.customer_location,
        )

        picking.write({
            'picking_type_id': self.warehouse_b.out_type_id.id,
            'location_id': self.warehouse_b.lot_stock_id.id,
        })

        self.assertEqual(picking.picking_type_id, self.warehouse_b.out_type_id)

    def test_autofix_internal_uses_source_warehouse_internal_type(self):
        picking = self._create_picking(
            self.warehouse_a.int_type_id,
            self.warehouse_a.lot_stock_id,
            self.warehouse_b.lot_stock_id,
        )

        picking.write({
            'picking_type_id': self.warehouse_b.int_type_id.id,
            'location_id': self.warehouse_b.lot_stock_id.id,
            'location_dest_id': self.warehouse_a.lot_stock_id.id,
        })

        self.assertEqual(picking.picking_type_id, self.warehouse_b.int_type_id)

    def test_autofix_does_not_change_non_draft_picking(self):
        picking = self._create_picking(
            self.warehouse_a.out_type_id,
            self.warehouse_a.lot_stock_id,
            self.customer_location,
            state='confirmed',
        )

        picking.write({
            'picking_type_id': self.warehouse_a.out_type_id.id,
            'location_id': self.warehouse_b.lot_stock_id.id,
        })

        self.assertEqual(picking.picking_type_id, self.warehouse_a.out_type_id)
