# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.tools import ustr

_logger = logging.getLogger(__name__)

LOOKBACK_PARAM = 'hf_mailbox.subject_match_days'
LOOKBACK_DEFAULT = 30


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.model
    def message_route(self, message, message_dict, model=None, thread_id=None, custom_values=None):
        """Post-fallback routing: if the standard logic would create a new
        record (no thread_id and no sure route), try to attach the email to
        an existing hf.mailbox.thread matched by normalized subject +
        overlapping participants.
        """
        routes = super().message_route(
            message, message_dict, model=model, thread_id=thread_id,
            custom_values=custom_values,
        )
        try:
            routes = self._hf_mailbox_augment_routes(
                routes, message, message_dict, model, thread_id, custom_values,
            )
        except Exception:  # pragma: no cover
            _logger.exception("hf_mailbox: augment_routes failed, falling back to default")
        return routes

    @api.model
    def _hf_mailbox_augment_routes(self, routes, message, message_dict, model, thread_id, custom_values):
        if thread_id:
            return routes  # Already resolved upstream.
        # Only augment when upstream produced no deterministic existing record.
        existing = [r for r in routes if r and r[1]]  # [model, res_id, ...]
        if existing:
            return routes

        subject = message_dict.get('subject') or ''
        Thread = self.env['hf.mailbox.thread'].sudo()
        normalized = Thread._normalize_subject(subject)
        if not normalized:
            return routes

        emails = self._hf_mailbox_extract_emails(message_dict)
        if not emails:
            return routes

        partners = self.env['res.partner'].sudo().search([
            ('email_normalized', 'in', emails),
        ])
        if not partners:
            return routes

        days = int(self.env['ir.config_parameter'].sudo().get_param(
            LOOKBACK_PARAM, LOOKBACK_DEFAULT,
        ))
        from datetime import timedelta
        cutoff = fields.Datetime.now() - timedelta(days=days)
        thread = Thread.search([
            ('normalized_subject', '=', normalized),
            ('participant_ids', 'in', partners.ids),
            ('last_message_date', '>=', cutoff),
            ('source_model', '!=', False),
            ('source_res_id', '!=', False),
        ], order='last_message_date desc', limit=1)
        if not thread or not thread.source_model or not thread.source_res_id:
            return routes
        if thread.source_model not in self.env:
            return routes

        route = (thread.source_model, thread.source_res_id, custom_values or {}, self.env.uid, None)
        _logger.info(
            "hf_mailbox: augmented route for incoming mail subject=%r -> %s(%s)",
            subject, thread.source_model, thread.source_res_id,
        )
        return [route]

    @api.model
    def _hf_mailbox_extract_emails(self, message_dict):
        from odoo.tools.mail import email_normalize, email_split
        pool = set()
        for key in ('email_from', 'to', 'cc', 'recipients'):
            value = message_dict.get(key) or ''
            if not value:
                continue
            for addr in email_split(ustr(value)):
                norm = email_normalize(addr)
                if norm:
                    pool.add(norm)
        return list(pool)
