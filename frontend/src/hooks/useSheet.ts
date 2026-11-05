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

/**
 * Состояние листа: движок формул, синхронизация с сервером и WS.
 * Движок изменяемый, поэтому React узнаёт об изменениях через счётчик `version`.
 */
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

    // Очередь и секвенсор живут столько же, сколько таблица; ссылки на загрузчик — через ref,
    // потому что loadSnapshot создаётся после них.
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
                    // Своё событие уже применено локально
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
            redraw();
        } catch (err: any) {
            const status = err.response?.status ?? null;
            setAccessError({
                status,
                message:
                    err.response?.data?.detail ||
                    (status === 403 ? 'Нет доступа к этой таблице' : status === 404 ? 'Таблица не найдена' : 'Не удалось загрузить таблицу'),
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

    // ── операции ──

    const commit = useCallback(
        (result: EngineResult) => {
            if (!result.cells.length && !result.styles.length && !result.meta && !result.structural) return;
            queue.push(result);
            redraw();
        },
        [queue, redraw],
    );

    const guard = useCallback(
        <T,>(action: () => T): T | undefined => {
            if (!canWrite) {
                setNotice('У вас нет прав на редактирование этой таблицы');
                return undefined;
            }
            try {
                return action();
            } catch (err: any) {
                setNotice(err?.message || 'Операция не выполнена');
                return undefined;
            }
        },
        [canWrite],
    );

    const setCell = useCallback((row: number, col: number, raw: string) => guard(() => commit(engine.setRaw(row, col, raw))), [guard, commit, engine]);

    const setMatrix = useCallback(
        (row: number, col: number, matrix: string[][]) => guard(() => commit(engine.setMatrix(row, col, matrix))),
        [guard, commit, engine],
    );

    const clearRange = useCallback((rect: Rect) => guard(() => commit(engine.clearRange(rect))), [guard, commit, engine]);

    const structural = useCallback(
        (op: StructuralOp) =>
            guard(() => {
                const isRows = op.kind.endsWith('rows');
                const extent = engine.extent();
                if (op.kind.startsWith('insert') && (isRows ? extent.rows + op.count > MAX_ROWS : extent.cols + op.count > MAX_COLS)) {
                    throw new Error('Достигнут предел размера листа');
                }
                if (!engine.canApply(op)) throw new Error('Эту операцию выполнить нельзя');
                commit(engine.applyStructural(op));
            }),
        [guard, commit, engine],
    );

    const applyStyle = useCallback((target: StyleTarget, patch: StylePatch) => guard(() => commit(engine.applyStyle(target, patch))), [guard, commit, engine]);

    const setColumnWidth = useCallback(
        (col: number, width: number) => guard(() => commit({cells: [], styles: [], meta: engine.setColumnWidth(col, width)})),
        [guard, commit, engine],
    );

    const setFrozenCols = useCallback((count: number) => guard(() => commit({cells: [], styles: [], meta: engine.setFrozenCols(count)})), [guard, commit, engine]);

    const copyRange = useCallback((rect: Rect) => engine.copy(rect), [engine]);

    const paste = useCallback((row: number, col: number) => guard(() => commit(engine.paste(row, col))), [guard, commit, engine]);

    return {
        engine,
        version,
        loading,
        canWrite,
        saving,
        accessError,
        notice,
        clearNotice: () => setNotice(''),
        setCell,
        setMatrix,
        clearRange,
        structural,
        applyStyle,
        setColumnWidth,
        setFrozenCols,
        copyRange,
        paste,
    };
}
