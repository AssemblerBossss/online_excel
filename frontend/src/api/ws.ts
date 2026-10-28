import { SheetEvent } from '../sheet/types';
import api from './axiosInstance';


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
* Подписка на события листа с автопереподключением (экспоненциальный backoff).
* onReconnect вызывается при каждом ПОВТОРНОМ подключении: за время обрыва
* могли пропасть события, поэтому клиент перечитывает снимок листа.
*/
export function subscribeToTableEvents(
    tableId: number,
    onEvent: (event: SheetEvent) => void,
    onReconnect?: () => void,
): () => void {
    let ws: WebSocket | null = null;
    let closed = false;
    let attempt = 0;
    let reconnectTimer: number | null = null;
    let wasConnected = false;

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
            if (wasConnected) onReconnect?.();
            wasConnected = true;
        };
        ws.onmessage = (msg) => onEvent(JSON.parse(msg.data) as SheetEvent);
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