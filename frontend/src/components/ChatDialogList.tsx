import React, {useState} from "react";
import {DialogOut} from "../api/chat";

interface ChatDialogListProps {
    dialogs: DialogOut[];
    onSelect: (email: string) => void;
    onClose: () => void;
}

function formatTime(iso: string | null): string {
    if (!iso) return "";
    const date = new Date(iso);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    return isToday
        ? date.toLocaleTimeString("ru-RU", {hour: "2-digit", minute: "2-digit"})
        : date.toLocaleDateString("ru-RU", {day: "2-digit", month: "2-digit"});
}

function isValidEmail(value: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

const ChatDialogList: React.FC<ChatDialogListProps> = ({dialogs, onSelect, onClose}) => {
    const [newChatEmail, setNewChatEmail] = useState("");
    const [formError, setFormError] = useState("");

    const handleStartChat = (e: React.FormEvent) => {
        e.preventDefault();
        const email = newChatEmail.trim().toLowerCase();

        if (!email) return;

        if (!isValidEmail(email)) {
            setFormError("Введите корректный email");
            return;
        }

        setFormError("");
        onSelect(email);
        setNewChatEmail("");
    };

    return (
        <>
            <div style={styles.header}>
        <h2 style={styles.headerTitle}>Чаты</h2>
            <button style={styles.closeButton} onClick={onClose} aria-label="Закрыть">
                    ✕
                </button>
                </div>

                <form onSubmit={handleStartChat} style={styles.newChatForm}>
    <div style={styles.newChatInputWrapper}>
    <input
        style={styles.newChatInput}
    type="email"
    placeholder="Email собеседника"
    value={newChatEmail}
    onChange={(e) => {
        setNewChatEmail(e.target.value);
        if (formError) setFormError("");
    }}
    />
    {formError && <span style={styles.formError}>{formError}</span>}
        </div>
        <button style={styles.newChatButton} type="submit" aria-label="Начать чат">
                    →
                </button>
                </form>

                <div style={styles.list}>
        {dialogs.length === 0 ? (
                <p style={styles.emptyText}>Пока нет диалогов — начните первый выше</p>
    ) : (
        dialogs.map((dialog) => (
            <div
                key={dialog.interlocutor_email}
        style={styles.dialogItem}
        onClick={() => onSelect(dialog.interlocutor_email)}
        onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = "#eef2f7";
    }}
        onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = "transparent";
    }}
    >
        <div style={styles.avatar}>
            {dialog.interlocutor_email.charAt(0).toUpperCase()}
            </div>
            <div style={styles.dialogInfo}>
    <div style={styles.dialogTopRow}>
    <span style={styles.dialogEmail}>{dialog.interlocutor_email}</span>
        <span style={styles.dialogTime}>{formatTime(dialog.last_message_at)}</span>
    </div>
    <div style={styles.dialogBottomRow}>
    <span
        style={{
    ...styles.dialogPreview,
    ...(dialog.unread_count > 0 ? styles.dialogPreviewUnread : {}),
    }}
    >
        {dialog.last_message_content || "Нет сообщений"}
        </span>
        {dialog.unread_count > 0 && (
            <span style={styles.unreadBadge}>{dialog.unread_count}</span>
        )}
        </div>
        </div>
        </div>
    ))
    )}
        </div>
        </>
    );
    };

    export default ChatDialogList;

    const styles: Record<string, React.CSSProperties> = {
        header: {
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "16px 16px 16px 20px",
            borderBottom: "1px solid #e2e8f0",
            flexShrink: 0,
        },
        headerTitle: {
            margin: 0,
            fontSize: 18,
            color: "#1e293b",
        },
        closeButton: {
            background: "transparent",
            border: "none",
            fontSize: 18,
            cursor: "pointer",
            color: "#94a3b8",
            padding: 4,
        },
        newChatForm: {
            display: "flex",
            alignItems: "flex-start",
            gap: 8,
            padding: 16,
            flexShrink: 0,
        },
        newChatInputWrapper: {
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: 4,
        },
        newChatInput: {
            width: "100%",
            padding: 10,
            borderRadius: 8,
            border: "1px solid #cbd5e1",
            fontSize: 13,
            boxSizing: "border-box",
        },
        formError: {
            fontSize: 11,
            color: "#ff4757",
        },
        newChatButton: {
            width: 40,
            height: 38,
            borderRadius: 8,
            border: "none",
            background: "#4CAF50",
            color: "#fff",
            fontWeight: 600,
            cursor: "pointer",
            fontSize: 16,
            flexShrink: 0,
        },
        list: {
            flex: 1,
            overflowY: "auto",
            padding: "0 8px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 4,
        },
        emptyText: {
            textAlign: "center",
            color: "#94a3b8",
            marginTop: 40,
            padding: "0 16px",
            fontSize: 13,
        },
        dialogItem: {
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: 10,
            borderRadius: 10,
            cursor: "pointer",
            transition: "background-color 0.15s ease",
        },
        avatar: {
            width: 40,
            height: 40,
            borderRadius: "50%",
            background: "#4CAF50",
            color: "#fff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 600,
            flexShrink: 0,
        },
        dialogInfo: {
            flex: 1,
            minWidth: 0,
        },
        dialogTopRow: {
            display: "flex",
            justifyContent: "space-between",
            alignItems: "baseline",
        },
        dialogEmail: {
            fontWeight: 600,
            fontSize: 14,
            color: "#1e293b",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
        },
        dialogTime: {
            fontSize: 11,
            color: "#94a3b8",
            flexShrink: 0,
            marginLeft: 6,
        },
        dialogBottomRow: {
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 2,
        },
        dialogPreview: {
            fontSize: 13,
            color: "#64748b",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
        },
        dialogPreviewUnread: {
            color: "#1e293b",
            fontWeight: 600,
        },
        unreadBadge: {
            background: "#4CAF50",
            color: "#fff",
            borderRadius: 10,
            fontSize: 11,
            fontWeight: 600,
            padding: "2px 7px",
            marginLeft: 6,
            flexShrink: 0,
        },
    };