import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { tablesAPI } from "../api/tables";

const TableViewPage: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [rows, setRows] = useState<any[] | null>(null);
  const [columns, setColumns] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadData();
  }, [id]);

    const loadData = async () => {
      try {
        setLoading(true);
        const data = await tablesAPI.getTableById(Number(id));

        if (!Array.isArray(data) || data.length === 0) {
          setRows([]);
          setColumns([]);
        } else {
          // здесь важно!
          const processed = data.map((row) => row.row_data || {});

          setRows(processed);
          setColumns(Object.keys(processed[0] ?? {}));
        }
      } catch (err) {
        setError("Не удалось загрузить данные таблицы");
        console.error(err);
      } finally {
        setLoading(false);
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
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <h1 style={styles.title}>Таблица №{id}</h1>
          <button style={styles.backButton} onClick={() => navigate("/tables")}>
            ← Назад
          </button>
        </div>
      </header>

      <main style={styles.main}>
        {error && (
          <div style={styles.error}>
            {error}
            <button style={styles.closeError} onClick={() => setError("")}>×</button>
          </div>
        )}

        {rows && rows.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>📭</div>
            <h2>В таблице пока нет данных</h2>
            <p>Добавьте строки через API или интерфейс редактирования</p>
          </div>
        ) : (
          <div style={styles.tableWrapper}>
            <table style={styles.table}>
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th key={col} style={styles.th}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows?.map((row, index) => (
                  <tr key={index} style={styles.tr}>
                    {columns.map((col) => (
                      <td key={`${index}-${col}`} style={styles.td}>
                        {String(row[col] ?? "")}
                      </td>
                    ))}
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



// -------------------- СТИЛИ --------------------

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: "#f8fafc",
  },
  header: {
    background: "#fff",
    borderBottom: "1px solid #e2e8f0",
    padding: "16px 0",
    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
  },
  headerContent: {
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "0 20px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  title: {
    fontSize: "26px",
    fontWeight: 700,
    color: "#1e293b",
    margin: 0,
  },
  backButton: {
    background: "#3b82f6",
    color: "white",
    border: "none",
    padding: "8px 16px",
    borderRadius: "6px",
    cursor: "pointer",
    fontSize: "14px",
    fontWeight: "500",
  },
  main: {
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "30px 20px",
  },

  // Loading
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

  // Error
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
  closeError: {
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "18px",
    color: "#dc2626",
  },

  // Empty state
  emptyState: {
    textAlign: "center",
    padding: "80px 20px",
    color: "#64748b",
  },
  emptyIcon: {
    fontSize: "64px",
    marginBottom: "12px",
  },

  // Table
  tableWrapper: {
    marginTop: "20px",
    overflowX: "auto",
    boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
    borderRadius: "8px",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    background: "white",
  },
  th: {
    padding: "12px",
    borderBottom: "2px solid #e2e8f0",
    background: "#f1f5f9",
    textAlign: "left",
    fontWeight: 600,
    color: "#334155",
  },
  tr: {
    borderBottom: "1px solid #e2e8f0",
  },
  td: {
    padding: "12px",
    color: "#334155",
    fontSize: "14px",
  },
};

// Animation
const sheet = document.styleSheets[0];
sheet.insertRule(
  `@keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
  }`,
  sheet.cssRules.length
);
