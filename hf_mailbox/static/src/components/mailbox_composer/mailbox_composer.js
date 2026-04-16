/** @odoo-module **/

import { Component, useState, useRef, onMounted } from "@odoo/owl";

/**
 * Reply composer (Gmail-style).
 * Props:
 *   - onSend(body: string, { internal: boolean }): Promise
 *   - onCancel(): void
 *   - disabled?: boolean  - true when no source record is linked (cannot reply)
 */
export class MailboxComposer extends Component {
    static template = "hf_mailbox.MailboxComposer";
    static props = {
        onSend: Function,
        onCancel: Function,
        disabled: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({
            body: "",
            internal: false,
            sending: false,
        });
        this.textareaRef = useRef("textarea");
        onMounted(() => {
            if (this.textareaRef.el) this.textareaRef.el.focus();
        });
    }

    onInput(ev) {
        this.state.body = ev.target.value;
    }

    toggleInternal() {
        this.state.internal = !this.state.internal;
    }

    async send() {
        const body = (this.state.body || "").trim();
        if (!body || this.state.sending || this.props.disabled) return;
        this.state.sending = true;
        try {
            await this.props.onSend(body, { internal: this.state.internal });
            this.state.body = "";
            this.state.internal = false;
        } finally {
            this.state.sending = false;
        }
    }

    cancel() {
        this.state.body = "";
        this.state.internal = false;
        this.props.onCancel();
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
            ev.preventDefault();
            this.send();
        } else if (ev.key === "Escape") {
            ev.preventDefault();
            this.cancel();
        }
    }
}
