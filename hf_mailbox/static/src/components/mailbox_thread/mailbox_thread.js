/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * Single message card within a conversation (Gmail-style).
 * Collapsed by default; click to expand/collapse.
 * Props:
 *   - message: {id, author_id, email_from, direction, date, body, subject}
 *   - expanded: boolean
 *   - onToggle(id): callback
 */
export class MailboxMessage extends Component {
    static template = "hf_mailbox.MailboxMessage";
    static props = {
        message: Object,
        expanded: Boolean,
        onToggle: Function,
    };

    get authorLabel() {
        const m = this.props.message;
        if (m.author_id && m.author_id.length > 1) return m.author_id[1];
        return m.email_from || "?";
    }

    get cssClass() {
        const m = this.props.message;
        const base = `o_hf_msg ${m.direction || "internal"}`;
        return this.props.expanded ? `${base} expanded` : `${base} collapsed`;
    }

    onClick() {
        this.props.onToggle(this.props.message.id);
    }
}
