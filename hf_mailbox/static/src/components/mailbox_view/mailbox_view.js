/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

import { MailboxSidebar } from "../mailbox_sidebar/mailbox_sidebar";
import { MailboxMessage } from "../mailbox_thread/mailbox_thread";
import { MailboxComposer } from "../mailbox_composer/mailbox_composer";

const FOLDER_LABELS = {
    inbox: _t("Inbox"),
    sent: _t("Sent"),
    waiting: _t("Waiting Reply"),
    followup: _t("Follow-up"),
    done: _t("Done"),
};

/**
 * Main orchestrator for the Gmail-style mailbox.
 * Owns the global state (current folder, selected thread, expanded messages)
 * and coordinates between the sidebar, the thread list and the reader pane.
 * All I/O goes through the `hf_mailbox` service.
 */
export class MailboxView extends Component {
    static template = "hf_mailbox.MailboxView";
    static components = { MailboxSidebar, MailboxMessage, MailboxComposer };
    static props = { "*": true };

    setup() {
        this.mailbox = useService("hf_mailbox");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            folder: "inbox",
            labels: [],
            threads: [],
            selectedThreadId: null,
            selectedMessages: [],
            expandedMessageIds: new Set(),
            loading: false,
            composerOpen: false,
        });

        onWillStart(async () => {
            await this.refreshLabels();
            await this.refreshThreads();
        });
    }

    // ------------------------------------------------------------------
    // Loaders
    // ------------------------------------------------------------------
    async refreshLabels() {
        this.state.labels = await this.mailbox.loadLabels();
    }

    async refreshThreads() {
        this.state.loading = true;
        try {
            this.state.threads = await this.mailbox.loadThreads(this.state.folder);
            if (this.state.threads.length && !this.state.selectedThreadId) {
                await this.selectThread(this.state.threads[0].id);
            } else if (
                this.state.selectedThreadId &&
                !this.state.threads.find(t => t.id === this.state.selectedThreadId)
            ) {
                this.state.selectedThreadId = null;
                this.state.selectedMessages = [];
            }
        } finally {
            this.state.loading = false;
        }
    }

    async selectThread(threadId) {
        this.state.selectedThreadId = threadId;
        this.state.composerOpen = false;
        const messages = await this.mailbox.loadMessages(threadId);
        this.state.selectedMessages = messages;
        // Collapse history, expand the latest message only.
        this.state.expandedMessageIds = new Set();
        if (messages.length) {
            this.state.expandedMessageIds.add(messages[messages.length - 1].id);
        }
    }

    // ------------------------------------------------------------------
    // Intents (passed down to children)
    // ------------------------------------------------------------------
    onFolderChange = async (folder) => {
        this.state.folder = folder;
        this.state.selectedThreadId = null;
        await this.refreshThreads();
    };

    onCompose = () => {
        // If a thread is selected and can be replied to, open the inline Gmail-style
        // composer. Otherwise fall back to Odoo's standard mail.compose.message wizard.
        if (this.canReply) {
            this.state.composerOpen = true;
            return;
        }
        this.mailbox.openComposeWizard({
            onClose: async () => {
                await this.refreshThreads();
            },
        });
    };

    onComposerCancel = () => {
        this.state.composerOpen = false;
    };

    onMessageToggle = (id) => {
        if (this.state.expandedMessageIds.has(id)) {
            this.state.expandedMessageIds.delete(id);
        } else {
            this.state.expandedMessageIds.add(id);
        }
    };

    onComposerSend = async (body, { internal }) => {
        const thread = this.selectedThread;
        if (!thread || !thread.source_model || !thread.source_res_id) {
            this.notification.add(
                _t("Cannot reply: this conversation has no linked source record."),
                { type: "warning" },
            );
            return;
        }
        await this.mailbox.postReply(thread.source_model, thread.source_res_id, body, { internal });
        this.notification.add(
            internal ? _t("Internal note logged") : _t("Reply sent"),
            { type: "success" },
        );
        this.state.composerOpen = false;
        await this.selectThread(this.state.selectedThreadId);
        await this.refreshThreads();
    };

    // ------------------------------------------------------------------
    // Thread actions (toolbar of the reader pane)
    // ------------------------------------------------------------------
    async markDone() {
        if (!this.state.selectedThreadId) return;
        await this.mailbox.markDone([this.state.selectedThreadId]);
        this.notification.add(_t("Conversation marked as done"), { type: "success" });
        await this.refreshThreads();
    }

    async markWaiting() {
        if (!this.state.selectedThreadId) return;
        await this.mailbox.markWaiting([this.state.selectedThreadId]);
        await this.refreshThreads();
    }

    async openSource() {
        if (!this.state.selectedThreadId) return;
        const action = await this.mailbox.openSource([this.state.selectedThreadId]);
        if (action) this.action.doAction(action);
    }

    // ------------------------------------------------------------------
    // Keyboard shortcuts (on the root element)
    // ------------------------------------------------------------------
    onKeydown(ev) {
        const tag = ev.target.tagName;
        if (tag === "TEXTAREA" || tag === "INPUT") return;
        const ids = this.state.threads.map(t => t.id);
        if (!ids.length) return;
        const idx = ids.indexOf(this.state.selectedThreadId);
        if (ev.key === "j") {
            this.selectThread(ids[Math.min(ids.length - 1, Math.max(0, idx) + 1)]);
        } else if (ev.key === "k") {
            this.selectThread(ids[Math.max(0, idx < 0 ? 0 : idx - 1)]);
        } else if (ev.key === "e") {
            this.markDone();
        } else if (ev.key === "#") {
            this.markWaiting();
        } else if (ev.key === "r") {
            this.onCompose();
        }
    }

    // ------------------------------------------------------------------
    // Computed
    // ------------------------------------------------------------------
    get selectedThread() {
        return this.state.threads.find(t => t.id === this.state.selectedThreadId) || null;
    }

    get currentFolderLabel() {
        if (this.state.folder.startsWith("label:")) {
            const labelId = parseInt(this.state.folder.slice(6), 10);
            const label = this.state.labels.find(l => l.id === labelId);
            return label ? label.name : _t("Label");
        }
        return FOLDER_LABELS[this.state.folder] || this.state.folder;
    }

    get canReply() {
        const t = this.selectedThread;
        return !!(t && t.source_model && t.source_res_id);
    }
}

registry.category("actions").add("hf_mailbox.view", MailboxView);
