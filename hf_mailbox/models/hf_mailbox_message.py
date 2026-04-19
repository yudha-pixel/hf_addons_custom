# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models

HTML_TAG_RE = re.compile(r'<[^>]+>')
WS_RE = re.compile(r'\s+')


class HfMailboxMessage(models.Model):
    _name = 'hf.mailbox.message'
    _description = 'Mailbox Message (link to mail.message)'
    _order = 'date desc, id desc'
    _rec_name = 'subject'

    mail_message_id = fields.Many2one(
        'mail.message', required=True, ondelete='cascade', index=True,
    )
    thread_id = fields.Many2one(
        'hf.mailbox.thread', required=True, ondelete='cascade', index=True,
    )
    chain_index = fields.Integer(index=True, default=0)
    direction = fields.Selection(
        [('incoming', 'Incoming'),
         ('outgoing', 'Outgoing'),
         ('internal', 'Internal')],
        required=True, index=True,
    )

    subject = fields.Char(related='mail_message_id.subject', store=False)
    date = fields.Datetime(related='mail_message_id.date', store=True, index=True)
    author_id = fields.Many2one(related='mail_message_id.author_id', store=True)
    email_from = fields.Char(related='mail_message_id.email_from', store=False)
    partner_ids = fields.Many2many(related='mail_message_id.partner_ids', store=False)
    incoming_email_to = fields.Text(related='mail_message_id.incoming_email_to', store=False)
    outgoing_email_to = fields.Char(related='mail_message_id.outgoing_email_to', store=False)
    body = fields.Html(related='mail_message_id.body', store=False, sanitize=False)
    message_type = fields.Selection(related='mail_message_id.message_type', store=False)
    display_from = fields.Char(compute='_compute_display_addresses')
    display_to = fields.Char(compute='_compute_display_addresses')

    _unique_mail_message = models.Constraint(
        'UNIQUE(mail_message_id)',
        'This mail.message is already mirrored in the mailbox.',
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.depends(
        'author_id', 'author_id.name', 'email_from', 'partner_ids',
        'partner_ids.name', 'partner_ids.email', 'incoming_email_to',
        'outgoing_email_to', 'direction',
    )
    def _compute_display_addresses(self):
        for rec in self:
            rec.display_from = rec._format_sender()
            rec.display_to = rec._format_recipients()

    def _format_sender(self):
        self.ensure_one()
        email_from = (self.email_from or '').strip()
        author_name = self.author_id.display_name if self.author_id else ''
        if email_from and '<' in email_from and '>' in email_from:
            return email_from
        if author_name and email_from:
            return f'{author_name} <{email_from}>'
        return author_name or email_from or ''

    def _format_recipients(self):
        self.ensure_one()
        if self.direction == 'outgoing' and self.outgoing_email_to:
            return self.outgoing_email_to
        if self.direction == 'incoming' and self.incoming_email_to:
            return self.incoming_email_to
        recipients = []
        for partner in self.partner_ids:
            if partner.email:
                recipients.append(f'{partner.display_name} <{partner.email}>')
            else:
                recipients.append(partner.display_name)
        return ', '.join(recipients)

    @api.model
    def _infer_direction(self, mail_message):
        """Classify a mail.message as incoming / outgoing / internal."""
        mtype = mail_message.message_type
        subtype = mail_message.subtype_id
        if mtype == 'email_outgoing':
            return 'outgoing'
        if mtype == 'email':
            # If the author is an internal user, treat as outgoing.
            if mail_message.author_id and mail_message.author_id.user_ids.filtered(
                lambda u: u.share is False
            ):
                return 'outgoing'
            return 'incoming'
        if mtype in ('comment', 'notification') and subtype and subtype.internal:
            return 'internal'
        if mtype == 'comment':
            return 'outgoing' if mail_message.author_id else 'internal'
        return 'internal'

    @api.model
    def _build_snippet(self, mail_message, length=200):
        body = mail_message.body or ''
        text = HTML_TAG_RE.sub(' ', body)
        text = WS_RE.sub(' ', text).strip()
        return text[:length]

    @api.model
    def _mirror_from_mail_message(self, mail_messages):
        """Create hf.mailbox.message for the given mail.message recordset."""
        self = self.sudo()
        if not mail_messages:
            return self.browse()
        existing = self.search([('mail_message_id', 'in', mail_messages.ids)])
        existing_ids = set(existing.mapped('mail_message_id').ids)
        to_create = []
        Thread = self.env['hf.mailbox.thread'].sudo()
        for mm in mail_messages:
            if mm.id in existing_ids:
                continue
            # Skip pure system notifications without any meaningful content.
            if mm.message_type not in ('email', 'comment', 'email_outgoing'):
                continue
            thread = Thread._find_or_create_for_message(mm)
            if not thread:
                continue
            direction = self._infer_direction(mm)
            chain_index = len(thread.message_ids) + 1
            to_create.append({
                'mail_message_id': mm.id,
                'thread_id': thread.id,
                'direction': direction,
                'chain_index': chain_index,
            })
            thread._touch_from_message(mm, direction)
        if not to_create:
            return self.browse()
        return self.create(to_create)
