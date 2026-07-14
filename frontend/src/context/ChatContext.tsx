import React, {createContext, useCallback, useContext, useEffect, useMemo, useState} from "react";
import {useLocation, useSearchParams} from "react-router-dom";
import {DialogOut, getDialogs} from "../api/chat";
import {getUserProfile} from "../api/users";
import {ChatSocketEvent, useChatSocket} from "../hooks/useChatSocket";

const CHAT_QUERY_PARAM = "chat";

// На этих страницах пользователь ещё не аутентифицирован —
// не открываем WS и не дёргаем защищённые эндпоинты вхолостую.
const PUBLIC_PATHS = ["/login", "/register"];

interface ChatContextValue {
    currentUserEmail: string;
    dialogs: DialogOut[];
    unreadTotal: number;
    lastEvent: ChatSocketEvent | null;
    isPanelOpen: boolean;
    activeEmail: string | null;
    openPanel: () => void;
    closePanel: () => void;
    openConversation: (email: string) => void;
    backToList: () => void;
    refreshDialogs: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export const useChat = (): ChatContextValue => {
    const ctx = useContext(ChatContext);
    if (!ctx) {
        throw new Error("useChat должен использоваться внутри ChatProvider");
    }
    return ctx;
};

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({children}) => {
    const location = useLocation();
    const [searchParams, setSearchParams] = useSearchParams();

    const isPublicPage = PUBLIC_PATHS.includes(location.pathname);
    const activeEmail = searchParams.get(CHAT_QUERY_PARAM);

    const [currentUserEmail, setCurrentUserEmail] = useState("");
    const [dialogs, setDialogs] = useState<DialogOut[]>([]);
    const [isPanelOpen, setIsPanelOpen] = useState(false);
    const [lastEvent, setLastEvent] = useState<ChatSocketEvent | null>(null);

    // На публичных страницах чистим состояние — иначе после логаута под другим
    // аккаунтом в той же вкладке можно на секунду увидеть чужие диалоги.
    useEffect(() => {
        if (isPublicPage) {
            setDialogs([]);
            setCurrentUserEmail("");
            setLastEvent(null);
        }
    }, [isPublicPage]);

    useEffect(() => {
        if (isPublicPage) return;
        getUserProfile()
            .then((profile) => setCurrentUserEmail(profile.email))
            .catch((err) => console.error("Не удалось получить профиль для чата:", err));
    }, [isPublicPage]);

    const refreshDialogs = useCallback(() => {
        if (isPublicPage) return;
        getDialogs()
            .then(setDialogs)
            .catch((err) => console.error("Не удалось загрузить диалоги:", err));
    }, [isPublicPage]);

    useEffect(() => {
        refreshDialogs();
    }, [refreshDialogs]);

    // Если в URL уже есть ?chat=..., значит панель должна быть открыта сразу —
    // например, пользователь перезагрузил страницу с открытой перепиской
    // или перешёл по прямой ссылке.
    useEffect(() => {
        if (activeEmail) setIsPanelOpen(true);
    }, [activeEmail]);

    const handleSocketEvent = useCallback((event: ChatSocketEvent) => {
        setLastEvent(event);
        refreshDialogs();
    }, [refreshDialogs]);

    // Единственное WS-соединение на всё приложение. Живёт, пока пользователь
    // залогинен, независимо от того, какая страница сейчас открыта —
    // ChatProvider смонтирован снаружи <Routes> и не размонтируется при навигации.
    useChatSocket(handleSocketEvent, !isPublicPage);

    const openPanel = useCallback(() => {
        setIsPanelOpen(true);
    }, []);

    const closePanel = useCallback(() => {
        setIsPanelOpen(false);
        setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.delete(CHAT_QUERY_PARAM);
            return next;
        }, {replace: true});
    }, [setSearchParams]);

    const openConversation = useCallback((email: string) => {
        setIsPanelOpen(true);
        setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.set(CHAT_QUERY_PARAM, email);
            return next;
        }, {replace: true});
    }, [setSearchParams]);

    const backToList = useCallback(() => {
        setSearchParams((prev) => {
            const next = new URLSearchParams(prev);
            next.delete(CHAT_QUERY_PARAM);
            return next;
        }, {replace: true});
    }, [setSearchParams]);

    const unreadTotal = useMemo(
        () => dialogs.reduce((sum, d) => sum + d.unread_count, 0),
        [dialogs],
    );

    const value: ChatContextValue = {
        currentUserEmail,
        dialogs,
        unreadTotal,
        lastEvent,
        isPanelOpen: isPanelOpen && !isPublicPage,
        activeEmail,
        openPanel,
        closePanel,
        openConversation,
        backToList,
        refreshDialogs,
    };

    return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
};