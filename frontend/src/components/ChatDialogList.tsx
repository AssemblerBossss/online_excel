import React, { useEffect, useRef, useState } from "react";
import { DialogOut, searchUsers, UserSuggestion } from "../api/chat";
import { colors, rounded, shadowLevel5, spacing, typography } from "../styles/theme";

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
        ? date.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" })
        : date.toLocaleDateString("ru-RU", { day: "2-digit", month: "2-digit" });
}

function isValidEmail(value: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 300;
const MAX_SUGGESTIONS = 5;

const ChatDialogList: React.FC<ChatDialogListProps> = ({ dialogs, onSelect, onClose }) => {
    const [newChatEmail, setNewChatEmail] = useState("");
    const [formError, setFormError] = useState("");

    // Состояния для автодополнения
    const [suggestions, setSuggestions] = useState<UserSuggestion[]>([]);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const [isSearching, setIsSearching] = useState(false);

    // Клиентский кэш: query → results
    const cacheRef = useRef<Map<string, UserSuggestion[]>>(new Map());

    // Debounce-поиск с кэшем
    useEffect(() => {
        const query = newChatEmail.trim();

        if (query.length < MIN_QUERY_LENGTH) {
            setSuggestions([]);
            setShowSuggestions(false);
            return;
        }

        const cacheKey = query.toLowerCase();
        if (cacheRef.current.has(cacheKey)) {
            const cached = cacheRef.current.get(cacheKey)!;
            setSuggestions(cached);
            setShowSuggestions(cached.length > 0);
            return;
        }

        let cancelled = false;
        const timer = setTimeout(async () => {
            setIsSearching(true);
            try {
                const results = await searchUsers(query, MAX_SUGGESTIONS);
                if (cancelled) return;
                cacheRef.current.set(cacheKey, results);
                setSuggestions(results);
                setShowSuggestions(results.length > 0);
            } catch (err) {
                console.error("Ошибка поиска пользователей:", err);
                if (!cancelled) {
                    setSuggestions([]);
                    setShowSuggestions(false);
                }
            } finally {
                if (!cancelled) setIsSearching(false);
            }
        }, DEBOUNCE_MS);

        return () => {
            cancelled = true;
            clearTimeout(timer);
        };
    }, [newChatEmail]);

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
        setSuggestions([]);
        setShowSuggestions(false);
    };

    const handleSelectSuggestion = (email: string) => {
        setNewChatEmail(email);
        setSuggestions([]);
        setShowSuggestions(false);
        setFormError("");
        // Сразу открываем чат с выбранным пользователем
        onSelect(email);
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
                    <div style={styles.inputWithSuggestions}>
                        <input
                            style={styles.newChatInput}
                            type="email"
                            placeholder="Email собеседника"
                            value={newChatEmail}
                            onChange={(e) => {
                                setNewChatEmail(e.target.value);
                                if (formError) setFormError("");
                            }}
                            onFocus={() => {
                                if (suggestions.length > 0) setShowSuggestions(true);
                            }}
                            onBlur={() => {
                                // Задержка, чтобы успел сработать onMouseDown на подсказке
                                setTimeout(() => setShowSuggestions(false), 150);
                            }}
                            autoComplete="off"
                        />
                        {isSearching && <div style={styles.inputSpinner} />}
                        {showSuggestions && suggestions.length > 0 && (
                            <div style={styles.suggestionsDropdown}>
                                {suggestions.map((s) => (
                                    <div
                                        key={s.email}
                                        style={styles.suggestionItem}
                                        onMouseDown={(e) => {
                                            e.preventDefault(); // Предотвращаем blur
                                            handleSelectSuggestion(s.email);
                                        }}
                                        onMouseEnter={(e) => {
                                            e.currentTarget.style.backgroundColor = colors.canvasSoft2;
                                        }}
                                        onMouseLeave={(e) => {
                                            e.currentTarget.style.backgroundColor = "transparent";
                                        }}
                                    >
                                        <div style={styles.suggestionAvatar}>
                                            {s.email.charAt(0).toUpperCase()}
                                        </div>
                                        <span style={styles.suggestionEmail}>{s.email}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
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
                                e.currentTarget.style.backgroundColor = colors.canvasSoft2;
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
        padding: `${spacing.md}px ${spacing.md}px ${spacing.md}px ${spacing.lg}px`,
        background: colors.canvas,
        borderBottom: `1px solid ${colors.hairline}`,
        flexShrink: 0,
    },
    headerTitle: {
        ...typography.displaySm,
        margin: 0,
        color: colors.ink,
    },
    closeButton: {
        ...typography.bodyMd,
        background: "transparent",
        border: "none",
        cursor: "pointer",
        color: colors.mute,
        padding: spacing.xxs,
    },
    newChatForm: {
        display: "flex",
        alignItems: "flex-start",
        gap: spacing.xs,
        padding: spacing.md,
        background: colors.canvas,
        borderBottom: `1px solid ${colors.hairline}`,
        flexShrink: 0,
    },
    newChatInputWrapper: {
        flex: 1,
        display: "flex",
        flexDirection: "column",
        gap: spacing.xxs,
    },
    inputWithSuggestions: {
        position: "relative",
    },
    newChatInput: {
        ...typography.bodySm,
        width: "100%",
        height: 40,
        padding: `0 ${spacing.sm}px`,
        borderRadius: rounded.sm,
        border: `1px solid ${colors.hairline}`,
        background: colors.canvas,
        color: colors.ink,
        boxSizing: "border-box",
    },
    inputSpinner: {
        position: "absolute",
        right: spacing.sm,
        top: "50%",
        transform: "translateY(-50%)",
        width: 14,
        height: 14,
        border: `2px solid ${colors.hairline}`,
        borderTop: `2px solid ${colors.primary}`,
        borderRadius: rounded.full,
        animation: "spin 1s linear infinite",
    },
    suggestionsDropdown: {
        position: "absolute",
        top: "calc(100% + 4px)",
        left: 0,
        right: 0,
        background: colors.canvas,
        borderRadius: rounded.sm,
        boxShadow: shadowLevel5,
        zIndex: 20,
        overflow: "hidden",
        border: `1px solid ${colors.hairline}`,
    },
    suggestionItem: {
        display: "flex",
        alignItems: "center",
        gap: spacing.xs,
        padding: `${spacing.xs}px ${spacing.sm}px`,
        cursor: "pointer",
        borderBottom: `1px solid ${colors.hairline}`,
        transition: "background-color 0.1s ease",
    },
    suggestionAvatar: {
        ...typography.caption,
        width: 24,
        height: 24,
        borderRadius: rounded.full,
        background: colors.primary,
        color: colors.onPrimary,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        fontWeight: 600,
    },
    suggestionEmail: {
        ...typography.bodySm,
        color: colors.ink,
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
    },
    formError: {
        ...typography.caption,
        color: colors.errorDeep,
    },
    newChatButton: {
        width: 40,
        height: 40,
        borderRadius: rounded.sm,
        border: "none",
        background: colors.primary,
        color: colors.onPrimary,
        fontWeight: 600,
        cursor: "pointer",
        fontSize: 16,
        flexShrink: 0,
    },
    list: {
        flex: 1,
        overflowY: "auto",
        padding: `0 ${spacing.xs}px ${spacing.md}px`,
        display: "flex",
        flexDirection: "column",
        gap: spacing.xxs,
    },
    emptyText: {
        ...typography.bodySm,
        textAlign: "center",
        color: colors.mute,
        marginTop: spacing["3xl"],
        padding: `0 ${spacing.md}px`,
    },
    dialogItem: {
        display: "flex",
        alignItems: "center",
        gap: spacing.xs,
        padding: spacing.sm,
        borderRadius: rounded.sm,
        cursor: "pointer",
        transition: "background-color 0.15s ease",
    },
    avatar: {
        ...typography.bodySmStrong,
        width: 40,
        height: 40,
        borderRadius: rounded.full,
        background: colors.primary,
        color: colors.onPrimary,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
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
        ...typography.bodySmStrong,
        color: colors.ink,
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
    },
    dialogTime: {
        ...typography.caption,
        color: colors.mute,
        flexShrink: 0,
        marginLeft: spacing.xxs,
    },
    dialogBottomRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginTop: 2,
    },
    dialogPreview: {
        ...typography.bodySm,
        color: colors.body,
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
    },
    dialogPreviewUnread: {
        color: colors.ink,
        fontWeight: 600,
    },
    unreadBadge: {
        ...typography.caption,
        background: colors.primary,
        color: colors.onPrimary,
        borderRadius: rounded.full,
        fontWeight: 600,
        padding: `2px ${spacing.xs}px`,
        marginLeft: spacing.xxs,
        flexShrink: 0,
    },
};