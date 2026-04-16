# -*- coding: utf-8 -*-
import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, vals_list):
        messages = super().create(vals_list)
        try:
            self.env['hf.mailbox.message'].sudo()._mirror_from_mail_message(messages)
        except Exception:  # pragma: no cover - defensive
            _logger.exception("hf_mailbox: failed to mirror mail.message into mailbox")
        return messages
