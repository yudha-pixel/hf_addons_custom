# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    hf_progress_state = fields.Selection(
        selection=[
            ('placed', 'Placed'),
            ('processed', 'Processed'),
            ('dispatched', 'Dispatched'),
            ('delivered', 'Delivered'),
        ],
        compute='_compute_hf_progress_state',
        store=True,
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _hf_get_internal_picking_type_from_source_location(self, location):
        warehouse = location.warehouse_id
        if not warehouse:
            return self.env['stock.picking.type']
        return warehouse.int_type_id

    # ------------------------------------------------------------------
    # Progress badge (Placed / Processed / Dispatched / Delivered)
    # ------------------------------------------------------------------
    @api.depends('state', 'picking_type_code', 'is_signed', 'signature')
    def _compute_hf_progress_state(self):
        for picking in self:
            # Defensive getattr in case a stripped-down install drops signature
            # support; the field should always exist thanks to stock/delivery.
            is_signed = getattr(picking, 'is_signed', False)

            if picking.state == 'cancel':
                picking.hf_progress_state = False
            elif picking.state == 'done':
                if picking.picking_type_code == 'outgoing':
                    picking.hf_progress_state = 'delivered' if is_signed else 'dispatched'
                else:
                    picking.hf_progress_state = 'delivered'
            elif picking.state == 'assigned':
                picking.hf_progress_state = 'processed'
            else:
                picking.hf_progress_state = 'placed'

    # ------------------------------------------------------------------
    # Auto-fix: internal-transfer picking type must belong to the
    # source location's warehouse, so sequence numbering stays aligned
    # with that warehouse (Lagos, Abuja, PHC, ...).
    # ------------------------------------------------------------------
    @api.onchange('location_id', 'location_dest_id')
    def _hf_onchange_locations_autofix_operation_type(self):
        for picking in self:
            if picking.state != 'draft':
                continue
            if not picking.location_id or not picking.picking_type_id:
                continue
            if picking.picking_type_id.code != 'internal':
                continue
            desired_type = picking._hf_get_internal_picking_type_from_source_location(picking.location_id)
            if not desired_type or desired_type == picking.picking_type_id:
                continue

            # Preserve user-chosen locations across the type swap (changing
            # picking_type_id triggers a compute that may reset them).
            src = picking.location_id
            dst = picking.location_dest_id
            picking.picking_type_id = desired_type
            picking.location_id = src
            picking.location_dest_id = dst

    def write(self, vals):
        if self.env.context.get('hf_skip_picking_type_autofix'):
            return super().write(vals)

        if not any(k in vals for k in ('location_id', 'location_dest_id', 'picking_type_id')):
            return super().write(vals)

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
            location = StockLocation.browse(new_location_id) if new_location_id else StockLocation
            current_type_id = vals.get('picking_type_id', picking.picking_type_id.id)
            current_type = PickingType.browse(current_type_id) if current_type_id else PickingType

            if not location or not current_type or current_type.code != 'internal':
                passthrough_ids.append(picking.id)
                continue

            desired_type = picking._hf_get_internal_picking_type_from_source_location(location)
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

        return res
