# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    hf_progress_state = fields.Selection(
        selection=[
            ('placed', 'Placed'),
            ('processed', 'Processed'),
            ('dispatched', 'Dispatched'),
            ('delivered', 'Delivered'),
        ],
        string='HF Progress State',
        default='placed',
        copy=False,
        index=True,
        readonly=True,
        tracking=True,
    )
    hf_placed_at = fields.Datetime(
        string='Placed At',
        readonly=True,
        copy=False,
    )
    hf_processed_at = fields.Datetime(
        string='Processed At',
        readonly=True,
        copy=False,
    )
    hf_dispatched_at = fields.Datetime(
        string='Dispatched At',
        readonly=True,
        copy=False,
    )
    hf_delivered_at = fields.Datetime(
        string='Delivered At',
        readonly=True,
        copy=False,
    )
    hf_signature_bypassed = fields.Boolean(
        string='HF Signature Bypassed',
        readonly=True,
        copy=False,
        help='Technical flag set by trusted instant-delivery flows such as FOTS Buy & Go.',
    )
    hf_transit_source_picking_id = fields.Many2one(
        'stock.picking',
        string='HF Transit Source Transfer',
        readonly=True,
        copy=False,
        index=True,
    )
    hf_transit_receipt_picking_id = fields.Many2one(
        'stock.picking',
        string='HF Transit Receiving Transfer',
        readonly=True,
        copy=False,
        index=True,
    )
    hf_final_location_dest_id = fields.Many2one(
        'stock.location',
        string='HF Final Destination',
        readonly=True,
        copy=False,
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _hf_get_warehouse_from_location(self, location):
        warehouse = location.warehouse_id
        return warehouse if warehouse else self.env['stock.warehouse']

    def _hf_get_picking_type_for_locations(self, picking_type_code, source_location, dest_location):
        if picking_type_code == 'incoming':
            warehouse = self._hf_get_warehouse_from_location(dest_location)
            return warehouse.in_type_id if warehouse else self.env['stock.picking.type']
        if picking_type_code == 'outgoing':
            warehouse = self._hf_get_warehouse_from_location(source_location)
            return warehouse.out_type_id if warehouse else self.env['stock.picking.type']
        if picking_type_code == 'internal':
            warehouse = self._hf_get_warehouse_from_location(source_location)
            return warehouse.int_type_id if warehouse else self.env['stock.picking.type']
        return self.env['stock.picking.type']

    def _hf_get_internal_receipt_picking_type(self, final_location):
        warehouse = self._hf_get_warehouse_from_location(final_location)
        if warehouse:
            return warehouse.int_type_id
        return self.picking_type_id

    def _hf_stage_timestamp_field(self, progress_state):
        return {
            'placed': 'hf_placed_at',
            'processed': 'hf_processed_at',
            'dispatched': 'hf_dispatched_at',
            'delivered': 'hf_delivered_at',
        }[progress_state]

    def _hf_has_proof_of_delivery(self):
        self.ensure_one()
        return (
            bool(getattr(self, 'is_signed', False))
            or bool(getattr(self, 'signature', False))
            or self.hf_signature_bypassed
        )

    def _hf_set_progress_state(self, progress_state):
        now = fields.Datetime.now()
        timestamp_field = self._hf_stage_timestamp_field(progress_state)
        stage_order = ['placed', 'processed', 'dispatched', 'delivered']
        required_stages = stage_order[:stage_order.index(progress_state) + 1]
        for picking in self:
            vals = {'hf_progress_state': progress_state}
            for stage in required_stages:
                previous_timestamp_field = picking._hf_stage_timestamp_field(stage)
                if not picking[previous_timestamp_field]:
                    vals[previous_timestamp_field] = now
            if not picking[timestamp_field]:
                vals[timestamp_field] = now
            picking.with_context(hf_skip_picking_type_autofix=True).write(vals)

    def _hf_mark_done_progress_from_validate(self):
        for picking in self.filtered(lambda rec: rec.state == 'done'):
            if picking.env.context.get('hf_internal_dispatch'):
                picking._hf_set_progress_state('dispatched')
            elif picking.picking_type_code in ('incoming', 'internal'):
                picking._hf_set_progress_state('delivered')
            elif picking._hf_has_proof_of_delivery():
                picking._hf_set_progress_state('delivered')
            else:
                picking._hf_set_progress_state('dispatched')

    def _hf_prepare_validate_quantities(self):
        for picking in self:
            for move in picking.move_ids.filtered(lambda rec: rec.state not in ('done', 'cancel')):
                if move.product_uom.is_zero(move.quantity):
                    move.quantity = move.product_uom_qty
                move.picked = True

    def _hf_create_transit_receipt_picking(self, final_location):
        self.ensure_one()
        transit_location = self.company_id.internal_transit_location_id
        receiving_type = self._hf_get_internal_receipt_picking_type(final_location)
        if not receiving_type:
            raise UserError(_('No internal operation type is configured for the receiving warehouse.'))

        receipt = self.create({
            'picking_type_id': receiving_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.origin or self.name,
            'location_id': transit_location.id,
            'location_dest_id': final_location.id,
            'scheduled_date': self.scheduled_date,
            'company_id': self.company_id.id,
            'hf_progress_state': 'dispatched',
            'hf_placed_at': self.hf_placed_at,
            'hf_processed_at': self.hf_processed_at,
            'hf_dispatched_at': self.hf_dispatched_at or fields.Datetime.now(),
            'hf_transit_source_picking_id': self.id,
            'hf_final_location_dest_id': final_location.id,
        })

        move_vals_list = []
        for move in self.move_ids.filtered(lambda rec: rec.state != 'cancel'):
            move_vals_list.append({
                'description_picking': move.description_picking,
                'product_id': move.product_id.id,
                'product_uom_qty': move.product_uom_qty,
                'product_uom': move.product_uom.id,
                'picking_id': receipt.id,
                'picking_type_id': receiving_type.id,
                'location_id': transit_location.id,
                'location_dest_id': final_location.id,
                'company_id': self.company_id.id,
                'origin': move.origin or self.origin or self.name,
            })
        if move_vals_list:
            self.env['stock.move'].create(move_vals_list)
            receipt.action_confirm()
            receipt.action_assign()
            receipt._hf_set_progress_state('dispatched')

        self.with_context(hf_skip_picking_type_autofix=True).write({
            'hf_transit_receipt_picking_id': receipt.id,
        })
        return receipt

    # ------------------------------------------------------------------
    # Auto-fix: operation type must belong to the warehouse that owns the
    # driving location, so sequence numbering stays aligned with that
    # warehouse (Lagos, Abuja, PHC, ...).
    # ------------------------------------------------------------------
    @api.onchange('location_id', 'location_dest_id')
    def _hf_onchange_locations_autofix_operation_type(self):
        for picking in self:
            if picking.state != 'draft':
                continue
            if not picking.location_id or not picking.location_dest_id or not picking.picking_type_id:
                continue
            desired_type = picking._hf_get_picking_type_for_locations(
                picking.picking_type_id.code,
                picking.location_id,
                picking.location_dest_id,
            )
            if not desired_type or desired_type == picking.picking_type_id:
                continue

            # Preserve user-chosen locations across the type swap (changing
            # picking_type_id triggers a compute that may reset them).
            src = picking.location_id
            dst = picking.location_dest_id
            picking.picking_type_id = desired_type
            picking.location_id = src
            picking.location_dest_id = dst

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            vals.setdefault('hf_progress_state', 'placed')
            vals.setdefault('hf_placed_at', now)
        return super().create(vals_list)

    def write(self, vals):
        def after_write(res):
            if vals.get('signature') or vals.get('hf_signature_bypassed'):
                delivered = self.filtered(lambda picking: picking.state == 'done' and picking._hf_has_proof_of_delivery())
                delivered._hf_set_progress_state('delivered')
            return res

        if self.env.context.get('hf_skip_picking_type_autofix'):
            return after_write(super().write(vals))

        if not any(k in vals for k in ('location_id', 'location_dest_id', 'picking_type_id')):
            return after_write(super().write(vals))

        StockLocation = self.env['stock.location']
        PickingType = self.env['stock.picking.type']

        # Group pickings that need the same resolved picking_type_id so each
        # group can be written in a single super-call. Pickings that do not
        # need any auto-fix fall into `passthrough` and also get one write.
        passthrough_ids = []
        groups = defaultdict(list)  # desired_type_id -> [picking_id, ...]

        for picking in self:
            if picking.state != 'draft':
                passthrough_ids.append(picking.id)
                continue

            new_location_id = vals.get('location_id', picking.location_id.id)
            new_dest_location_id = vals.get('location_dest_id', picking.location_dest_id.id)
            source_location = StockLocation.browse(new_location_id) if new_location_id else StockLocation
            dest_location = StockLocation.browse(new_dest_location_id) if new_dest_location_id else StockLocation
            current_type_id = vals.get('picking_type_id', picking.picking_type_id.id)
            current_type = PickingType.browse(current_type_id) if current_type_id else PickingType

            if not source_location or not dest_location or not current_type:
                passthrough_ids.append(picking.id)
                continue

            desired_type = picking._hf_get_picking_type_for_locations(
                current_type.code,
                source_location,
                dest_location,
            )
            if not desired_type or desired_type.id == current_type.id:
                passthrough_ids.append(picking.id)
                continue

            groups[desired_type.id].append(picking.id)

        res = True

        if passthrough_ids:
            res = super(StockPicking, self.browse(passthrough_ids).with_context(
                hf_skip_picking_type_autofix=True,
            )).write(vals) and res

        # For each auto-fix group, write all three fields in ONE super-call
        # so Odoo processes the picking_type_id compute and our explicit
        # location overrides in a single transaction (last-write wins on
        # location fields, because they're explicitly present in vals).
        for desired_id, picking_ids in groups.items():
            batch = self.browse(picking_ids)
            merged_vals = dict(vals)
            merged_vals['picking_type_id'] = desired_id
            merged_vals.setdefault('location_id', batch[:1].location_id.id)
            merged_vals.setdefault('location_dest_id', batch[:1].location_dest_id.id)
            res = super(StockPicking, batch.with_context(
                hf_skip_picking_type_autofix=True,
            )).write(merged_vals) and res

        return after_write(res)

    def action_assign(self):
        res = super().action_assign()
        assigned_pickings = self.filtered(lambda picking: picking.state == 'assigned')
        assigned_pickings._hf_set_progress_state('processed')
        return res

    def action_hf_set_receipt_dispatched(self):
        receipts = self.filtered(lambda picking: picking.picking_type_code == 'incoming')
        receipts._hf_set_progress_state('dispatched')
        return True

    def action_hf_process_receipt(self):
        receipts = self.filtered(lambda picking: picking.picking_type_code == 'incoming')
        receipts._hf_prepare_validate_quantities()
        res = receipts.with_context(hf_receipt_final=True).button_validate()
        receipts.filtered(lambda picking: picking.state == 'done')._hf_set_progress_state('delivered')
        return res

    def action_hf_ship_goods(self):
        for picking in self:
            if picking.picking_type_code != 'internal':
                continue
            if picking.hf_transit_receipt_picking_id:
                continue

            transit_location = picking.company_id.internal_transit_location_id
            if not transit_location:
                raise UserError(_('No internal transit location is configured for %s.', picking.company_id.display_name))
            if picking.location_dest_id == transit_location:
                raise UserError(_('This transfer is already destined for the transit location.'))

            final_location = picking.location_dest_id
            picking.with_context(hf_skip_picking_type_autofix=True).write({
                'hf_final_location_dest_id': final_location.id,
                'location_dest_id': transit_location.id,
            })
            picking._hf_prepare_validate_quantities()
            res = picking.with_context(hf_internal_dispatch=True).button_validate()
            if picking.state == 'done':
                picking._hf_set_progress_state('dispatched')
                picking._hf_create_transit_receipt_picking(final_location)
            if isinstance(res, dict):
                return res
        return True

    def action_hf_confirm_received(self):
        pickings = self
        source_pickings = pickings.filtered(lambda picking: picking.hf_transit_receipt_picking_id)
        receiving_pickings = (pickings - source_pickings) | source_pickings.mapped('hf_transit_receipt_picking_id')
        receiving_pickings = receiving_pickings.filtered(lambda picking: picking.picking_type_code == 'internal')
        receiving_pickings._hf_prepare_validate_quantities()
        res = receiving_pickings.with_context(hf_transit_receipt=True).button_validate()
        receiving_pickings.filtered(lambda picking: picking.state == 'done')._hf_set_progress_state('delivered')
        return res

    def action_hf_out_for_delivery(self):
        deliveries = self.filtered(lambda picking: picking.picking_type_code == 'outgoing')
        deliveries._hf_prepare_validate_quantities()
        res = deliveries.with_context(hf_delivery_dispatch=True).button_validate()
        deliveries.filtered(lambda picking: picking.state == 'done')._hf_set_progress_state('dispatched')
        return res

    def action_hf_mark_delivered(self):
        for picking in self.filtered(lambda rec: rec.picking_type_code == 'outgoing'):
            if picking.state != 'done':
                raise UserError(_('Only validated deliveries can be marked delivered.'))
            if not picking._hf_has_proof_of_delivery():
                raise UserError(_('Add a customer signature or use a trusted bypass before marking this delivery as delivered.'))
            picking._hf_set_progress_state('delivered')
        return True

    def button_validate(self):
        res = super().button_validate()
        if self.env.context.get('hf_bypass_signature'):
            done_pickings = self.filtered(lambda picking: picking.state == 'done')
            if done_pickings:
                done_pickings.with_context(hf_skip_picking_type_autofix=True).write({
                    'hf_signature_bypassed': True,
                })
        self._hf_mark_done_progress_from_validate()
        return res
