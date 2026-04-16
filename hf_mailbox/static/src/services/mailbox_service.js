/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * hf_mailbox data layer.
 * All components MUST go through this service instead of calling ORM directly,
 * so we can later add caching, batching or bus-driven invalidation in one place.
 */
export const mailboxService = {
    dependencies: ["orm", "action"],
    start(env, { orm, action }) {
        const THREAD_FIELDS = [
            "id", "name", "last_message_date", "last_author_id",
            "last_direction", "message_count", "state", "snippet",
            "label_ids", "source_model", "source_res_id",
        ];
        const MESSAGE_FIELDS = [
            "id", "mail_message_id", "chain_index", "direction",
            "date", "author_id", "email_from", "subject", "body",
        ];
        const LABEL_FIELDS = ["id", "name", "color", "system_key", "user_id"];

        function folderDomain(folder) {
            if (!folder || folder === "inbox") return [["state", "!=", "done"]];
            if (folder === "sent")      return [["last_direction", "=", "outgoing"]];
            if (folder === "waiting")   return [["state", "=", "waiting"]];
            if (folder === "followup")  return [["label_ids.system_key", "=", "followup"]];
            if (folder === "done")      return [["state", "=", "done"]];
            if (folder.startsWith("label:")) {
                return [["label_ids", "in", [parseInt(folder.slice(6), 10)]]];
            }
            return [];
        }

        return {
            folderDomain,

            loadLabels() {
                return orm.searchRead(
                    "hf.mailbox.label",
                    [["active", "=", true]],
                    LABEL_FIELDS,
                    { order: "sequence,name" },
                );
            },

            loadThreads(folder, { limit = 80 } = {}) {
                return orm.searchRead(
                    "hf.mailbox.thread",
                    folderDomain(folder),
                    THREAD_FIELDS,
                    { order: "last_message_date desc", limit },
                );
            },

            loadMessages(threadId) {
                return orm.searchRead(
                    "hf.mailbox.message",
                    [["thread_id", "=", threadId]],
                    MESSAGE_FIELDS,
                    { order: "chain_index asc, date asc" },
                );
            },

            markDone(threadIds) {
                return orm.call("hf.mailbox.thread", "action_mark_done", [threadIds]);
            },
            markWaiting(threadIds) {
                return orm.call("hf.mailbox.thread", "action_mark_waiting", [threadIds]);
            },
            reopen(threadIds) {
                return orm.call("hf.mailbox.thread", "action_reopen", [threadIds]);
            },
            openSource(threadIds) {
                return orm.call("hf.mailbox.thread", "action_open_source", [threadIds]);
            },

            postReply(model, resId, body, { internal = false } = {}) {
                return orm.call(model, "message_post", [[resId]], {
                    body,
                    message_type: "comment",
                    subtype_xmlid: internal ? "mail.mt_note" : "mail.mt_comment",
                });
            },

            /**
             * Open Odoo's standard mail.compose.message wizard in a dialog.
             * Used for the "new email" flow when no conversation is selected.
             * @param {Object} [options] extra context / onClose hook
             * @returns {Promise<any>}
             */
            openComposeWizard({ onClose, context = {} } = {}) {
                return action.doAction(
                    "hf_mailbox.action_hf_mailbox_compose",
                    { onClose, additionalContext: context },
                );
            },
        };
    },
};

registry.category("services").add("hf_mailbox", mailboxService);
