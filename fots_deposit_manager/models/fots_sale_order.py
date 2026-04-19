# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    fots_agent_id = fields.Many2one(
        'fots.agent',
        string='FOTS Agent',
        tracking=True,
        help='Link this sales order to a FOTS agent for analytics and wholesale tracking.',
    )

    fots_team_id = fields.Many2one(
        related='fots_agent_id.team_id',
        string='FOTS Team',
        store=True,
        readonly=True,
    )

    @api.onchange('fots_agent_id')
    def _onchange_fots_agent_id(self):
        if not self.fots_agent_id:
            return
        if self.fots_agent_id.partner_id:
            self.partner_id = self.fots_agent_id.partner_id
        if self.fots_agent_id.pricelist_id:
            self.pricelist_id = self.fots_agent_id.pricelist_id

    @api.constrains('fots_agent_id', 'partner_id')
    def _check_agent_partner_match(self):
        for order in self:
            if order.fots_agent_id and order.fots_agent_id.partner_id:
                if order.partner_id != order.fots_agent_id.partner_id:
                    raise ValidationError(_(
                        'The sales order customer must match the agent\'s customer (%s).'
                    ) % order.fots_agent_id.partner_id.name)

    def action_fots_buy_and_go(self):
        """Buy-and-Go: Confirm SO, validate delivery, create invoice, register full payment.

        Intended for direct B2B wholesale at the office counter: the FOTS agent pays
        cash/transfer upfront and takes the goods immediately.
        """
        self.ensure_one()

        if not self.fots_agent_id:
            raise UserError(_('Buy & Go is only available for FOTS agent orders.'))
        if self.state not in ('draft', 'sent'):
            raise UserError(_('This order is already confirmed. Buy & Go can only be used on a draft quotation.'))
        if not self.order_line:
            raise UserError(_('Add at least one product line before using Buy & Go.'))

        # Enforce Dozen-only on the supply path. Returns (credit note +
        # return picking) are unaffected, so agents can still return fractional
        # dozens (3 packs = 0.25 dz, 6 packs = 0.5 dz) via native flows.
        dozen_uom = self.env.ref('uom.product_uom_dozen', raise_if_not_found=False)
        if dozen_uom:
            non_dozen = self.order_line.filtered(
                lambda l: l.product_id and l.product_uom_id
                          and not l.product_uom_id._has_common_reference(dozen_uom)
            )
            if non_dozen:
                raise UserError(_(
                    'Buy & Go requires every line to use a unit of measure compatible with Dozens. '
                    'The following lines use an incompatible unit of measure:\n- %s'
                ) % '\n- '.join(non_dozen.mapped('product_id.display_name')))

        # 1. Confirm the sale order.
        self.action_confirm()

        # 2. Validate every outgoing picking in one shot.
        pickings = self.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        if pickings:
            pickings = pickings.with_context(
                skip_backorder=True,
                skip_sanity_check=True,
                cancel_backorder=True,
            )
            pickings.button_validate()

        # 3. Create and post the customer invoice.
        invoices = self._create_invoices(final=True)
        if not invoices:
            raise UserError(_('Unable to generate a customer invoice for this order.'))
        invoices.action_post()

        # 4. Register the payment automatically (Odoo picks default journal & method).
        payment_register = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=invoices.ids,
        ).create({})
        payment_register.action_create_payments()

        # 5. Reopen the SO form so the admin sees the result.
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _fots_refund_delivery_candidates(self):
        self.ensure_one()
        return self.picking_ids.filtered(
            lambda picking: picking.state == 'done' and picking.picking_type_code == 'outgoing'
        )

    def _fots_refund_invoice_candidates(self):
        self.ensure_one()
        return self.invoice_ids.filtered(
            lambda invoice: invoice.state == 'posted' and invoice.move_type == 'out_invoice'
        )

    def action_fots_open_refund_wizard(self):
        self.ensure_one()

        if not self.fots_agent_id:
            raise UserError(_('Refund is only available for FOTS agent orders.'))
        if self.state != 'sale':
            raise UserError(_('Refund is only available for confirmed FOTS sales orders.'))

        deliveries = self._fots_refund_delivery_candidates()
        invoices = self._fots_refund_invoice_candidates()
        if not deliveries:
            raise UserError(_('This FOTS sales order has no done outgoing delivery to return.'))
        if not invoices:
            raise UserError(_(
                'This FOTS sales order has no posted customer invoice to refund.'
            ))

        wizard = self.env['fots.sale.order.refund.wizard'].create({
            'sale_order_id': self.id,
            'picking_id': deliveries[:1].id,
            'invoice_id': invoices[:1].id,
        })
        wizard._rebuild_refund_lines()

        return {
            'name': _('FOTS Refund'),
            'type': 'ir.actions.act_window',
            'res_model': 'fots.sale.order.refund.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'fots_deposit_manager.view_fots_sale_order_refund_wizard_form'
            ).id,
            'target': 'new',
        }
