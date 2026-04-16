# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models


SUBJECT_PREFIX_RE = re.compile(
    r'^\s*(?:(?:re|fw|fwd|aw|sv|tr|rv)\s*(?:\[\d+\])?\s*:\s*)+',
    re.IGNORECASE,
)


class HfMailboxThread(models.Model):
    _name = 'hf.mailbox.thread'
    _description = 'Mailbox Conversation'
    _order = 'last_message_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Subject', required=True, index=True)
    normalized_subject = fields.Char(index=True, readonly=True)
    source_model = fields.Char(index=True)
    source_res_id = fields.Many2oneReference(model_field='source_model', index=True)
    source_ref = fields.Reference(
        selection='_selection_source_model',
        compute='_compute_source_ref',
        string='Source Record',
    )

    participant_ids = fields.Many2many(
        'res.partner',
        'hf_mailbox_thread_partner_rel',
        'thread_id', 'partner_id',
        string='Participants',
    )
    message_ids = fields.One2many(
        'hf.mailbox.message', 'thread_id', string='Messages',
    )
    message_count = fields.Integer(compute='_compute_message_count', store=True)
    last_message_date = fields.Datetime(index=True)
    last_author_id = fields.Many2one('res.partner', string='Last Author')
    last_direction = fields.Selection(
        [('incoming', 'Incoming'), ('outgoing', 'Outgoing'), ('internal', 'Internal')],
    )
    snippet = fields.Text(help="Preview of the most recent message.")

    state = fields.Selection(
        [('open', 'Open'),
         ('waiting', 'Waiting Reply'),
         ('done', 'Done')],
        default='open', index=True,
    )
    label_ids = fields.Many2many(
        'hf.mailbox.label',
        'hf_mailbox_thread_label_rel',
        'thread_id', 'label_id',
        string='Labels',
    )

    followup_due_date = fields.Datetime(index=True)
    followup_done = fields.Boolean(default=False)

    @api.model
    def _selection_source_model(self):
        """Return selection of installed models that inherit mail.thread.
        Detection: model exposes ``message_post`` attribute from the mixin."""
        models_list = []
        for m in self.env['ir.model'].sudo().search([('transient', '=', False)]):
            Model = self.env.get(m.model)
            if Model is None:
                continue
            inherit = getattr(Model, '_inherit', None) or ()
            if isinstance(inherit, str):
                inherit = (inherit,)
            if 'mail.thread' in inherit \
                    or hasattr(Model, '_mail_post_access') \
                    or 'message_post' in type(Model).__dict__:
                models_list.append((m.model, m.name))
        return models_list or [('mail.thread', 'Mail Thread')]

    @api.depends('message_ids')
    def _compute_message_count(self):
        for rec in self:
            rec.message_count = len(rec.message_ids)

    @api.depends('source_model', 'source_res_id')
    def _compute_source_ref(self):
        for rec in self:
            if rec.source_model and rec.source_res_id and rec.source_model in self.env:
                rec.source_ref = f'{rec.source_model},{rec.source_res_id}'
            else:
                rec.source_ref = False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _normalize_subject(self, subject):
        if not subject:
            return ''
        s = SUBJECT_PREFIX_RE.sub('', subject.strip())
        s = re.sub(r'\s+', ' ', s).strip().lower()
        return s[:240]

    @api.model
    def _find_or_create_for_message(self, mail_message):
        """Get (or create) a hf.mailbox.thread for a given mail.message."""
        self = self.sudo()
        if not mail_message:
            return self.browse()

        source_model = mail_message.model or False
        source_res_id = mail_message.res_id or False
        normalized = self._normalize_subject(mail_message.subject or '')

        domain = []
        if source_model and source_res_id:
            domain = [
                ('source_model', '=', source_model),
                ('source_res_id', '=', source_res_id),
            ]
            thread = self.search(domain, limit=1)
            if thread:
                return thread

        # Fallback: match by normalized subject + any shared participant
        participants = self._collect_participants(mail_message)
        if normalized and participants:
            thread = self.search([
                ('normalized_subject', '=', normalized),
                ('participant_ids', 'in', participants.ids),
            ], limit=1)
            if thread:
                # keep source info stable on first linkage
                if not thread.source_model and source_model:
                    thread.write({
                        'source_model': source_model,
                        'source_res_id': source_res_id,
                    })
                return thread

        thread = self.create({
            'name': mail_message.subject or '(no subject)',
            'normalized_subject': normalized,
            'source_model': source_model,
            'source_res_id': source_res_id,
            'participant_ids': [(6, 0, participants.ids)] if participants else False,
            'last_message_date': mail_message.date,
            'last_author_id': mail_message.author_id.id,
            'snippet': (mail_message.preview or '')[:500] if hasattr(mail_message, 'preview') else '',
        })
        return thread

    @api.model
    def _collect_participants(self, mail_message):
        partners = self.env['res.partner']
        if mail_message.author_id:
            partners |= mail_message.author_id
        partners |= mail_message.partner_ids
        return partners

    def _touch_from_message(self, mail_message, direction):
        for rec in self:
            rec.write({
                'last_message_date': mail_message.date,
                'last_author_id': mail_message.author_id.id,
                'last_direction': direction,
                'snippet': self.env['hf.mailbox.message']._build_snippet(mail_message),
            })
            new_partners = self._collect_participants(mail_message) - rec.participant_ids
            if new_partners:
                rec.participant_ids = [(4, p.id) for p in new_partners]
            if direction == 'incoming' and rec.state == 'waiting':
                rec.state = 'open'
                rec.followup_due_date = False

    def action_mark_done(self):
        return self.write({'state': 'done', 'followup_due_date': False})

    def action_mark_waiting(self):
        return self.write({'state': 'waiting'})

    def action_reopen(self):
        return self.write({'state': 'open', 'followup_done': False})

    # ------------------------------------------------------------------
    # Follow-up cron
    # ------------------------------------------------------------------
    @api.model
    def _cron_check_followups(self, days=None):
        """Mark open threads whose last message is outgoing and older than
        ``days`` as waiting, create a reminder activity once."""
        from datetime import timedelta
        ICP = self.env['ir.config_parameter'].sudo()
        if days is None:
            days = int(ICP.get_param('hf_mailbox.followup_days', 3))
        cutoff = fields.Datetime.now() - timedelta(days=days)
        threads = self.sudo().search([
            ('state', '=', 'open'),
            ('last_direction', '=', 'outgoing'),
            ('last_message_date', '<=', cutoff),
            ('followup_done', '=', False),
        ], limit=500)
        if not threads:
            return True
        followup_label = self.env['hf.mailbox.label']._get_system_label('followup')
        ActivityType = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for thread in threads:
            thread.write({
                'state': 'waiting',
                'followup_due_date': fields.Datetime.now(),
                'followup_done': True,
            })
            if followup_label:
                thread.label_ids = [(4, followup_label.id)]
            if ActivityType and thread.source_model and thread.source_res_id \
                    and thread.source_model in self.env:
                try:
                    record = self.env[thread.source_model].browse(thread.source_res_id)
                    if record.exists() and thread.last_author_id:
                        user = thread.last_author_id.user_ids[:1]
                        if user:
                            record.with_user(user).activity_schedule(
                                activity_type_id=ActivityType.id,
                                summary=f"Mailbox follow-up: {thread.name}",
                                note="No reply received after %s day(s)." % days,
                                user_id=user.id,
                            )
                except Exception:  # pragma: no cover
                    _logger_fallback = None
        return True

    def action_open_source(self):
        self.ensure_one()
        if not self.source_model or not self.source_res_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.source_model,
            'res_id': self.source_res_id,
            'views': [(False, 'form')],
            'target': 'current',
        }
