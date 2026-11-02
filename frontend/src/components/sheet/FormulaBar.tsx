import React, {useEffect, useState} from 'react';
import type {GridSelection} from '@glideapps/glide-data-grid';
import {addressLabel} from '../../sheet/address';
import type {SheetEngine} from '../../sheet/engine';
import {colors, rounded, spacing, typography} from '../../styles/theme';

interface Props {
    /** Движок таблицы: источник значений и формул. Изменяемый, поэтому обновления приходят через `version`. */
    engine: SheetEngine;
    /** Счётчик изменений движка. Меняется при каждом редактировании — заставляет перечитать `draft`. */
    version: number;
    /** Текущее выделение сетки. Из него берётся активная ячейка (`selection.current.cell`). */
    selection: GridSelection;
    /** Есть ли у пользователя права на редактирование. Если `false` — поле ввода заблокировано. */
    canWrite: boolean;
    /** Колбэк применения ввода: вызывается при `Enter`, если значение изменилось. */
    onCommit: (row: number, col: number, raw: string) => void;
}

/**
 * Строка формул (как в Excel/Google Sheets).
 *
 * Показывает адрес активной ячейки и её **сырое** содержимое (формулу, а не результат).
 * Позволяет изменить формулу или значение прямо в поле ввода:
 * - `Enter` — применить (`onCommit`) и убрать фокус;
 * - `Escape` — отменить ввод и вернуть текущее значение из движка.
 *
 * Компонент **не меняет движок сам** — только сообщает наружу через `onCommit`.
 * Локально держит `draft` (черновик ввода) и `focused` (защита от перезаписи
 * во время набора, если данные пришли по WS или сменилась активная ячейка).
 */
const FormulaBar: React.FC<Props> = ({engine, version, selection, canWrite, onCommit}) => {
    /** Активная ячейка как пара [col, row]; `undefined`, если ничего не выбрано. */
    const active = selection.current?.cell;

    /** Черновик поля ввода. Может отличаться от значения в движке, пока пользователь не нажмёт Enter. */
    const [draft, setDraft] = useState('');
    /** `true`, пока поле в фокусе. Защищает `draft` от перезаписи во время набора. */
    const [focused, setFocused] = useState(false);

    const col = active?.[0];
    const row = active?.[1];

    /**
     * Синхронизирует `draft` с текущим значением движка.
     * Срабатывает при смене активной ячейки (`row`/`col`), изменении движка
     * (`version`/`engine`) или потере фокуса (`focused`).
     * Пока пользователь печатает (`focused === true`) — не трогает `draft`.
     */
    useEffect(() => {
        if (focused) return;
        setDraft(row === undefined || col === undefined ? '' : engine.view(row, col).raw);
    }, [engine, version, row, col, focused]);

    /**
     * Применяет введённое значение к активной ячейке через `onCommit`.
     * Ничего не делает, если ячейка не выбрана или значение не изменилось.
     */
    const commit = () => {
        if (row === undefined || col === undefined) return;
        if (draft !== engine.view(row, col).raw) onCommit(row, col, draft);
    };

    return (
        <div style={styles.bar}>
            <div style={styles.address}>
                {row === undefined || col === undefined ? '' : addressLabel(row, col)}
            </div>
            <span style={styles.fx}>ƒx</span>
            <input
                style={styles.input}
                value={draft}
                disabled={!canWrite || row === undefined}
                placeholder="Введите значение или формулу, например =SUM(A1:A10)"
                onChange={(e) => setDraft(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                        commit();
                        (e.target as HTMLInputElement).blur();
                    }
                    if (e.key === 'Escape') {
                        setDraft(row === undefined || col === undefined ? '' : engine.view(row, col).raw);
                        (e.target as HTMLInputElement).blur();
                    }
                }}
            />
        </div>
    );
};

/**
 * Inline-стили строки формул.
 * Вынесены в константу, чтобы не создавать новый объект на каждый рендер.
 */
const styles: Record<string, React.CSSProperties> = {
    bar: {
        display: 'flex', alignItems: 'center', gap: spacing.xs, padding: `${spacing.xxs}px ${spacing.xs}px`,
        background: colors.canvas, border: `1px solid ${colors.hairline}`, borderBottom: 'none',
    },
    address: {
        ...typography.code, width: 64, textAlign: 'center', color: colors.body,
        borderRight: `1px solid ${colors.hairline}`,
    },
    fx: {...typography.caption, color: colors.mute, fontStyle: 'italic'},
    input: {
        ...typography.code, flex: 1, border: `1px solid ${colors.hairline}`, borderRadius: rounded.xs,
        padding: `${spacing.xxs}px ${spacing.xs}px`, outline: 'none', color: colors.ink,
    },
};

export default FormulaBar;