# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'hf_mailbox')
class TestMailboxChaining(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Partner = self.env['res.partner']
        self.Thread = self.env['hf.mailbox.thread']
        self.Message = self.env['hf.mailbox.message']

    def test_normalize_subject(self):
        self.assertEqual(self.Thread._normalize_subject('Re: Hello World'), 'hello world')
        self.assertEqual(self.Thread._normalize_subject('FWD: RE: Fw: Test'), 'test')
        self.assertEqual(self.Thread._normalize_subject('   Already clean   '), 'already clean')
        self.assertEqual(self.Thread._normalize_subject(''), '')

    def test_mirror_creates_thread_and_message(self):
        partner = self.Partner.create({'name': 'Alice', 'email': 'alice@example.com'})
        record = self.Partner.create({'name': 'Ticket Holder'})
        mm = self.env['mail.message'].create({
            'model': 'res.partner',
            'res_id': record.id,
            'subject': 'Pricing question',
            'body': '<p>Hi, how much?</p>',
            'message_type': 'email',
            'author_id': partner.id,
        })
        mirrored = self.Message.search([('mail_message_id', '=', mm.id)])
        self.assertTrue(mirrored, "mail.message should be mirrored into hf.mailbox.message")
        self.assertEqual(mirrored.thread_id.source_model, 'res.partner')
        self.assertEqual(mirrored.thread_id.source_res_id, record.id)
        self.assertEqual(mirrored.direction, 'incoming')

    def test_same_record_reuses_thread(self):
        record = self.Partner.create({'name': 'Customer'})
        mm1 = self.env['mail.message'].create({
            'model': 'res.partner', 'res_id': record.id,
            'subject': 'Order update', 'body': '<p>1</p>',
            'message_type': 'email',
        })
        mm2 = self.env['mail.message'].create({
            'model': 'res.partner', 'res_id': record.id,
            'subject': 'Re: Order update', 'body': '<p>2</p>',
            'message_type': 'email',
        })
        t1 = self.Message.search([('mail_message_id', '=', mm1.id)]).thread_id
        t2 = self.Message.search([('mail_message_id', '=', mm2.id)]).thread_id
        self.assertEqual(t1, t2)
        self.assertEqual(t1.message_count, 2)
