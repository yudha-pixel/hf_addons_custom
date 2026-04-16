# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HfMailboxCompose(models.TransientModel):
    """Lightweight "New Message" wizard for the Mailbox app.

    Avoids the issues of opening Odoo's ``mail.compose.message`` without a
    source record (which fails with ``JSON.parse`` of empty ``res_ids``).
    Each selected partner becomes the source record of a new mailbox thread.
    """
    _name = 'hf.mailbox.compose'
    _description = 'Mailbox Compose Wizard'

    partner_ids = fields.Many2many(
        'res.partner', string='Recipients', required=True,
    )
    subject = fields.Char(required=True)
    body = fields.Html(sanitize=True)
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'hf_mailbox_compose_attachment_rel',
        'wizard_id', 'attachment_id',
        string='Attachments',
    )
    message_type = fields.Selection(
        [('email', 'Email'), ('comment', 'Log Note')],
        default='email', required=True,
    )
    mail_server_id = fields.Many2one(
        'ir.mail_server', string='Outgoing Mail Server',
    )

    def action_send(self):
        self.ensure_one()
        if not self.partner_ids:
            raise UserError(_("Please select at least one recipient."))
        subtype = 'mail.mt_note' if self.message_type == 'comment' else 'mail.mt_comment'
        mtype = 'comment' if self.message_type == 'comment' else 'email_outgoing'
        post_kwargs_base = {
            'body': self.body or '',
            'subject': self.subject,
            'message_type': mtype,
            'subtype_xmlid': subtype,
            'attachment_ids': [att.id for att in self.attachment_ids],
        }
        if self.mail_server_id:
            post_kwargs_base['mail_server_id'] = self.mail_server_id.id
        for partner in self.partner_ids:
            partner.message_post(
                partner_ids=[partner.id],
                **post_kwargs_base,
            )
        # Detach attachments so transient cleanup doesn't wipe them.
        if self.attachment_ids:
            self.attachment_ids = [(5,)]
        return {'type': 'ir.actions.act_window_close'}
