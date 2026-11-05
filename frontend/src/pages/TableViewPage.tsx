// frontend/src/pages/TableViewPage.tsx
import React, {useState} from "react";
import {useParams, useNavigate} from "react-router-dom";
import type {CompactSelection, GridSelection} from "@glideapps/glide-data-grid";
import TablePermissionsPanel from '../components/TablePermissionsPanel';
import SidebarWithToggle from '../components/SidebarWithToggle';
import SheetGrid, {emptySelection, type ContextMenuState} from '../components/sheet/SheetGrid';
import FormulaBar from '../components/sheet/FormulaBar';
import Toolbar from '../components/sheet/Toolbar';
import SheetContextMenu from '../components/sheet/SheetContextMenu';
import {tablesAPI} from "../api/tables";
import {useSheet} from '../hooks/useSheet';
import {MAX_COLS, MAX_ROWS} from '../sheet/address';
import type {StyleTarget} from '../sheet/engine';
import type {Rect} from '../sheet/types';
import {colors, rounded, shadowLevel3, spacing, typography} from '../styles/theme';

/** Выделение, в которое попал кликнутый индекс -> {index, count}; иначе одна строка/колонка. */
function spanOf(clicked: number, picked: CompactSelection, start?: number, length?: number) {
    if (picked.hasIndex(clicked)) {
        const all = picked.toArray();
        return {index: Math.min(...all), count: all.length};
    }
    if (start !== undefined && length !== undefined && clicked >= start && clicked < start + length) {
        return {index: start, count: length};
    }
    return {index: clicked, count: 1};
}

const TableViewPage: React.FC = () => {
    const {id} = useParams();
    const navigate = useNavigate();
    const tableId = Number(id);

    const sheet = useSheet(tableId);
    const {engine, version, canWrite} = sheet;

    const [selection, setSelection] = useState<GridSelection>(emptySelection());
    const [menu, setMenu] = useState<ContextMenuState | null>(null);
    const [exporting, setExporting] = useState(false);
    const [error, setError] = useState("");

    const range = selection.current?.range;
    const active = selection.current ? {row: selection.current.cell[1], col: selection.current.cell[0]} : null;

    // К чему применять оформление: целые колонки / целые строки / прямоугольник
    const styleTarget = (): StyleTarget | null => {
        if (selection.columns.length > 0) return {kind: 'cols', cols: selection.columns.toArray()};
        if (selection.rows.length > 0) return {kind: 'rows', rows: selection.rows.toArray()};
        if (range) return {kind: 'range', rect: {x: range.x, y: range.y, width: range.width, height: range.height}};
        return null;
    };

    const clearSelection = (sel: GridSelection) => {
        const rects: Rect[] = [];
        if (sel.current) {
            const r = sel.current.range;
            rects.push({x: r.x, y: r.y, width: r.width, height: r.height});
        }
        sel.columns.toArray().forEach((col) => rects.push({x: col, y: 0, width: 1, height: MAX_ROWS}));
        sel.rows.toArray().forEach((row) => rects.push({x: 0, y: row, width: MAX_COLS, height: 1}));
        rects.forEach((rect) => sheet.clearRange(rect));
    };

    const handleExport = async () => {
        try {
            setExporting(true);
            const {job_id} = await tablesAPI.startExport(tableId);
            const result = await tablesAPI.waitForExport(job_id);

            if (result.status === 'error' || !result.download_url) {
                setError(result.error || 'Не удалось экспортировать таблицу');
                return;
            }

            // presigned-ссылка уже содержит content-disposition с именем файла
            const link = document.createElement('a');
            link.href = result.download_url;
            link.click();
        } catch (err: any) {
            console.error('export error:', err);
            setError(err.response?.data?.detail || 'Не удалось экспортировать таблицу')
        } finally {
            setExporting(false);
        }
    };

    if (sheet.loading) {
        return (
            <div style={styles.loadingContainer}>
                <div style={styles.spinner}></div>
                <p>Загрузка данных...</p>
            </div>
        );
    }

    if (sheet.accessError) {
        return (
            <div style={styles.container}>
                <SidebarWithToggle/>
                <main style={styles.main}>
                    <div style={styles.error}>{sheet.accessError.message}</div>
                    <button style={styles.backButton} onClick={() => navigate("/tables")}>← Назад</button>
                </main>
            </div>
        );
    }

    return (
        <div style={styles.container}>
            <SidebarWithToggle/>

            <header style={styles.header}>
                <div style={styles.headerContent}>
                    <h1 style={styles.title}>Таблица №{id}</h1>
                    <div style={styles.headerActions}>
                        <span style={styles.status}>
                            {!canWrite ? 'Только чтение' : sheet.saving ? 'Сохранение…' : 'Все изменения сохранены'}
                        </span>
                        <button style={styles.exportButton} onClick={handleExport} disabled={exporting}>
                            {exporting ? "Экспорт…" : "⬇ Экспорт в Excel"}
                        </button>
                        <button style={styles.backButton} onClick={() => navigate("/tables")}>
                            ← Назад
                        </button>
                    </div>
                </div>
            </header>

            <main style={styles.main}>
                <div style={styles.contentLayout}>
                    <div style={styles.tableColumn}>
                        {(error || sheet.notice) && (
                            <div style={styles.error}>
                                {error || sheet.notice}
                                <button style={styles.closeError} onClick={() => { setError(""); sheet.clearNotice(); }}>×</button>
                            </div>
                        )}

                        <Toolbar
                            engine={engine}
                            version={version}
                            canWrite={canWrite}
                            active={active}
                            target={styleTarget()}
                            onStyle={sheet.applyStyle}
                            onFreeze={sheet.setFrozenCols}
                        />
                        <FormulaBar
                            engine={engine}
                            version={version}
                            selection={selection}
                            canWrite={canWrite}
                            onCommit={sheet.setCell}
                        />
                        <div style={styles.gridWrapper}>
                            <SheetGrid
                                engine={engine}
                                version={version}
                                canWrite={canWrite}
                                selection={selection}
                                onSelectionChange={setSelection}
                                onEdit={sheet.setCell}
                                onPasteText={sheet.setMatrix}
                                onPasteInternal={sheet.paste}
                                onCopy={sheet.copyRange}
                                onClear={clearSelection}
                                onColumnResize={sheet.setColumnWidth}
                                onContextMenu={setMenu}
                            />
                        </div>
                    </div>
                    <aside style={styles.sidePanel}>
                        <TablePermissionsPanel tableId={tableId}/>
                    </aside>
                </div>
            </main>

            {menu && canWrite && (
                <SheetContextMenu
                    menu={menu}
                    rowSpan={spanOf(menu.row, selection.rows, range?.y, range?.height)}
                    colSpan={spanOf(menu.col, selection.columns, range?.x, range?.width)}
                    onStructural={sheet.structural}
                    onClear={() => {
                        const r = spanOf(menu.row, selection.rows, range?.y, range?.height);
                        const c = spanOf(menu.col, selection.columns, range?.x, range?.width);
                        sheet.clearRange(menu.row >= 0
                            ? {x: c.index, y: r.index, width: c.count, height: r.count}
                            : {x: c.index, y: 0, width: c.count, height: MAX_ROWS});
                    }}
                    onClose={() => setMenu(null)}
                />
            )}
        </div>
    );
};

