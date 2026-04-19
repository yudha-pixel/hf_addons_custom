/** @odoo-module **/

import { Component, markup } from "@odoo/owl";

const HTML_ENTITY_RE = /&(?:lt|gt|amp|quot|#39|#x27);/i;
const HTML_TAG_RE = /<\s*[a-z][\s\S]*>/i;

/**
 * Single message card within a conversation (Gmail-style).
 * Collapsed by default; click to expand/collapse.
 * Props:
 *   - message: {id, display_from, display_to, direction, date, body, subject}
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
        return m.display_from
            || (m.author_id && m.author_id.length > 1 && m.author_id[1])
            || m.email_from
            || "?";
    }

    get recipientLabel() {
        return this.props.message.display_to || "";
    }

    get bodyContent() {
        const body = this.props.message.body || "";
        const normalized = this._decodeEscapedHtml(body);
        if (!HTML_TAG_RE.test(normalized)) {
            return body;
        }
        const sanitized = window.DOMPurify ? window.DOMPurify.sanitize(normalized) : normalized;
        return markup(sanitized);
    }

    get cssClass() {
        const m = this.props.message;
        const base = `o_hf_msg ${m.direction || "internal"}`;
        return this.props.expanded ? `${base} expanded` : `${base} collapsed`;
    }

    onClick() {
        this.props.onToggle(this.props.message.id);
    }

    _decodeEscapedHtml(value) {
        if (!HTML_ENTITY_RE.test(value)) {
            return value;
        }
        const textarea = document.createElement("textarea");
        textarea.innerHTML = value;
        return textarea.value;
    }
}
