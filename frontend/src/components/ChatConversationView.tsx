import React, {useEffect, useRef, useState} from "react";
import {getMessages, markChatAsRead, MessageOut, sendMessage} from "../api/chat";
import {ChatSocketEvent} from "../hooks/useChatSocket";
import {colors, rounded, spacing, typography} from "../styles/theme";

interface ChatConversationViewProps {
    interlocutorEmail: string;
    currentUserEmail: string;
    onBack: () => void;
    onClosePanel: () => void;
    incomingEvent: ChatSocketEvent | null;
    onRead: () => void;
}

const ChatConversationView: React.FC<ChatConversationViewProps> = ({
                                                                       interlocutorEmail,
                                                                       currentUserEmail,
                                                                       onBack,
                                                                       onClosePanel,
                                                                       incomingEvent,
                                                                       onRead,
                                                                   }) => {
    const [messages, setMessages] = useState<MessageOut[]>([]);
    const [draft, setDraft] = useState("");
    const [isLoading, setIsLoading] = useState(true);
    const [isSending, setIsSending] = useState(false);
    const [error, setError] = useState("");
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setIsLoading(true);
        setError("");

        getMessages(interlocutorEmail)
            .then((data) => setMessages([...data.items].reverse()))
            .catch((err) => setError(err.response?.data?.detail || "Не удалось загрузить сообщения"))
            .finally(() => setIsLoading(false));

        markChatAsRead(interlocutorEmail)
            .then(onRead)
            .catch((err) => console.error("Не удалось пометить чат прочитанным:", err));
        // onRead — стабильная ссылка (useCallback в ChatProvider), в зависимости не добавляем
        // осознанно, чтобы не перезапускать эффект при каждом обновлении списка диалогов.
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [interlocutorEmail]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({behavior: "smooth"});
    }, [messages]);

    useEffect(() => {
        if (!incomingEvent || incomingEvent.type !== "new_message") return;
        if (incomingEvent.message.sender_email !== interlocutorEmail) return;

        setMessages((prev) => {
            if (prev.some((m) => m.id === incomingEvent.message.id)) return prev;
            return [...prev, incomingEvent.message];
        });

        markChatAsRead(interlocutorEmail)
            .then(onRead)
            .catch(() => {
            });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [incomingEvent, interlocutorEmail]);

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault();
        const content = draft.trim();
        if (!content || isSending) return;

        setDraft("");
        setIsSending(true);
        try {
            const message = await sendMessage(interlocutorEmail, content);
            setMessages((prev) => [...prev, message]);
            onRead();
        } catch (err: any) {
            setError(err.response?.data?.detail || "Не удалось отправить сообщение");
            setDraft(content);
        } finally {
            setIsSending(false);
        }
    };

    return (
        <>
            <div style={styles.header}>
                <button style={styles.backButton} onClick={onBack} aria-label="Назад к списку">
                    ←
                </button>
                <div style={styles.headerAvatar}>{interlocutorEmail.charAt(0).toUpperCase()}</div>
                <h2 style={styles.headerTitle}>{interlocutorEmail}</h2>
                <button style={styles.closeButton} onClick={onClosePanel} aria-label="Закрыть">
                    ✕
                </button>
            </div>

            <div style={styles.messagesArea}>
                {error && <p style={styles.error}>{error}</p>}

                {isLoading ? (
                    <p style={styles.emptyText}>Загрузка...</p>
                ) : messages.length === 0 ? (
                    <p style={styles.emptyText}>Сообщений пока нет — начните переписку</p>
                ) : (
                    messages.map((msg) => {
                        const isMine = msg.sender_email === currentUserEmail;
                        return (
                            <div
                                key={msg.id}
                                style={{...styles.messageRow, justifyContent: isMine ? "flex-end" : "flex-start"}}
                            >
                                <div
                                    style={{
                                        ...styles.messageBubble,
                                        ...(isMine ? styles.messageBubbleMine : styles.messageBubbleTheirs),
                                    }}
                                >
                                    <div style={styles.messageContent}>{msg.content}</div>
                                    <div style={styles.messageTime}>
                                        {new Date(msg.created_at).toLocaleTimeString("ru-RU", {
                                            hour: "2-digit",
                                            minute: "2-digit",
                                        })}
                                    </div>
                                </div>
                            </div>
                        );
                    })
                )}
                <div ref={messagesEndRef}/>
            </div>

            <form onSubmit={handleSend} style={styles.inputArea}>
                <input
                    style={styles.input}
                    type="text"
                    placeholder="Сообщение..."
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    disabled={isSending}
                />
                <button style={styles.sendButton} type="submit" disabled={!draft.trim() || isSending}>
                    ➤
                </button>
            </form>
        </>
    );
};

