import React, {useState, useEffect} from 'react';
import {useNavigate} from 'react-router-dom';
import {tablesAPI, DataTableResponse} from '../api/tables';

const TrashPage: React.FC = () => {
    const navigate = useNavigate();
    const [tables, setTables] = useState<DataTableResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const loadData = async () => {
        try {
            setLoading(true);
            const data = await tablesAPI.getTrash();
            setTables(data);
        } catch (err) {
            setError("Не удалось загрузить корзину");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadData();
    }, []);

    const handlePermanentDelete = async (id: number) => {
        if (!confirm('Вы уверены? Это действие необратимо.')) return;
        const backup = tables;
        setTables(prev => prev.filter(t => t.id !== id));
        try {
            await tablesAPI.permanentDelete(id);
        } catch (err) {
            setTables(backup);
            setError('Не удалось удалить таблицу');
        }
    };

    const handleRestore = async (id: number) => {
        const backup = tables;
        setTables(prev => prev.filter(t => t.id !== id));
        try {
            await tablesAPI.restoreTable(id);
        } catch (err) {
            setTables(backup);
            setError('Не удалось восстановить таблицу');
        }
    };

    const formatDate = (dateStr: string) =>
        new Date(dateStr).toLocaleString('ru-RU');

    if (loading) {
        return (
            <div style={styles.loadingContainer}>
                <div style={styles.loadingSpinner}></div>
                <p>Загрузка...</p>
            </div>
        );
    }

    return (
        <div style={styles.container}>
            <header style={styles.header}>
                <div style={styles.headerContent}>
                    <h1 style={styles.title}>🗑 Корзина</h1>
                    <button style={styles.backButton} onClick={() => navigate('/tables')}>
                        ← Назад к таблицам
                    </button>
                </div>
            </header>

            <main style={styles.main}>
                {error && (
                    <div style={styles.error}>
                        {error}
                        <button onClick={() => setError('')} style={styles.closeError}>×</button>
                    </div>
                )}

                {tables.length === 0 ? (
                    <div style={styles.emptyState}>
                        <div style={styles.emptyIcon}>🗑</div>
                        <h2>Корзина пуста</h2>
                        <p>Удалённые таблицы будут отображаться здесь</p>
                    </div>
                ) : (
                    <div style={styles.tableGrid}>
                        {tables.map(table => (
                            <div key={table.id} style={styles.tableCard}>
                                <div style={styles.tableHeader}>
                                    <h3 style={styles.tableName}>{table.name}</h3>
                                </div>

                                {table.description && (
                                    <p style={styles.tableDescription}>{table.description}</p>
                                )}

                                <div style={styles.tableMeta}>
                                    <div style={styles.metaItem}>
                                        <span style={styles.metaLabel}>Столбцов:</span>
                                        <span>{table.columns_schema?.length || 0}</span>
                                    </div>
                                    <div style={styles.metaItem}>
                                        <span style={styles.metaLabel}>Удалена:</span>
                                        <span>{table.deleted_at ? formatDate(table.deleted_at) : '—'}</span>
                                    </div>
                                </div>

                                <div style={styles.tableActions}>
                                    <button
                                        style={styles.restoreButton}
                                        onClick={() => handleRestore(table.id)}
                                    >
                                        ↩ Восстановить
                                    </button>
                                    <button
                                        style={styles.deleteButton}
                                        onClick={() => handlePermanentDelete(table.id)}
                                    >
                                        🗑 Удалить навсегда
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>
        </div>
    );
};

export default TrashPage;

const styles: Record<string, React.CSSProperties> = {
    container: {minHeight: '100vh', background: '#f8fafc'},
    header: {
        background: '#fff',
        borderBottom: '1px solid #e2e8f0',
        padding: '16px 0',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    },
    headerContent: {
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '0 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    title: {fontSize: '28px', fontWeight: '700', color: '#1a202c', margin: 0},
    backButton: {
        background: '#64748b', color: 'white', border: 'none',
        padding: '8px 16px', borderRadius: '6px', fontSize: '14px', cursor: 'pointer',
    },
    main: {maxWidth: '1200px', margin: '0 auto', padding: '32px 20px'},
    loadingContainer: {
        display: 'flex', flexDirection: 'column', alignItems: 'center',
        justifyContent: 'center', minHeight: '50vh', gap: '16px',
    },
    loadingSpinner: {
        width: '40px', height: '40px',
        border: '4px solid #e2e8f0', borderTop: '4px solid #3b82f6',
        borderRadius: '50%', animation: 'spin 1s linear infinite',
    },
    error: {
        background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626',
        padding: '16px', borderRadius: '8px', marginBottom: '24px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    },
    closeError: {background: 'none', border: 'none', fontSize: '18px', cursor: 'pointer', color: '#dc2626'},
    emptyState: {textAlign: 'center', padding: '80px 20px', color: '#64748b'},
    emptyIcon: {fontSize: '64px', marginBottom: '16px'},
    tableGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: '24px',
    },
    tableCard: {
        background: 'white', border: '1px solid #e2e8f0',
        borderRadius: '12px', padding: '24px',
    },
    tableHeader: {
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'flex-start', marginBottom: '12px',
    },
    tableName: {fontSize: '18px', fontWeight: '600', color: '#1a202c', margin: 0},
    tableDescription: {color: '#64748b', fontSize: '14px', lineHeight: '1.5', marginBottom: '16px'},
    tableMeta: {display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '20px'},
    metaItem: {display: 'flex', justifyContent: 'space-between', fontSize: '14px'},
    metaLabel: {color: '#64748b', fontWeight: '500'},
    tableActions: {display: 'flex', gap: '8px'},
    restoreButton: {
        flex: 1, background: '#f0fdf4', border: '1px solid #bbf7d0',
        color: '#16a34a', padding: '8px 12px', borderRadius: '6px',
        fontSize: '14px', cursor: 'pointer', fontWeight: '500',
    },
    deleteButton: {
        flex: 1, background: '#fef2f2', border: '1px solid #fecaca',
        color: '#dc2626', padding: '8px 12px', borderRadius: '6px',
        fontSize: '14px', cursor: 'pointer', fontWeight: '500',
    },
};