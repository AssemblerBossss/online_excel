// frontend/src/pages/TableViewPage.tsx
import React, {useEffect, useState, useRef} from "react";
import {useParams, useNavigate} from "react-router-dom";
import TablePermissionsPanel from '../components/TablePermissionsPanel';
import SidebarWithToggle from '../components/SidebarWithToggle';
import {tablesAPI, TableRow, ColumnSchema, RowFilter, isFormula, evaluateFormula} from "../api/tables";
import {subscribeToTableEvents} from '../api/ws';
import {colors, rounded, shadowLevel3, spacing, typography} from '../styles/theme';

const PAGE_SIZE = 50;

interface EditingCell {
    rowId: number;
    col: string;
}

const TableViewPage: React.FC = () => {
    const {id} = useParams();
    const navigate = useNavigate();
    const tableId = Number(id);

    const [rows, setRows] = useState<TableRow[]>([]);
    const [columns, setColumns] = useState<ColumnSchema[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [accessError, setAccessError] = useState<{ status: number | null; message: string } | null>(null);
    const [editingCell, setEditingCell] = useState<EditingCell | null>(null);
    const [editingValue, setEditingValue] = useState("");
    const [saving, setSaving] = useState<number | null>(null);
    const [exporting, setExporting] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    // Сортировка / фильтрация / пагинация (серверные)
    const [page, setPage] = useState(0);          // 0-based
    const [total, setTotal] = useState(0);
    const [sortBy, setSortBy] = useState<string | null>(null);
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
    // черновик фильтров в инпутах (применяется по Enter/blur) и применённые фильтры
    const [filterDraft, setFilterDraft] = useState<Record<string, string>>({});
    const [filters, setFilters] = useState<RowFilter[]>([]);

    useEffect(() => {
        loadTable();
    }, [id]);
    useEffect(() => {
        loadRows();
    }, [id, page, sortBy, sortOrder, filters]);

    useEffect(() => {
        if (editingCell && inputRef.current) {
            inputRef.current.focus();
        }
    }, [editingCell]);

    const loadTable = async () => {
        try {
            const tableInfo = await tablesAPI.getTableById(tableId);
            setColumns(tableInfo.columns_schema || []);
        } catch (err: any) {
            console.error('loadTable error:', err);
            const status = err.response?.status ?? null;
            const detail = err.response?.data?.detail;
            setAccessError({
                status,
                message: detail || (status === 403
                    ? 'Нет доступа к этой таблице'
                    : status === 404
                        ? 'Таблица не найдена'
                        : 'Не удалось загрузить таблицу'),
            });
        }
    };

    const loadRows = async () => {
        try {
            setLoading(true);
            const res = await tablesAPI.getTableRows(tableId, {
                skip: page * PAGE_SIZE,
                limit: PAGE_SIZE,
                sortBy: sortBy ?? undefined,
                sortOrder,
                filters,
            });
            setRows(res.items);
            setTotal(res.total);
        } catch (err: any) {
            console.error('loadRows error:', err);
            const status = err.response?.status ?? null;
            if (status === 403 || status === 404) {
                const detail = err.response?.data?.detail;
                setAccessError({
                    status,
                    message: detail || (status === 403 ? 'Нет доступа к этой таблице' : 'Таблица не найдена'),
                });
            } else {
                setError(err.response?.data?.detail || "Не удалось загрузить данные таблицы");
            }
        } finally {
            setLoading(false);
        }
    };


    const loadRowsRef = useRef(loadRows);
    useEffect(() => {
        loadRowsRef.current = loadRows;
    });

    useEffect(() => {
        if (!tableId) return;
        let reloadTimer: number | null = null;

        const unsubscribe = subscribeToTableEvents(tableId, () => {
            if (reloadTimer) window.clearTimeout(reloadTimer);
            reloadTimer = window.setTimeout(() => loadRowsRef.current(), 300);
        });

        return () => {
            if (reloadTimer) window.clearTimeout(reloadTimer);
            unsubscribe();
        };
    }, [tableId]);

    const colNames = columns.map(c => c.name);
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    // ── Сортировка / фильтрация / пагинация ──

    const toggleSort = (col: string) => {
        if (sortBy === col) {
            setSortOrder(prev => (prev === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortBy(col);
            setSortOrder('asc');
        }
        setPage(0);
    };

    // применяем фильтр по колонке: пустое значение — убираем фильтр
    const applyFilter = (col: string) => {
        const value = (filterDraft[col] ?? '').trim();
        setFilters(prev => {
            const rest = prev.filter(f => f.field !== col);
            return value ? [...rest, {field: col, op: 'contains' as const, value}] : rest;
        });
        setPage(0);
    };

    // ── Отображение ──

    const getDisplayValue = (row: TableRow, col: string): string =>
        String(row.row_data[col] ?? "");

    const hasFormula = (row: TableRow, col: string): boolean =>
        !!(row.formulas?.[col]);

    // ── Inline editing ──

    /**
     * При открытии ячейки показываем исходную формулу если она есть,
     * иначе — вычисленное значение.
     */
    const startEdit = (rowId: number, col: string, row: TableRow) => {
        const formulaOrValue = row.formulas?.[col] ?? String(row.row_data[col] ?? "");
        setEditingCell({rowId, col});
        setEditingValue(formulaOrValue);
    };

    const cancelEdit = () => {
        setEditingCell(null);
        setEditingValue("");
    };

    const commitEdit = async () => {
        if (!editingCell) return;

        const {rowId, col} = editingCell;
        const row = rows.find(r => r.id === rowId);
        if (!row) return;

        setEditingCell(null);

        const valueIsFormula = isFormula(editingValue);

        // Фронтенд вычисляет результат сам
        // стало
        const computedValue = valueIsFormula
            ? String(evaluateFormula(editingValue, row.row_data, colNames))
            : editingValue;

        // Обновляем словарь формул: добавляем или удаляем запись
        const updatedFormulas: Record<string, string> = {...(row.formulas ?? {})};
        if (valueIsFormula) {
            updatedFormulas[col] = editingValue;
        } else {
            delete updatedFormulas[col];
        }

        // row_data всегда хранит вычисленные значения
        const newRowData = {...row.row_data, [col]: computedValue};

        // Оптимистичное обновление
        setRows(prev => prev.map(r =>
            r.id === rowId
                ? {
                    ...r,
                    row_data: newRowData,
                    formulas: Object.keys(updatedFormulas).length ? updatedFormulas : undefined,
                }
                : r
        ));

        try {
            setSaving(rowId);
            // Отправляем вычисленное значение + исходную формулу отдельно.
            // Бэкенд просто сохраняет оба поля, ничего не пересчитывает.
            const updated = await tablesAPI.updateRow(
                tableId,
                rowId,
                newRowData,                                                          // вычисленные значения
                Object.keys(updatedFormulas).length ? updatedFormulas : undefined,   // исходные формулы
            );
            // Синхронизируемся с ответом бэкенда
            setRows(prev => prev.map(r => r.id === rowId ? updated : r));
            setError("");
        } catch (err) {
            console.error('commitEdit error:', err);
            setRows(prev => prev.map(r => r.id === rowId ? row : r));
            setError("Не удалось сохранить изменения");
        } finally {
            setSaving(null);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter") commitEdit();
        if (e.key === "Escape") cancelEdit();
    };

    // ── Добавление строки ──

    const addRow = async () => {
        const emptyRow: Record<string, any> = {};
        colNames.forEach(col => {
            emptyRow[col] = "";
        });

        try {
            const newRow = await tablesAPI.createRow(tableId, emptyRow);
            setRows(prev => [...prev, newRow]);
            setError("");
            if (colNames.length > 0) {
                startEdit(newRow.id, colNames[0], newRow);
            }
        } catch (err) {
            setError("Не удалось добавить строку");
        }
    };

    // ── Удаление строки ──

    const deleteRow = async (rowId: number) => {
        const backup = rows;
        setRows(prev => prev.filter(r => r.id !== rowId));
        try {
            await tablesAPI.deleteRow(tableId, rowId);
            setError("");
        } catch (err: any) {
            setRows(backup);
            setError(err.response?.data?.detail || "Не удалось удалить строку");
        }
    };

    // ── Дублирование строки ──

    const duplicateRow = async(rowId: number) => {
        try {
            await tablesAPI.duplicateRow(tableId, rowId);
            // Строки постранично пагинируются на сервере — проще перезапросить
            // текущую страницу, чем вручную пересчитывать смещения/индексы.
            await loadRows();
            setError("");
        }  catch (err: any) {
            console.error('duplicateRow error:', err);
            setError(err.response?.data?.detail || "Не удалось скопировать строку");
        }
    };

    // ── Экспорт ──

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

    if (loading) {
        return (
            <div style={styles.loadingContainer}>
                <div style={styles.spinner}></div>
                <p>Загрузка данных...</p>
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
                        <button style={styles.exportButton} onClick={handleExport} disabled={exporting}>
                            {exporting ? "Экспорт…" : "⬇ Экспорт в Excel"}
                        </button>
                        <button style={styles.addButton} onClick={addRow}>
                            + Добавить строку
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
                        {error && (
                            <div style={styles.error}>
                                {error}
                                <button style={styles.closeError} onClick={() => setError("")}>×</button>
                            </div>
                        )}

                        {rows.length === 0 ? (
                            <div style={styles.emptyState}>
                                <div style={styles.emptyIcon}>📭</div>
                                <h2 style={styles.emptyTitle}>В таблице пока нет данных</h2>
                                <p style={styles.emptyText}>Нажмите «+ Добавить строку» чтобы начать</p>
                                <button style={styles.addButton} onClick={addRow}>+ Добавить строку</button>
                            </div>
                        ) : (
                            <div style={styles.tableWrapper}>
                                <table style={styles.table}>
                                    <thead>
                                    <tr>
                                        <th style={styles.rowNumberHeader}></th>
                                        {colNames.map(col => (
                                            <th
                                                key={col}
                                                style={{...styles.th, cursor: "pointer"}}
                                                onClick={() => toggleSort(col)}
                                            >
                                                {col}
                                                {sortBy === col && <span> {sortOrder === 'asc' ? '▲' : '▼'}</span>}
                                            </th>
                                        ))}
                                        <th style={{...styles.th, width: "72px"}}></th>
                                    </tr>
                                    <tr>
                                        <th style={styles.rowNumberHeader}></th>
                                        {colNames.map(col => (
                                            <th key={col} style={styles.filterCell}>
                                                <input
                                                    style={styles.filterInput}
                                                    placeholder="фильтр…"
                                                    value={filterDraft[col] ?? ''}
                                                    onChange={e => setFilterDraft(prev => ({
                                                        ...prev,
                                                        [col]: e.target.value
                                                    }))}
                                                    onKeyDown={e => {
                                                        if (e.key === 'Enter') applyFilter(col);
                                                    }}
                                                    onBlur={() => applyFilter(col)}
                                                />
                                            </th>
                                        ))}
                                        <th style={styles.filterCell}></th>
                                    </tr>
                                    </thead>
                                    <tbody>
                                    {rows.map((row, rowIndex) => (
                                        <tr
                                            key={row.id}
                                            style={{...styles.tr, opacity: saving === row.id ? 0.6 : 1}}
                                        >
                                            <td style={styles.rowNumber}>{page * PAGE_SIZE + rowIndex + 1}</td>
                                            {colNames.map(col => {
                                                const isEditing =
                                                    editingCell?.rowId === row.id &&
                                                    editingCell?.col === col;
                                                const cellHasFormula = hasFormula(row, col);
                                                const displayValue = getDisplayValue(row, col);

                                                return (
                                                    <td
                                                        key={col}
                                                        style={styles.td}
                                                        onClick={() => !isEditing && startEdit(row.id, col, row)}
                                                    >
                                                        {
                                                            isEditing ? (
                                                                <input
                                                                    ref={inputRef}
                                                                    style={styles.cellInput}
                                                                    value={editingValue}
                                                                    onChange={e => setEditingValue(e.target.value)}
                                                                    onBlur={commitEdit}
                                                                    onKeyDown={handleKeyDown}
                                                                />
                                                            ) : (
                                                                <span
                                                                    style={{
                                                                        ...styles.cellText,
                                                                        ...(cellHasFormula ? styles.cellFormula : {}),
                                                                        ...(displayValue === "#ОШИБКА!" ? styles.cellError : {}),
                                                                    }}
                                                                    title={cellHasFormula ? row.formulas![col] : undefined}
                                                                >
                                                        {displayValue}
                                                                    {cellHasFormula && displayValue !== "#ОШИБКА!" && (
                                                                        <span style={styles.formulaIndicator}>ƒ</span>
                                                                    )}
                                                    </span>
                                                            )
                                                        }
                                                    </td>
                                                )
                                                    ;
                                            })}
                                            <td style={{...styles.td, textAlign: "center"}}>
                                                <button
                                                    style={styles.duplicateRowBtn}
                                                    onClick={() => duplicateRow(row.id)}
                                                    title="Копировать строку"
                                                >
                                                    📄
                                                </button>
                                                <button
                                                    style={styles.deleteRowBtn}
                                                    onClick={() => deleteRow(row.id)}
                                                    title="Удалить строку"
                                                >
                                                    🗑
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                    </tbody>
                                </table>

                                <div style={styles.pagination}>
                                    <button
                                        style={styles.pageBtn}
                                        disabled={page === 0}
                                        onClick={() => setPage(p => Math.max(0, p - 1))}
                                    >
                                        ← Назад
                                    </button>
                                    <span style={styles.pageInfo}>
                                Стр. {page + 1} из {totalPages} · всего {total}
                            </span>
                                    <button
                                        style={styles.pageBtn}
                                        disabled={page + 1 >= totalPages}
                                        onClick={() => setPage(p => p + 1)}
                                    >
                                        Вперёд →
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                    <aside style={styles.sidePanel}>
                        <TablePermissionsPanel tableId={tableId}/>
                    </aside>
                </div>
            </main>
        </div>
    );
};

export default TableViewPage;

// ── Стили ──

const captionMono: React.CSSProperties = {
    ...typography.caption,
    fontFamily: "'Geist Mono', 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, monospace",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    color: colors.body,
};

const styles: Record<string, React.CSSProperties> = {
    container: {minHeight: "100vh", background: colors.canvasSoft},
    header: {
        background: colors.canvas,
        borderBottom: `1px solid ${colors.hairline}`,
        padding: `${spacing.md}px 0`,
    },
    headerContent: {
        maxWidth: "1400px",
        margin: "0 auto",
        padding: `0 ${spacing.lg}px`,
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
    },
    headerActions: {display: "flex", gap: spacing.sm, alignItems: "center"},
    title: {...typography.displayMd, color: colors.ink, margin: 0},
    backButton: {
        ...typography.bodySmStrong,
        background: "transparent",
        color: colors.body,
        border: "none",
        padding: `0 ${spacing.xs}px`,
        height: 32,
        cursor: "pointer",
    },
    addButton: {
        ...typography.buttonMd,
        background: colors.primary,
        color: colors.onPrimary,
        border: "none",
        padding: `0 ${spacing.md}px`,
        height: 32,
        borderRadius: rounded.sm,
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
    main: {maxWidth: "1400px", margin: "0 auto", padding: `${spacing.xl}px ${spacing.lg}px`},
    contentLayout: {display: "flex", gap: spacing.lg, alignItems: "flex-start"},
    tableColumn: {flex: 1, minWidth: 0},
    sidePanel: {width: 320, flexShrink: 0},
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
        padding: spacing.md, borderRadius: rounded.sm, marginBottom: spacing.lg,
        display: "flex", justifyContent: "space-between", alignItems: "center",
    },
    closeError: {background: "none", border: "none", cursor: "pointer", fontSize: 18, color: colors.errorDeep},
    emptyState: {
        ...typography.bodyMd,
        textAlign: "center", padding: `${spacing["4xl"]}px ${spacing.lg}px`,
        background: colors.canvas, borderRadius: rounded.lg, boxShadow: shadowLevel3, color: colors.body,
    },
    emptyIcon: {fontSize: 64, marginBottom: spacing.md},
    emptyTitle: {...typography.displaySm, color: colors.ink, margin: 0},
    emptyText: {...typography.bodySm, color: colors.body, marginTop: spacing.xs, marginBottom: spacing.md},
    tableWrapper: {
        marginTop: spacing.md, overflowX: "auto",
        background: colors.canvas, borderRadius: rounded.md, boxShadow: shadowLevel3,
    },
    table: {width: "100%", borderCollapse: "collapse", background: colors.canvas},
    th: {
        ...captionMono,
        padding: `${spacing.xs}px ${spacing.sm}px`, borderBottom: `1px solid ${colors.hairline}`,
        background: colors.canvasSoft, textAlign: "left", whiteSpace: "nowrap",
    },
    tr: {borderBottom: `1px solid ${colors.hairline}`, transition: "opacity 0.2s"},
    td: {padding: 0, color: colors.ink, cursor: "pointer", minWidth: 120},
    cellText: {
        ...typography.bodySm,
        display: "block", padding: `${spacing.xs}px ${spacing.sm}px`, minHeight: 38,
        lineHeight: "20px", position: "relative" as const, color: colors.ink,
    },
    cellFormula: {
        background: colors.linkBgSoft,
        color: colors.linkDeep,
    },
    cellError: {
        color: colors.errorDeep,
        fontWeight: 600,
    },
    formulaIndicator: {
        position: "absolute" as const, top: 2, right: 4,
        fontSize: 9, color: colors.link, fontWeight: 700,
        lineHeight: 1, userSelect: "none" as const,
    },
    cellInput: {
        ...typography.bodySm,
        width: "100%", padding: `${spacing.xs}px ${spacing.sm}px`, border: "none",
        borderBottom: `2px solid ${colors.primary}`, outline: "none",
        background: colors.canvasSoft2, boxSizing: "border-box" as const, minHeight: 38, color: colors.ink,
    },
    deleteRowBtn: {
        background: "none", border: "none", cursor: "pointer",
        fontSize: 16, padding: `${spacing.xxs}px ${spacing.xs}px`, borderRadius: rounded.xs, opacity: 0.6,
    },
    duplicateRowBtn: {
        background: "none", border: "none", cursor: "pointer",
        fontSize: 16, padding: `${spacing.xxs}px ${spacing.xs}px`, borderRadius: rounded.xs, opacity: 0.6,
    },
    rowNumber: {
        padding: `0 ${spacing.xs}px`,
        textAlign: "center" as const,
        ...typography.caption,
        color: colors.mute,
        background: colors.canvasSoft,
        borderRight: `1px solid ${colors.hairline}`,
        userSelect: "none" as const,
        minWidth: 40,
    },
    rowNumberHeader: {
        width: 40,
        minWidth: 40,
        background: colors.canvasSoft2,
        borderBottom: `1px solid ${colors.hairline}`,
        borderRight: `1px solid ${colors.hairline}`,
    },
    filterCell: {
        padding: `${spacing.xxs}px ${spacing.xs}px`, background: colors.canvasSoft,
        borderBottom: `1px solid ${colors.hairline}`,
    },
    filterInput: {
        ...typography.caption,
        width: "100%", padding: `${spacing.xxs}px ${spacing.xs}px`,
        border: `1px solid ${colors.hairline}`, borderRadius: rounded.xs,
        boxSizing: "border-box" as const, background: colors.canvas, color: colors.ink,
    },
    pagination: {
        display: "flex", alignItems: "center", justifyContent: "center",
        gap: spacing.md, padding: spacing.md,
    },
    pageBtn: {
        ...typography.bodySmStrong,
        background: colors.canvas, color: colors.ink, border: `1px solid ${colors.hairline}`,
        padding: `0 ${spacing.md}px`, height: 32, borderRadius: rounded.sm, cursor: "pointer",
    },
    pageInfo: {...typography.bodySm, color: colors.body},
};