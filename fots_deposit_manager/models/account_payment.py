# -*- coding: utf-8 -*-

from odoo import models, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_validate(self):
        """Override to automatically reconcile payment with linked invoices."""
        # First call the original action_validate to set state to 'paid'
        res = super().action_validate()
        
        # Auto-reconcile with linked invoices
        for payment in self:
            if payment.invoice_ids and payment.move_id:
                # Get the payment's counterpart lines (receivable/payable lines)
                liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                
                # For each linked invoice, try to reconcile
                for invoice in payment.invoice_ids:
                    if invoice.state == 'posted':
                        # Get the invoice's receivable/payable lines
                        invoice_lines = invoice.line_ids.filtered(
                            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable')
                        )
                        
                        # Reconcile payment counterpart lines with invoice lines
                        if counterpart_lines and invoice_lines:
                            try:
                                (counterpart_lines + invoice_lines).reconcile()
                            except Exception as e:
                                # Log error but don't fail the validation
                                payment.message_post(
                                    body=_("Auto-reconciliation failed: %s") % str(e)
                                )
        
        return res
