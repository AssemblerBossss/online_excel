import React, {useEffect, useRef, useState} from "react";
import {getMessages, markChatAsRead, MessageOut, sendMessage} from "../api/chat";
import {ChatSocketEvent} from "../hooks/useChatSocket";

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
        gap: 10,
        padding: "16px",
        borderBottom: "1px solid #e2e8f0",
        flexShrink: 0,
    },
    backButton: {
        background: "transparent",
        border: "none",
        fontSize: 18,
        cursor: "pointer",
        color: "#475569",
        padding: 4,
        flexShrink: 0,
    },
    headerAvatar: {
        width: 32,
        height: 32,
        borderRadius: "50%",
        background: "#4CAF50",
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 600,
        fontSize: 14,
        flexShrink: 0,
    },
    headerTitle: {
        margin: 0,
        fontSize: 15,
        color: "#1e293b",
        flex: 1,
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
    },
    closeButton: {
        background: "transparent",
        border: "none",
        fontSize: 16,
        cursor: "pointer",
        color: "#94a3b8",
        padding: 4,
        flexShrink: 0,
    },
    messagesArea: {
        flex: 1,
        overflowY: "auto",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 8,
    },
    error: {
        color: "#ff4757",
        padding: 10,
        background: "#ffe6e6",
        borderRadius: 6,
        marginBottom: 12,
        fontSize: 13,
    },
    emptyText: {
        textAlign: "center",
        color: "#94a3b8",
        marginTop: 30,
        fontSize: 13,
    },
    messageRow: {
        display: "flex",
    },
    messageBubble: {
        maxWidth: "80%",
        padding: "8px 12px",
        borderRadius: 12,
    },
    messageBubbleMine: {
        background: "#4CAF50",
        color: "#fff",
        borderBottomRightRadius: 4,
    },
    messageBubbleTheirs: {
        background: "#fff",
        color: "#1e293b",
        border: "1px solid #e2e8f0",
        borderBottomLeftRadius: 4,
    },
    messageContent: {
        fontSize: 13,
        wordBreak: "break-word",
    },
    messageTime: {
        fontSize: 10,
        opacity: 0.7,
        marginTop: 3,
        textAlign: "right",
    },
    inputArea: {
        display: "flex",
        gap: 8,
        padding: 12,
        borderTop: "1px solid #e2e8f0",
        flexShrink: 0,
    },
    input: {
        flex: 1,
        padding: 10,
        borderRadius: 8,
        border: "1px solid #cbd5e1",
        fontSize: 13,
    },
    sendButton: {
        width: 40,
        borderRadius: 8,
        border: "none",
        background: "#4CAF50",
        color: "#fff",
        cursor: "pointer",
        fontSize: 16,
    },
};