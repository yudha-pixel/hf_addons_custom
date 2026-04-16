/** @odoo-module **/

import { Component } from "@odoo/owl";

/**
 * Left navigation: system folders + user labels + "Compose" CTA.
 * Props:
 *   - labels: {id, name, color, system_key}[]
 *   - folder: current folder key ("inbox" | "sent" | "waiting" | "followup" | "done" | "label:<id>")
 *   - onFolderChange(folder): callback
 *   - onCompose(): callback for the Compose button
 */
export class MailboxSidebar extends Component {
    static template = "hf_mailbox.MailboxSidebar";
    static props = {
        labels: Array,
        folder: String,
        onFolderChange: Function,
        onCompose: Function,
    };

    static FOLDERS = [
        { key: "inbox",    label: "Inbox",         icon: "fa-inbox" },
        { key: "sent",     label: "Sent",          icon: "fa-paper-plane" },
        { key: "waiting",  label: "Waiting Reply", icon: "fa-hourglass-half" },
        { key: "followup", label: "Follow-up",     icon: "fa-bell" },
        { key: "done",     label: "Done",          icon: "fa-check-circle" },
    ];

    get folders() {
        return this.constructor.FOLDERS;
    }

    isActive(key) {
        return this.props.folder === key;
    }
}
