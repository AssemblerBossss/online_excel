import {useEffect, useRef, useState} from "react";
import {getWsTicket} from "../api/chat";
import {MessageOut} from "../api/chat";

export interface ChatSocketEvent {
    type: string;
    target_email: string;
    chat_id: string;
    message: MessageOut;
}

const RECONNECT_DELAY_MS = 3000;

function buildWsUrl(ticket: string): string {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/api/chat/ws?ticket=${ticket}`;
}

/**
 * Держит одно WS-соединение живым, пока enabled === true.
 * При разрыве — переподключается, каждый раз запрашивая новый тикет
 * (тикет одноразовый, старый использовать повторно нельзя).
 */
export function useChatSocket(
    onEvent: (event: ChatSocketEvent) => void,
    enabled: boolean = true,
) {
    const [isConnected, setIsConnected] = useState(false);
    const onEventRef = useRef(onEvent);
    onEventRef.current = onEvent;

    useEffect(() => {
        if (!enabled) {
            setIsConnected(false);
            return;
        }

        let isMounted = true;
        let socket: WebSocket | null = null;
        let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

        const connect = async () => {
            if (!isMounted) return;

            let ticket: string;
            try {
                const ticketData = await getWsTicket();
                ticket = ticketData.ticket;
            } catch (err) {
                console.error("Не удалось получить WS-тикет:", err);
                if (isMounted) {
                    reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
                }
                return;
            }

            if (!isMounted) return;

            socket = new WebSocket(buildWsUrl(ticket));

            socket.onopen = () => {
                if (isMounted) setIsConnected(true);
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data) as ChatSocketEvent;
                    onEventRef.current(data);
                } catch (err) {
                    console.error("Не удалось разобрать WS-событие:", err);
                }
            };

            socket.onclose = () => {
                if (!isMounted) return;
                setIsConnected(false);
                reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
            };

            socket.onerror = () => {
                socket?.close();
            };
        };

        connect();

        return () => {
            isMounted = false;
            if (reconnectTimer) clearTimeout(reconnectTimer);
            socket?.close();
        };
    }, [enabled]);

    return {isConnected};
}