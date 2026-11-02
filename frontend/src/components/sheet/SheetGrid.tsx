import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {
    CompactSelection,
    DataEditor,
    GridCellKind,
    type DataEditorRef,
    type EditableGridCell,
    type GridCell,
    type GridColumn,
    type GridSelection,
    type Item,
    type Rectangle,
    type Theme,
} from '@glideapps/glide-data-grid';
import '@glideapps/glide-data-grid/dist/index.css';
import {colToLetters, DEFAULT_COLS, DEFAULT_ROWS, MAX_COLS, MAX_ROWS} from '../../sheet/address';
import type {SheetEngine} from '../../sheet/engine';
import type {CellStyle, Rect} from '../../sheet/types';
import {colors} from '../../styles/theme';

const ROW_HEIGHT = 24;
const GROW_ROWS = 500;
const GROW_COLS = 10;
const DEFAULT_COL_WIDTH = 100;

const baseTheme: Partial<Theme> = {
    accentColor: colors.link,
    accentLight: colors.linkBgSoft,
    textDark: colors.ink,
    bgCell: colors.canvas,
    bgHeader: colors.canvasSoft,
    borderColor: colors.hairline,
    fontFamily: "'Geist', Inter, system-ui, sans-serif",
    baseFontStyle: '13px',
    headerFontStyle: '600 12px',
};

function cellTheme(style: CellStyle | undefined, isError: boolean): Partial<Theme> | undefined {
    if (!style && !isError) return undefined;
    const theme: Partial<Theme> = {};
    if (style?.bg) theme.bgCell = style.bg;
    if (style?.fg) theme.textDark = style.fg;
    if (isError) theme.textDark = colors.errorDeep;
    if (style?.bold || style?.italic) {
        theme.baseFontStyle = `${style.italic ? 'italic ' : ''}${style.bold ? 'bold ' : ''}13px`;
    }
    return theme;
}

export interface ContextMenuState {
    x: number;
    y: number;
    row: number;
    col: number;
}

interface Props {
    engine: SheetEngine;
    /** Меняется при каждом изменении движка: заставляет сетку перерисоваться */
    version: number;
    canWrite: boolean;
    selection: GridSelection;
    onSelectionChange: (selection: GridSelection) => void;
    onEdit: (row: number, col: number, raw: string) => void;
    onPasteText: (row: number, col: number, matrix: string[][]) => void;
    onPasteInternal: (row: number, col: number) => void;
    onCopy: (rect: Rect) => void;
    onClear: (selection: GridSelection) => void;
    onColumnResize: (col: number, width: number) => void;
    onContextMenu: (menu: ContextMenuState) => void;
}

const tsv = (matrix: readonly (readonly string[])[]): string => matrix.map((line) => line.join('\t')).join('\n');