export default TableViewPage;

// ── Стили ──

const styles: Record<string, React.CSSProperties> = {
    container: {minHeight: "100vh", background: colors.canvasSoft},
    header: {
        background: colors.canvas,
        borderBottom: `1px solid ${colors.hairline}`,
        padding: `${spacing.md}px 0`,
    },
    headerContent: {
        padding: `0 ${spacing.lg}px`,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
    },
    headerActions: {display: "flex", gap: spacing.sm, alignItems: "center"},
    title: {...typography.displayMd, color: colors.ink, margin: 0},
    status: {...typography.caption, color: colors.mute},
    backButton: {
        ...typography.bodySmStrong,
        background: "transparent",
        color: colors.body,
        border: "none",
        padding: `0 ${spacing.xs}px`,
        height: 32,
        cursor: "pointer",
    },
    exportButton: {
        ...typography.buttonMd,
        background: colors.canvas,
        color: colors.ink,
        border: `1px solid ${colors.hairline}`,
        padding: `0 ${spacing.md}px`,
        height: 32,
        borderRadius: rounded.sm,
        cursor: "pointer",
    },
    main: {margin: "0 auto", padding: `${spacing.lg}px ${spacing.lg}px`},
    contentLayout: {display: "flex", gap: spacing.lg, alignItems: "flex-start"},
    tableColumn: {flex: 1, minWidth: 0},
    sidePanel: {width: 320, flexShrink: 0},
    // У Glide Data Grid должен быть задан размер контейнера
    gridWrapper: {
        height: "calc(100vh - 260px)", minHeight: 400,
        background: colors.canvas, border: `1px solid ${colors.hairline}`, boxShadow: shadowLevel3,
    },
    loadingContainer: {
        minHeight: "50vh", display: "flex", flexDirection: "column",
        gap: spacing.md, justifyContent: "center", alignItems: "center", color: colors.body,
    },
    spinner: {
        width: 40, height: 40,
        border: `4px solid ${colors.hairline}`, borderTop: `4px solid ${colors.primary}`,
        borderRadius: rounded.full, animation: "spin 1s linear infinite",
    },
    error: {
        ...typography.bodySm,
        background: colors.errorSoft, color: colors.errorDeep, border: `1px solid ${colors.errorSoft}`,
        padding: spacing.md, borderRadius: rounded.sm, marginBottom: spacing.md,
        display: "flex", justifyContent: "space-between", alignItems: "center",
    },
    closeError: {background: "none", border: "none", cursor: "pointer", fontSize: 18, color: colors.errorDeep},
};
