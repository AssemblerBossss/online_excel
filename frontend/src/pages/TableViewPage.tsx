import React, {useEffect, useState, useRef} from "react";
import {useParams, useNavigate} from "react-router-dom";
import {tablesAPI, TableRow, ColumnSchema} from "../api/tables";

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
    const [saving, setSaving] = useState<number | null>(null); // rowId который сохраняется
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        loadData();
    }, [id]);

    useEffect(() => {
        if (editingCell && inputRef.current) {
            inputRef.current.focus();
        }
    }, [editingCell]);

    const loadData = async () => {
        try {
            setLoading(true);

            // Загружаем схему колонок и строки параллельно
            const [tableInfo, tableRows] = await Promise.all([
                tablesAPI.getTableById(tableId),
                tablesAPI.getTableRows(tableId),
            ]);

            setColumns(tableInfo.columns_schema || []);
            setRows(tableRows);
        } catch (err) {
            console.error('loadData error:', err);  // ← добавь
            setError("Не удалось загрузить данные таблицы");
        } finally {
            setLoading(false);
        }
    };

    const colNames = columns.map(c => c.name);

    // ── Inline editing ──

    const startEdit = (rowId: number, col: string, currentValue: any) => {
        setEditingCell({rowId, col});
        setEditingValue(String(currentValue ?? ""));
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

        const newRowData = {...row.row_data, [col]: editingValue};
        console.log('newRowData:', newRowData);  // ← добавь


        // Оптимистичное обновление
        setRows(prev => prev.map(r =>
            r.id === rowId ? {...r, row_data: newRowData} : r
        ));
        setEditingCell(null);

        try {
            setSaving(rowId);
            await tablesAPI.updateRow(tableId, rowId, newRowData);
        } catch (err) {
            // Откатываем при
            console.error('commitEdit error full:', err);
            console.error('commitEdit error message:', err?.message);
            console.error('commitEdit error stack:', err?.stack);
            setRows(prev => prev.map(r =>
                r.id === rowId ? {...r, row_data: row.row_data} : r
            ));
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

            // Сразу открываем редактирование первой ячейки новой строки
            if (colNames.length > 0) {
                startEdit(newRow.id, colNames[0], "");
            }
        } catch (err) {
            setError("Не удалось добавить строку");
        }
    };

    // ── Удаление строки ──

    const deleteRow = async (rowId: number) => {
        // Оптимистичное удаление
        const backup = rows;
        setRows(prev => prev.filter(r => r.id !== rowId));

        try {
            await tablesAPI.deleteRow(tableId, rowId);
        } catch (err) {
            setRows(backup);
            setError("Не удалось удалить строку");
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
                        <button style={styles.addButton} onClick={addRow}>
                            + Добавить строку
                        </button>
                    </div>
                ) : (
                    <div style={styles.tableWrapper}>
                        <table style={styles.table}>
                            <thead>
                            <tr>
                                {colNames.map(col => (
                                    <th key={col} style={styles.th}>{col}</th>
                                ))}
                                <th style={{...styles.th, width: "48px"}}></th>
                            </tr>
                            </thead>
                            <tbody>
                            {rows.map(row => (
                                <tr
                                    key={row.id}
                                    style={{
                                        ...styles.tr,
                                        opacity: saving === row.id ? 0.6 : 1,
                                    }}
                                >
                                    {colNames.map(col => {
                                        const isEditing =
                                            editingCell?.rowId === row.id &&
                                            editingCell?.col === col;

                                        return (
                                            <td
                                                key={col}
                                                style={styles.td}
                                                onClick={() => !isEditing && startEdit(row.id, col, row.row_data[col])}
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
                                                    <span style={styles.cellText}>
                                                        {String(row.row_data[col] ?? "")}
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
                    </div>
                )}
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
        background: "#64748b",
        color: "white",
        border: "none",
        padding: "8px 16px",
        borderRadius: "6px",
        cursor: "pointer",
        fontSize: "14px",
    },
    addButton: {
        background: "#22c55e",
        color: "white",
        border: "none",
        padding: "8px 16px",
        borderRadius: "6px",
        cursor: "pointer",
        fontSize: "14px",
        fontWeight: "600",
    },
    main: {maxWidth: "1400px", margin: "0 auto", padding: "30px 20px"},
    loadingContainer: {
        minHeight: "50vh",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
        justifyContent: "center",
        alignItems: "center",
    },
    spinner: {
        width: "40px",
        height: "40px",
        border: "4px solid #e5e7eb",
        borderTop: "4px solid #3b82f6",
        borderRadius: "50%",
        animation: "spin 1s linear infinite",
    },
    error: {
        background: "#fef2f2",
        color: "#dc2626",
        border: "1px solid #fecaca",
        padding: "16px",
        borderRadius: "8px",
        marginBottom: "20px",
        display: "flex",
        justifyContent: "space-between",
    },
    closeError: {background: "none", border: "none", cursor: "pointer", fontSize: "18px", color: "#dc2626"},
    emptyState: {textAlign: "center", padding: "80px 20px", color: "#64748b"},
    emptyIcon: {fontSize: "64px", marginBottom: "12px"},
    tableWrapper: {
        marginTop: "20px",
        overflowX: "auto",
        boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
        borderRadius: "8px",
    },
    table: {width: "100%", borderCollapse: "collapse", background: "white"},
    th: {
        padding: "12px 16px",
        borderBottom: "2px solid #e2e8f0",
        background: "#f1f5f9",
        textAlign: "left",
        fontWeight: 600,
        color: "#334155",
        whiteSpace: "nowrap",
    },
    tr: {borderBottom: "1px solid #e2e8f0", transition: "opacity 0.2s"},
    td: {
        padding: "0",
        color: "#334155",
        fontSize: "14px",
        cursor: "pointer",
        minWidth: "120px",
    },
    cellText: {
        display: "block",
        padding: "10px 16px",
        minHeight: "38px",
        lineHeight: "18px",
    },
    cellInput: {
        width: "100%",
        padding: "10px 16px",
        border: "none",
        borderBottom: "2px solid #3b82f6",
        outline: "none",
        fontSize: "14px",
        background: "#eff6ff",
        boxSizing: "border-box",
        minHeight: "38px",
    },
    deleteRowBtn: {
        background: "none",
        border: "none",
        cursor: "pointer",
        fontSize: "16px",
        padding: "4px 8px",
        borderRadius: "4px",
        opacity: 0.6,
    },
};

const sheet = document.styleSheets[0];
sheet.insertRule(
    `@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`,
    sheet.cssRules.length
);