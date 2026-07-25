import api from "./axiosInstance";

export interface DialogOut {
    interlocutor_email: string;
    last_message_content: string | null;
    last_message_at: string | null;
    unread_count: number;
}

export interface MessageOut {
    id: string;
    sender_email: string;
    content: string;
    created_at: string;
    is_read: boolean;
}

export interface PaginatedMessages {
    items: MessageOut[];
    total: number;
    page: number | null;
    cursor: string | null;
}

export interface WsTicket {
    ticket: string;
    expires_in: number;
}

export interface UserSuggestion {
    email: string;
}

/**
 * Список диалогов текущего пользователя с последним сообщением
 * и счётчиком непрочитанных по каждому собеседнику.
 */
export const getDialogs = async (): Promise<DialogOut[]> => {
    const response = await api.get("/chat/users");
    return response.data;
};

/**
 * История переписки с конкретным собеседником.
 * Бэкенд отдаёт сообщения новыми сверху (для пагинации) —
 * порядок для отображения в чате разворачивается на стороне UI.
 */
export const getMessages = async (
    interlocutorEmail: string,
    limit: number = 30,
    offset: number = 0,
): Promise<PaginatedMessages> => {
    const response = await api.get(
        `/chat/messages/${encodeURIComponent(interlocutorEmail)}`,
        {params: {limit, offset}},
    );
    return response.data;
};

/**
 * Отправляет сообщение. Чат между пользователями создаётся автоматически
 * при первом сообщении — отдельного эндпоинта "создать чат" не требуется.
 */
export const sendMessage = async (
    receiverEmail: string,
    content: string,
): Promise<MessageOut> => {
    const response = await api.post("/chat/messages", {
        receiver_email: receiverEmail,
        content,
    });
    return response.data;
};

/**
 * Сбрасывает счётчик непрочитанных и помечает входящие сообщения
 * в этом диалоге как прочитанные.
 */
export const markChatAsRead = async (interlocutorEmail: string): Promise<void> => {
    await api.patch(`/chat/messages/${encodeURIComponent(interlocutorEmail)}/read`);
};

/**
 * Одноразовый короткоживущий тикет для WS-подключения.
 * Браузерный WebSocket не умеет передавать заголовок Authorization,
 * поэтому JWT обменивается на тикет через обычный REST-запрос,
 * а сам WS-хендшейк аутентифицируется уже тикетом (см. useChatSocket).
 */
export const getWsTicket = async (): Promise<WsTicket> => {
    const response = await api.post("/chat/ws-ticket");
    return response.data;
};


/**
 * Поиск пользователей по префиксу email для автодополнения.
 * Backend: ES (основной) → PG (fallback).
 */
export const searchUsers = async (
    query: string,
    limit: number = 5,
): Promise<UserSuggestion[]> => {
    const  response = await api.get("/chat/users/search", {params: {q: query, limit}});

    return response.data;
}

