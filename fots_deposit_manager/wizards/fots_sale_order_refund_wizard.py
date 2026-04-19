# -*- coding: utf-8 -*-

from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError


class FotsSaleOrderRefundWizard(models.TransientModel):
    _name = 'fots.sale.order.refund.wizard'
    _description = 'FOTS Sales Order Refund'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        required=True,
    )
    available_picking_ids = fields.Many2many(
        'stock.picking',
        compute='_compute_available_documents',
    )
    available_invoice_ids = fields.Many2many(
        'account.move',
        compute='_compute_available_documents',
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery',
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Customer Invoice',
    )
    line_ids = fields.One2many(
        'fots.sale.order.refund.line',
        'wizard_id',
        string='Products to Return',
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        order = self.env['sale.order'].browse(values.get('sale_order_id'))
        if not order and self.env.context.get('active_model') == 'sale.order':
            order = self.env['sale.order'].browse(self.env.context.get('active_id'))
            if order:
                values['sale_order_id'] = order.id

        if order:
            pickings = order._fots_refund_delivery_candidates()
            invoices = order._fots_refund_invoice_candidates()
            if len(pickings) == 1:
                values['picking_id'] = pickings.id
            if len(invoices) == 1:
                values['invoice_id'] = invoices.id
        return values

    @api.depends('sale_order_id')
    def _compute_available_documents(self):
        for wizard in self:
            if wizard.sale_order_id:
                wizard.available_picking_ids = wizard.sale_order_id._fots_refund_delivery_candidates()
                wizard.available_invoice_ids = wizard.sale_order_id._fots_refund_invoice_candidates()
            else:
                wizard.available_picking_ids = False
                wizard.available_invoice_ids = False

    @api.onchange('picking_id', 'invoice_id')
    def _onchange_refund_documents(self):
        for wizard in self:
            wizard.line_ids = [Command.clear()]
            if wizard.picking_id and wizard.invoice_id:
                wizard.line_ids = [
                    Command.create(vals)
                    for vals in wizard._prepare_refund_line_values()
                ]

    def _check_fots_order(self):
        self.ensure_one()
        if not self.sale_order_id.fots_agent_id:
            raise UserError(_('Refund is only available for FOTS agent orders.'))
        if self.sale_order_id.state != 'sale':
            raise UserError(_('Refund is only available for confirmed FOTS sales orders.'))
        if not self.picking_id:
            raise UserError(_('Select a done delivery before processing the return.'))
        if self.picking_id not in self.available_picking_ids:
            raise UserError(_('The selected delivery is not a done outgoing delivery for this sales order.'))
        if not self.invoice_id:
            raise UserError(_('Select a posted customer invoice before processing the return.'))
        if self.invoice_id not in self.available_invoice_ids:
            raise UserError(_('The selected invoice is not a posted customer invoice for this sales order.'))

    def _get_invoice_line_for_move(self, move):
        self.ensure_one()
        sale_line = move.sale_line_id
        invoice_lines = self.invoice_id.invoice_line_ids.filtered(
            lambda line: line.display_type == 'product'
        )
        if not sale_line:
            product_lines = invoice_lines.filtered(lambda line: line.product_id == move.product_id)
            return product_lines[:1]

        sale_linked_lines = invoice_lines.filtered(lambda line: sale_line in line.sale_line_ids)
        if sale_linked_lines:
            return sale_linked_lines[:1]

        sale_invoice_lines = sale_line.invoice_lines.filtered(lambda line: line.move_id == self.invoice_id)
        if sale_invoice_lines:
            return sale_invoice_lines[:1]

        product_lines = invoice_lines.filtered(
            lambda line: line.product_id == move.product_id
            or line.product_id == sale_line.product_id
        )
        if product_lines:
            return product_lines[:1]

        template_lines = invoice_lines.filtered(
            lambda line: line.product_id.product_tmpl_id
            and line.product_id.product_tmpl_id in (move.product_id.product_tmpl_id | sale_line.product_id.product_tmpl_id)
        )
        if template_lines:
            return template_lines[:1]

        if len(invoice_lines) == 1 and len(self.sale_order_id.order_line.filtered(lambda line: not line.display_type)) == 1:
            return invoice_lines

        return self.env['account.move.line']

    def _get_returned_quantity(self, move):
        returned_moves = move.move_dest_ids.filtered(
            lambda returned_move: returned_move.origin_returned_move_id == move
            and returned_move.state != 'cancel'
        )
        return sum(returned_moves.mapped('quantity'))

    def _prepare_refund_line_values(self):
        self.ensure_one()
        values = []
        for move in self.picking_id.move_ids.filtered(lambda m: m.state == 'done' and m.sale_line_id):
            returned_qty = self._get_returned_quantity(move)
            returnable_qty = move.product_uom.round(move.quantity - returned_qty)
            if move.product_uom.compare(returnable_qty, 0.0) <= 0:
                continue
            invoice_line = self._get_invoice_line_for_move(move)
            values.append({
                'product_id': move.product_id.id,
                'move_id': move.id,
                'sale_line_id': move.sale_line_id.id,
                'invoice_line_id': invoice_line.id,
                'delivered_qty': move.quantity,
                'returned_qty': returned_qty,
                'returnable_qty': returnable_qty,
                'return_qty': 0.0,
                'product_uom_id': move.product_uom.id,
            })
        return values

    def _rebuild_refund_lines(self):
        self.ensure_one()
        commands = [Command.clear()]
        if self.picking_id and self.invoice_id:
            commands += [
                Command.create(line_values)
                for line_values in self._prepare_refund_line_values()
            ]
        self.write({'line_ids': commands})

    def _get_lines_to_return(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda line: line.return_qty)
        if not lines:
            raise UserError(_('Enter a return quantity for at least one product.'))
        for line in lines:
            if not line.invoice_line_id and line.move_id:
                line.invoice_line_id = self._get_invoice_line_for_move(line.move_id)
            line._check_return_qty()
            if not line.invoice_line_id:
                raise UserError(_(
                    'Product %(product)s cannot be refunded automatically because no matching posted invoice line was found.'
                ) % {'product': line.product_id.display_name})
        return lines

    def _create_and_validate_return_picking(self, lines):
        self.ensure_one()
        return_wizard = self.env['stock.return.picking'].with_context(
            active_model='stock.picking',
            active_id=self.picking_id.id,
            active_ids=self.picking_id.ids,
        ).create({'picking_id': self.picking_id.id})

        for return_move in return_wizard.product_return_moves:
            line = lines.filtered(lambda l: l.move_id == return_move.move_id)
            return_move.quantity = line[:1].return_qty if line else 0.0

        return_picking = return_wizard._create_return()
        for move in return_picking.move_ids:
            if move.product_uom.compare(move.quantity, 0.0) <= 0:
                move.quantity = move.product_uom_qty
        return_picking.with_context(
            skip_backorder=True,
            skip_sanity_check=True,
            cancel_backorder=True,
        ).button_validate()
        return return_picking

    def _prepare_credit_note_line_vals(self, line):
        invoice_line = line.invoice_line_id
        quantity = line.product_uom_id._compute_quantity(
            line.return_qty,
            invoice_line.product_uom_id,
            rounding_method='HALF-UP',
        )
        return {
            'product_id': invoice_line.product_id.id,
            'name': invoice_line.name,
            'quantity': quantity,
            'product_uom_id': invoice_line.product_uom_id.id,
            'price_unit': invoice_line.price_unit,
            'discount': invoice_line.discount,
            'tax_ids': [Command.set(invoice_line.tax_ids.ids)],
            'account_id': invoice_line.account_id.id,
            'analytic_distribution': invoice_line.analytic_distribution,
            'sale_line_ids': [Command.set(line.sale_line_id.ids)],
        }

    def _create_and_post_credit_note(self, lines, return_picking):
        self.ensure_one()
        invoice = self.invoice_id
        credit_note = self.env['account.move'].with_context(
            default_move_type='out_refund',
        ).create({
            'move_type': 'out_refund',
            'partner_id': invoice.partner_id.id,
            'partner_shipping_id': invoice.partner_shipping_id.id,
            'journal_id': invoice.journal_id.id,
            'currency_id': invoice.currency_id.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': self.sale_order_id.name,
            'invoice_payment_term_id': invoice.invoice_payment_term_id.id,
            'invoice_user_id': invoice.invoice_user_id.id,
            'company_id': invoice.company_id.id,
            'reversed_entry_id': invoice.id,
            'ref': _('Return of %(invoice)s / %(picking)s', invoice=invoice.name, picking=return_picking.name),
            'invoice_line_ids': [
                Command.create(self._prepare_credit_note_line_vals(line))
                for line in lines
            ],
        })
        credit_note.action_post()
        return credit_note

    def action_process_return(self):
        self.ensure_one()
        self._check_fots_order()
        lines = self._get_lines_to_return()
        return_picking = self._create_and_validate_return_picking(lines)
        credit_note = self._create_and_post_credit_note(lines, return_picking)

        return {
            'name': _('Credit Note'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': credit_note.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_move_type': 'out_refund'},
        }


class FotsSaleOrderRefundLine(models.TransientModel):
    _name = 'fots.sale.order.refund.line'
    _description = 'FOTS Sales Order Refund Line'

    wizard_id = fields.Many2one(
        'fots.sale.order.refund.wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one('product.product', string='Product')
    move_id = fields.Many2one('stock.move', string='Delivery Move')
    sale_line_id = fields.Many2one('sale.order.line', string='Sales Order Line')
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line')
    delivered_qty = fields.Float(string='Delivered Qty', digits='Product Unit')
    returned_qty = fields.Float(string='Already Returned', digits='Product Unit')
    returnable_qty = fields.Float(string='Returnable Qty', digits='Product Unit')
    return_qty = fields.Float(string='Return Qty', digits='Product Unit')
    product_uom_id = fields.Many2one('uom.uom', string='Unit')

    def _check_return_qty(self):
        self.ensure_one()
        if self.product_uom_id.compare(self.return_qty, 0.0) <= 0:
            raise UserError(_(
                'Return quantity for %(product)s must be greater than zero.'
            ) % {'product': self.product_id.display_name})
        if self.product_uom_id.compare(self.return_qty, self.returnable_qty) > 0:
            raise UserError(_(
                'Return quantity for %(product)s cannot exceed the returnable quantity (%(qty)s %(uom)s).'
            ) % {
                'product': self.product_id.display_name,
                'qty': self.returnable_qty,
                'uom': self.product_uom_id.display_name,
            })