const SheetGrid: React.FC<Props> = ({
    engine, version, canWrite, selection, onSelectionChange, onEdit, onPasteText, onPasteInternal,
    onCopy, onClear, onColumnResize, onContextMenu,
}) => {
    const gridRef = useRef<DataEditorRef>(null);
    const lastCopyText = useRef<string | null>(null);

    // Сколько строк/колонок показываем: занятая область + запас; растёт при прокрутке к краю
    const [size, setSize] = useState({rows: DEFAULT_ROWS, cols: DEFAULT_COLS});
    useEffect(() => {
        const extent = engine.extent();
        setSize((prev) => ({
            rows: Math.min(MAX_ROWS, Math.max(prev.rows, extent.rows + 100)),
            cols: Math.min(MAX_COLS, Math.max(prev.cols, extent.cols + 5)),
        }));
    }, [engine, version]);

    // Ширину колонок меняем «вживую» локально и отправляем на сервер один раз — по окончании перетаскивания
    const [liveWidths, setLiveWidths] = useState<Record<number, number>>({});

    const columns = useMemo<GridColumn[]>(
        () =>
            Array.from({length: size.cols}, (_, col) => ({
                id: String(col),
                title: colToLetters(col),
                width: liveWidths[col] ?? engine.meta.col_widths?.[col] ?? DEFAULT_COL_WIDTH,
            })),
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [size.cols, liveWidths, engine, version],
    );

    const getCellContent = useCallback(
        ([col, row]: Item): GridCell => {
            const view = engine.view(row, col);
            const align = view.style?.halign ?? (view.isNumber ? 'right' : 'left');
            return {
                kind: GridCellKind.Text,
                allowOverlay: canWrite,
                readonly: !canWrite,
                // data — то, что попадёт в редактор (формула), displayData — то, что видно в ячейке
                data: view.raw,
                displayData: view.text,
                copyData: view.text,
                contentAlign: align,
                allowWrapping: view.style?.wrap,
                themeOverride: cellTheme(view.style, view.isError),
            };
        },
        // version нужен, чтобы сетка перечитала ячейки после изменения движка
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [engine, canWrite, version],
    );

    const onCellEdited = useCallback(
        ([col, row]: Item, value: EditableGridCell) => {
            if (value.kind === GridCellKind.Text) onEdit(row, col, value.data);
        },
        [onEdit],
    );

    const onVisibleRegionChanged = useCallback((range: Rectangle) => {
        setSize((prev) => {
            const needRows = range.y + range.height > prev.rows - 30;
            const needCols = range.x + range.width > prev.cols - 3;
            if (!needRows && !needCols) return prev;
            return {
                rows: needRows ? Math.min(MAX_ROWS, prev.rows + GROW_ROWS) : prev.rows,
                cols: needCols ? Math.min(MAX_COLS, prev.cols + GROW_COLS) : prev.cols,
            };
        });
    }, []);

    const selectedRect = (): Rect | null => {
        const range = selection.current?.range;
        return range ? {x: range.x, y: range.y, width: range.width, height: range.height} : null;
    };

    return (
        <DataEditor
            ref={gridRef}
            columns={columns}
            rows={size.rows}
            getCellContent={getCellContent}
            onCellEdited={onCellEdited}
            gridSelection={selection}
            onGridSelectionChange={onSelectionChange}
            onVisibleRegionChanged={onVisibleRegionChanged}
            theme={baseTheme}
            rowHeight={ROW_HEIGHT}
            headerHeight={26}
            rowMarkers="number"
            freezeColumns={engine.meta.frozen_cols ?? 0}
            smoothScrollX
            smoothScrollY
            width="100%"
            height="100%"
            getCellsForSelection={true}
            // Ctrl+C: запоминаем диапазон в движке (hf.copy) и текст, который уйдёт в системный буфер
            onKeyDown={(event) => {
                if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'c') {
                    const rect = selectedRect();
                    if (!rect) return;
                    onCopy(rect);
                    const lines: string[][] = [];
                    for (let r = rect.y; r < rect.y + rect.height; r++) {
                        const line: string[] = [];
                        for (let c = rect.x; c < rect.x + rect.width; c++) line.push(engine.view(r, c).text);
                        lines.push(line);
                    }
                    lastCopyText.current = tsv(lines);
                }
            }}
            // Вставка: если в буфере то, что мы сами скопировали, вставляем через движок (сдвиг ссылок)
            onPaste={(target, values) => {
                const [col, row] = target;
                if (lastCopyText.current !== null && tsv(values) === lastCopyText.current && engine.hasClip()) {
                    onPasteInternal(row, col);
                } else {
                    onPasteText(row, col, values.map((line) => [...line]));
                }
                return false;
            }}
            onDelete={(sel) => {
                onClear(sel);
                return false;
            }}
            onColumnResize={(_column, newSize, index) => setLiveWidths((prev) => ({...prev, [index]: newSize}))}
            onColumnResizeEnd={(_column, newSize, index) => {
                setLiveWidths((prev) => {
                    const {[index]: _dropped, ...rest} = prev;
                    return rest;
                });
                onColumnResize(index, newSize);
            }}
            onCellContextMenu={([col, row], event) => {
                event.preventDefault();
                onContextMenu({x: event.bounds.x + event.localEventX, y: event.bounds.y + event.localEventY, row, col});
            }}
            onHeaderContextMenu={(col, event) => {
                event.preventDefault();
                onContextMenu({x: event.bounds.x + event.localEventX, y: event.bounds.y + event.localEventY, row: -1, col});
            }}
        />
    );
};

export const emptySelection = (): GridSelection => ({
    columns: CompactSelection.empty(),
    rows: CompactSelection.empty(),
});

export default SheetGrid;