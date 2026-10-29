import {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {sheetAPI} from '../api/sheet';
import {subscribeToTableEvents} from '../api/ws';
import {MAX_COLS, MAX_ROWS} from '../sheet/address';
import {SheetEngine, type StyleTarget} from '../sheet/engine';
import {EventSequencer} from '../sheet/sequencer';
import {SyncQueue} from '../sheet/syncQueue';
import type {EngineResult, Rect, SheetEvent, StructuralOp, StylePatch} from '../sheet/types';

export interface AccessError {
    status: number | null;
    message: string;
}

const makeClientId = (): string => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;

export function useSheet(tableId: number) {
    const engine = useMemo(() => new SheetEngine(), [tableId]);
    const clientId = useMemo(makeClientId, [tableId]);
    const layoutRevision = useRef(0);

    const [version, setVersion] = useState(0);
    const [loading, setLoading] = useState(true);
    const [canWrite, setCanWrite] = useState(false);
    const [saving, setSaving] = useState(false);
    const [notice, setNotice] = useState('');
    const [accessError, setAccessError] = useState<AccessError | null>(null);

    const redraw = useCallback(() => setVersion((v) => v + 1), []);

    const loadRef = useRef<() => Promise<void>>(async () => {});

    const queue = useMemo(
        () =>
            new SyncQueue({
                send: async (batch) => {
                    const result = await sheetAPI.applyBatch(tableId, {
                        client_id: clientId,
                        base_layout_revision: layoutRevision.current,
                        ...batch,
                    });
                    layoutRevision.current = Math.max(layoutRevision.current, result.layout_revision);
                },
                onConflict: () => {
                    setNotice('Структуру листа изменил другой пользователь — данные обновлены, повторите действие');
                    void loadRef.current();
                },
                onError: (error) => {
                    console.error('sheet save error', error);
                    setNotice('Не удалось сохранить изменения — данные обновлены с сервера');
                    void loadRef.current();
                },
                onBusyChange: setSaving,
            }),
        [tableId, clientId],
    );

    const sequencer = useMemo(
        () =>
            new EventSequencer(
                (event: SheetEvent) => {
                    if (event.kind === 'reload') {
                        // Большой пакет: тело в событие не вошло. Свой же пакет перечитывать не нужно
                        if (event.client_id !== clientId) void loadRef.current();
                        return;
                    }
                    layoutRevision.current = Math.max(layoutRevision.current, event.layout_revision);
                    if (event.client_id !== clientId) {
                        engine.applyRemote(event);
                        redraw();
                    }
                },
                () => void loadRef.current(),
            ),
        [engine, clientId, redraw],
    );

    const loadSnapshot = useCallback(async () => {
        try {
            const snapshot = await sheetAPI.getSheet(tableId);
            queue.clear();
            const repair = engine.load(snapshot);
            layoutRevision.current = snapshot.layout_revision;
            sequencer.reset(snapshot.revision);
            setCanWrite(snapshot.can_write);
            setAccessError(null);
            // Значения, которых не было на сервере (импорт из Excel и т.п.), досчитаны движком — сохраняем
            if (snapshot.can_write && repair.length) queue.push({cells: repair, styles: []});
            redraw;
        } catch (err: any) {
            const status = err.response?.status ?? null;
            setAccessError({
                status,
                message:
                    err.response?.data?.detail ||  (status === 403 ? 'Нет доступа к этой таблице' : status === 404 ? 'Таблица не найдена' : 'Не удалось загрузить таблицу')
            });
        } finally {
            setLoading(false);
        }

    }, [tableId, engine, queue, sequencer, redraw]);
    loadRef.current = loadSnapshot;

    useEffect(() => {
        setLoading(true);
        // Сначала подписка, потом снимок: события, пришедшие во время загрузки, секвенсор придержит
        const unsubscribe = subscribeToTableEvents(tableId, (event) => sequencer.push(event), () => void loadSnapshot());
        void loadSnapshot();
        return () => {
            unsubscribe();
            sequencer.dispose();
            // engine.destroy() не зовём: в StrictMode эффект отрабатывает дважды на одном и том же движке
        };
    }, [tableId, engine, sequencer, loadSnapshot]);


    




}
