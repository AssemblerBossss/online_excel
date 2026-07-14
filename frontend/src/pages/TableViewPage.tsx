// frontend/src/pages/TableViewPage.tsx
import React, {useEffect, useState, useRef} from "react";
import {useParams, useNavigate} from "react-router-dom";
import TablePermissionsPanel from '../components/TablePermissionsPanel';
import {tablesAPI, TableRow, ColumnSchema, RowFilter, isFormula, evaluateFormula} from "../api/tables";
import {subscribeToTableEvents} from '../api/ws';

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
        } catch (err) {
            console.error('loadTable error:', err);
            setError("Не удалось загрузить таблицу");
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
        } catch (err) {
            console.error('loadRows error:', err);
            setError("Не удалось загрузить данные таблицы");
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
        } catch (err) {
            setRows(backup);
            setError("Не удалось удалить строку");
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
        } catch (err) {
            console.error('export error:', err);
            setError('Не удалось экспортировать таблицу');
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
                                <h2>В таблице пока нет данных</h2>
                                <p>Нажмите «+ Добавить строку» чтобы начать</p>
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
                                        <th style={{...styles.th, width: "48px"}}></th>
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
                                                        {isEditing ? (
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
                                                        )}
                                                    </td>
                                                );
                                            })}
                                            <td style={{...styles.td, textAlign: "center"}}>
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

const styles: Record<string, React.CSSProperties> = {
    container: {minHeight: "100vh", background: "#f8fafc"},
    header: {
        background: "#fff",
        borderBottom: "1px solid #e2e8f0",
        padding: "16px 0",
        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
    },
    headerContent: {
        maxWidth: "1400px",
        margin: "0 auto",
        padding: "0 20px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
    },
    headerActions: {display: "flex", gap: "12px", alignItems: "center"},
    title: {fontSize: "26px", fontWeight: 700, color: "#1e293b", margin: 0},
    backButton: {
        background: "#64748b", color: "white", border: "none",
        padding: "8px 16px", borderRadius: "6px", cursor: "pointer", fontSize: "14px",
    },
    addButton: {
        background: "#22c55e", color: "white", border: "none",
        padding: "8px 16px", borderRadius: "6px", cursor: "pointer",
        fontSize: "14px", fontWeight: "600",
    },
    exportButton: {
        background: "#3b82f6", color: "white", border: "none",
        padding: "8px 16px", borderRadius: "6px", cursor: "pointer",
        fontSize: "14px", fontWeight: "600",
    },
    main: {maxWidth: "1400px", margin: "0 auto", padding: "30px 20px"},
    contentLayout: {display: 'flex', gap: 24, alignItems: 'flex-start'},
    tableColumn: {flex: 1, minWidth: 0},
    sidePanel: {width: 320, flexShrink: 0},
    loadingContainer: {
        minHeight: "50vh", display: "flex", flexDirection: "column",
        gap: "16px", justifyContent: "center", alignItems: "center",
    },
    spinner: {
        width: "40px", height: "40px",
        border: "4px solid #e5e7eb", borderTop: "4px solid #3b82f6",
        borderRadius: "50%", animation: "spin 1s linear infinite",
    },
    error: {
        background: "#fef2f2", color: "#dc2626", border: "1px solid #fecaca",
        padding: "16px", borderRadius: "8px", marginBottom: "20px",
        display: "flex", justifyContent: "space-between",
    },
    closeError: {background: "none", border: "none", cursor: "pointer", fontSize: "18px", color: "#dc2626"},
    emptyState: {textAlign: "center", padding: "80px 20px", color: "#64748b"},
    emptyIcon: {fontSize: "64px", marginBottom: "12px"},
    tableWrapper: {
        marginTop: "20px", overflowX: "auto",
        boxShadow: "0 1px 3px rgba(0,0,0,0.1)", borderRadius: "8px",
    },
    table: {width: "100%", borderCollapse: "collapse", background: "white"},
    th: {
        padding: "12px 16px", borderBottom: "2px solid #e2e8f0",
        background: "#f1f5f9", textAlign: "left", fontWeight: 600,
        color: "#334155", whiteSpace: "nowrap",
    },
    tr: {borderBottom: "1px solid #e2e8f0", transition: "opacity 0.2s"},
    td: {padding: "0", color: "#334155", fontSize: "14px", cursor: "pointer", minWidth: "120px"},
    cellText: {
        display: "block", padding: "10px 16px", minHeight: "38px",
        lineHeight: "18px", position: "relative" as const,
    },
    cellFormula: {
        background: "#eff6ff",
        color: "#1e40af",
    },
    cellError: {
        color: "#dc2626",
        fontWeight: 600,
    },
    formulaIndicator: {
        position: "absolute" as const, top: "2px", right: "4px",
        fontSize: "9px", color: "#93c5fd", fontWeight: 700,
        lineHeight: 1, userSelect: "none" as const,
    },
    cellInput: {
        width: "100%", padding: "10px 16px", border: "none",
        borderBottom: "2px solid #3b82f6", outline: "none", fontSize: "14px",
        background: "#eff6ff", boxSizing: "border-box" as const, minHeight: "38px",
    },
    deleteRowBtn: {
        background: "none", border: "none", cursor: "pointer",
        fontSize: "16px", padding: "4px 8px", borderRadius: "4px", opacity: 0.6,
    },
    rowNumber: {
        padding: "0 8px",
        textAlign: "center" as const,
        fontSize: "11px",
        color: "#94a3b8",
        background: "#f1f5f9",
        borderRight: "1px solid #e2e8f0",
        userSelect: "none" as const,
        minWidth: "40px",
    },
    rowNumberHeader: {
        width: "40px",
        minWidth: "40px",
        background: "#e2e8f0",
        borderBottom: "2px solid #e2e8f0",
        borderRight: "1px solid #e2e8f0",
    },
    filterCell: {
        padding: "4px 8px", background: "#f8fafc",
        borderBottom: "1px solid #e2e8f0",
    },
    filterInput: {
        width: "100%", padding: "4px 8px", fontSize: "12px",
        border: "1px solid #cbd5e1", borderRadius: "4px",
        boxSizing: "border-box" as const,
    },
    pagination: {
        display: "flex", alignItems: "center", justifyContent: "center",
        gap: "16px", padding: "16px",
    },
    pageBtn: {
        background: "#64748b", color: "white", border: "none",
        padding: "8px 16px", borderRadius: "6px", cursor: "pointer", fontSize: "14px",
    },
    pageInfo: {fontSize: "14px", color: "#475569"},
};