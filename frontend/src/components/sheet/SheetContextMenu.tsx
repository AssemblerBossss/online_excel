import React, {useEffect} from 'react';
import type {StructuralOp} from '../../sheet/types';
import {colors, rounded, shadowLevel5, spacing, typography} from '../../styles/theme';
import type {ContextMenuState} from './SheetGrid';

const styles: Record<string, React.CSSProperties> = {
    menu: {
        position: 'fixed', zIndex: 1000, minWidth: 220, display: 'flex', flexDirection: 'column',
        background: colors.canvas, borderRadius: rounded.sm, boxShadow: shadowLevel5, padding: spacing.xxs,
    },
    item: {
        ...typography.bodySm, textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer',
        padding: `${spacing.xxs}px ${spacing.xs}px`, borderRadius: rounded.xs, color: colors.ink,
    },
};


interface Props {
    menu: ContextMenuState;
    /** Сколько строк / колонок выделено вокруг ячейки, по которой кликнули */
    rowSpan: {index: number, count: number};
    colSpan: {index: number, count: number};
    onStructural: (op: StructuralOp) => void;
    onClear: () => void;
    onClose: () => void;
}

const SheetContextMenu: React.FC<Props> = ({menu, rowSpan, colSpan, onStructural, onClear, onClose}) => {
    useEffect(() => {
        const close = () => onClose();
        window.addEventListener('click', close);
        window.addEventListener('scroll', close, true);
        return () => {
            window.removeEventListener('click', close);
            window.removeEventListener('scroll', close, true);
        }
    }, [onClose]);

    const onRow = menu.row >= 0;
    const rows = rowSpan.count;
    const cols = rowSpan.count;
    const items: {label: string; action: () => void}[] = [
        ...(onRow
            ? [
                  {label: `Вставить ${rows} стр. выше`, action: () => onStructural({kind: 'insert_rows', index: rowSpan.index, count: rows})},
                  {label: `Вставить ${rows} стр. ниже`, action: () => onStructural({kind: 'insert_rows', index: rowSpan.index + rows, count: rows})},
                  {label: `Удалить строки (${rows})`, action: () => onStructural({kind: 'delete_rows', index: rowSpan.index, count: rows})},
              ]
            : []),
        {label: `Вставить ${cols} кол. слева`, action: () => onStructural({kind: 'insert_cols', index: colSpan.index, count: cols})},
        {label: `Вставить ${cols} кол. справа`, action: () => onStructural({kind: 'insert_cols', index: colSpan.index + cols, count: cols})},
        {label: `Удалить колонки (${cols})`, action: () => onStructural({kind: 'delete_cols', index: colSpan.index, count: cols})},
        {label: 'Очистить содержимое', action: onClear},
    ];

    return (
        <div style={{...styles.menu, left: menu.x, top: menu.y}} onContextMenu={(e) => e.preventDefault()}>
            {items.map((item) => (
                <button key={item.label} style={styles.item} onClick={item.action}>{item.label}</button>
            ))}
        </div>
    )
}
export default SheetContextMenu;

