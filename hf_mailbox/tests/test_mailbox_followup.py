# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'hf_mailbox')
class TestMailboxFollowup(TransactionCase):

    def test_cron_marks_waiting(self):
        record = self.env['res.partner'].create({'name': 'Lead Example'})
        user_partner = self.env.user.partner_id
        mm = self.env['mail.message'].create({
            'model': 'res.partner', 'res_id': record.id,
            'subject': 'Quote sent', 'body': '<p>here</p>',
            'message_type': 'email',
            'author_id': user_partner.id,
        })
        thread = self.env['hf.mailbox.message'].search(
            [('mail_message_id', '=', mm.id)]).thread_id
        self.assertTrue(thread, "thread must exist for cron test")
        # Force last_message_date backwards past threshold.
        thread.write({
            'last_message_date': fields.Datetime.now() - timedelta(days=5),
            'last_direction': 'outgoing',
            'state': 'open',
            'followup_done': False,
        })
        self.env['hf.mailbox.thread']._cron_check_followups(days=3)
        thread.invalidate_recordset()
        self.assertEqual(thread.state, 'waiting')
        self.assertTrue(thread.followup_done)
