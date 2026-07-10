import api from './axiosInstance';
import {TableRow} from './tables';

export type RowEventType = 'row.created' | 'row.updated' | 'row.deleted';

export interface RowEvent {
    event: RowEventType;
    table_id: number;
    row_id: number;
    actor_id: number;
    row: TableRow | null;
    occurred_at: string;
}

interface WsTicketResponse {
    ticket: string;
    expires_in: number;
}

const WS_BASE_URL =
    import.meta.env.VITE_WS_URL ||
    `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}`;

async function openTableSocket(tableId: number): Promise<WebSocket> {
    // Тикет одноразовый и живёт 30с — берём новый перед каждым подключением
    const {data} = await api.post<WsTicketResponse>('/tables/ws-ticket');
    return new WebSocket(`${WS_BASE_URL}/ws/tables/${tableId}?ticket=${data.ticket}`);
}

/**
 * Подписка на события строк таблицы с автопереподключением (экспоненциальный backoff).
 * Возвращает функцию отписки.
 */
export function subscribeToTableEvents(
    tableId: number,
    onEvent: (event: RowEvent) => void,
): () => void {
    let ws: WebSocket | null = null;
    let closed = false;
    let attempt = 0;
    let reconnectTimer: number | null = null;

    const scheduleReconnect = () => {
        if (closed) return;
        const delay = Math.min(30_000, 1000 * 2 ** attempt++);
        reconnectTimer = window.setTimeout(connect, delay);
    };

    const connect = async () => {
        try {
            ws = await openTableSocket(tableId);
        } catch {
            scheduleReconnect();
            return;
        }
        ws.onopen = () => {
            attempt = 0;
        };
        ws.onmessage = (msg) => onEvent(JSON.parse(msg.data) as RowEvent);
        ws.onclose = () => scheduleReconnect();
    };

    connect();

    return () => {
        closed = true;
        if (reconnectTimer) window.clearTimeout(reconnectTimer);
        if (ws) {
            ws.onclose = null;
            ws.close();
        }
    };
}