export default ChatConversationView;

const styles: Record<string, React.CSSProperties> = {
    header: {
        display: "flex",
        alignItems: "center",
        gap: spacing.xs,
        padding: spacing.md,
        background: colors.canvas,
        borderBottom: `1px solid ${colors.hairline}`,
        flexShrink: 0,
    },
    backButton: {
        ...typography.bodyMd,
        background: "transparent",
        border: "none",
        cursor: "pointer",
        color: colors.body,
        padding: spacing.xxs,
        flexShrink: 0,
    },
    headerAvatar: {
        ...typography.bodySmStrong,
        width: 32,
        height: 32,
        borderRadius: rounded.full,
        background: colors.primary,
        color: colors.onPrimary,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
    },
    headerTitle: {
        ...typography.bodyMdStrong,
        margin: 0,
        color: colors.ink,
        flex: 1,
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
    },
    closeButton: {
        ...typography.bodyMd,
        background: "transparent",
        border: "none",
        cursor: "pointer",
        color: colors.mute,
        padding: spacing.xxs,
        flexShrink: 0,
    },
    messagesArea: {
        flex: 1,
        overflowY: "auto",
        padding: spacing.md,
        display: "flex",
        flexDirection: "column",
        gap: spacing.xs,
    },
    error: {
        ...typography.bodySm,
        color: colors.errorDeep,
        padding: spacing.sm,
        background: colors.errorSoft,
        borderRadius: rounded.sm,
        marginBottom: spacing.sm,
    },
    emptyText: {
        ...typography.bodySm,
        textAlign: "center",
        color: colors.mute,
        marginTop: spacing["2xl"],
    },
    messageRow: {
        display: "flex",
    },
    messageBubble: {
        maxWidth: "80%",
        padding: `${spacing.xs}px ${spacing.sm}px`,
        borderRadius: rounded.md,
    },
    messageBubbleMine: {
        background: colors.primary,
        color: colors.onPrimary,
        borderBottomRightRadius: rounded.xs,
    },
    messageBubbleTheirs: {
        background: colors.canvas,
        color: colors.ink,
        border: `1px solid ${colors.hairline}`,
        borderBottomLeftRadius: rounded.xs,
    },
    messageContent: {
        ...typography.bodySm,
        wordBreak: "break-word",
    },
    messageTime: {
        ...typography.caption,
        opacity: 0.7,
        marginTop: spacing.xxs,
        textAlign: "right",
    },
    inputArea: {
        display: "flex",
        gap: spacing.xs,
        padding: spacing.sm,
        background: colors.canvas,
        borderTop: `1px solid ${colors.hairline}`,
        flexShrink: 0,
    },
    input: {
        ...typography.bodySm,
        flex: 1,
        height: 40,
        padding: `0 ${spacing.sm}px`,
        borderRadius: rounded.sm,
        border: `1px solid ${colors.hairline}`,
        background: colors.canvas,
        color: colors.ink,
        boxSizing: "border-box",
    },
    sendButton: {
        width: 40,
        height: 40,
        borderRadius: rounded.sm,
        border: "none",
        background: colors.primary,
        color: colors.onPrimary,
        cursor: "pointer",
        fontSize: 16,
        flexShrink: 0,
    },
};