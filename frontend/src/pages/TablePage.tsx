import React, {useState, useEffect} from 'react';
import {useNavigate} from 'react-router-dom';
import {tablesAPI, DataTableResponse} from '../api/tables';
import api from "../api/axiosInstance";
import SidebarWithToggle from '../components/SidebarWithToggle';
import {colors, rounded, shadowLevel2, shadowLevel3, shadowLevel5, spacing, typography} from '../styles/theme';


const TablesPage: React.FC = () => {
    const navigate = useNavigate();
    const [tables, setTables] = useState<DataTableResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [duplicatingTable, setDuplicatingTable] = useState<DataTableResponse | null>(null);
    const [duplicateName, setDuplicateName] = useState('');
    const [duplicateWithRows, setDuplicateWithRows] = useState(true);
    const [isDuplicating, setIsDuplicating] = useState(false);
    const [newTableName, setNewTableName] = useState('');
    const [newTableDescription, setNewTableDescription] = useState('');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [createMethod, setCreateMethod] = useState<'manual' | 'excel'>('manual');

    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<DataTableResponse[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [showSuggestions, setShowSuggestions] = useState(false)

    useEffect(() => {
        if (!searchQuery.trim()) {
            setSearchResults([]);
            setShowSuggestions(false);
            return;
        }

        const timer = setTimeout(async () => {
            setIsSearching(true);
            try {
                const results = await tablesAPI.searchTables(searchQuery);
                setSearchResults(results);
                setShowSuggestions(true);
            } catch (err) {
                console.error('Ошибка поиска:', err);
            } finally {
                setIsSearching(false);
            }
        }, 300);
        return () => clearTimeout(timer);
    }, [searchQuery]);


    useEffect(() => {
        loadTables();
    }, []);

    const loadTables = async () => {
        try {
            setLoading(true);
            const data = await tablesAPI.getAllTables();
            setTables(data);
        } catch (err: any) {
            setError('Не удалось загрузить таблицы');
            console.error('Error loading tables:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateTable = async (e: React.FormEvent) => {
        e.preventDefault();

        if (createMethod === 'excel') {
            await handleExcelUpload();
        } else {
            await handleManualCreate();
        }
    };

    const handleManualCreate = async () => {
        if (!newTableName.trim()) return;

        try {
            const newTable = await tablesAPI.createTable({
                name: newTableName,
                description: newTableDescription || undefined,
                is_public: false,
                columns_schema: [
                    {name: 'A', type: 'string'},
                    {name: 'B', type: 'number'},
                    {name: 'C', type: 'string'}
                ]
            });

            setTables(prev => [newTable, ...prev]);
            resetModal();
            // Остаёмся на странице таблиц, не переходим на несуществующий роут
        } catch (err: any) {
            setError('Не удалось создать таблицу');
            console.error('Error creating table:', err);
        }
    };

    const handleExcelUpload = async () => {
        if (!selectedFile) {
            setError('Пожалуйста, выберите файл Excel');
            return;
        }

        if (!newTableName.trim()) {
            setError('Пожалуйста, введите название таблицы');
            return;
        }

        try {
            setIsUploading(true);

            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('table_name', newTableName);
            if (newTableDescription) {
                formData.append('description', newTableDescription);
            }

            // Используем axios для загрузки файла
            const response = await api.post('/tables/process_excel', formData);

            const newTable = response.data;

            setTables(prev => [newTable, ...prev]);
            resetModal();
            // Остаёмся на странице таблиц, не переходим на несуществующий роут
        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || 'Не удалось загрузить файл Excel';
            setError(errorMessage);
            console.error('Error uploading Excel file:', err);
        } finally {
            setIsUploading(false);
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            // Проверяем расширение файла
            const validExtensions = ['.xlsx', '.xls', '.csv'];
            const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();

            if (!validExtensions.includes(fileExtension)) {
                setError('Пожалуйста, выберите файл Excel (.xlsx, .xls) или CSV');
                return;
            }

            setSelectedFile(file);

            // Автоматически устанавливаем название таблицы из имени файла
            if (!newTableName.trim()) {
                const fileNameWithoutExtension = file.name.replace(/\.[^/.]+$/, "");
                setNewTableName(fileNameWithoutExtension);
            }
        }
    };

    const resetModal = () => {
        setNewTableName('');
        setNewTableDescription('');
        setSelectedFile(null);
        setCreateMethod('manual');
        setShowCreateModal(false);
        setError('');
    };

    const handleDeleteTable = async (id: number) => {
        if (!confirm('Вы уверены, что хотите удалить эту таблицу?')) return;

        try {
            await tablesAPI.deleteTable(id);
            setTables(prev => prev.filter(table => table.id !== id));
        } catch (err: any) {
            setError('Не удалось удалить таблицу');
            console.error('Error deleting table:', err);
        }
    };


    const handleTogglePin = async (e: React.MouseEvent, table: DataTableResponse) => {
       e.stopPropagation(); // не дать клику всплыть на карточку (у карточки cursor: pointer, но открытия таблицы по клику на неё пока нет — на будущее)
       const wasPinned = table.is_pinned;
        // Оптимистично обновляем UI сразу, откатываем при ошибке
        setTables(prev =>
            prev
                .map(t => t.id === table.id ? {...t, is_pinned: !wasPinned} : t)
                .sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned))
        );

        try {
            if (wasPinned) {
                await tablesAPI.unpinTable(table.id);
            } else {
                await tablesAPI.pinTable(table.id);
            }
        } catch (err: any) {
            setError('Не удалось изменить закрепление');
            console.error('Error toggling pin:', err);
            // откат при ошибке
            setTables(prev =>
                prev
                    .map(t => t.id === table.id ? {...t, is_pinned: wasPinned} : t)
                    .sort((a, b) => Number(b.is_pinned) - Number(a.is_pinned))
            );
        }
    };

    const openDuplicateModal = (table: DataTableResponse) => {
        setDuplicatingTable(table);
        setDuplicateName(`${table.name} (копия)`);
        setDuplicateWithRows(true);
    };

    const closeDuplicateModal = () => {
        setDuplicatingTable(null);
        setDuplicateName('');
        setIsDuplicating(false);
    };

    const handleDuplicateTable = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!duplicatingTable) return;

        try {
            setIsDuplicating(true);
            const newTable = await tablesAPI.duplicateTable(duplicatingTable.id, {
                name: duplicateName.trim() || undefined,
                withRows: duplicateWithRows,
            });
            setTables(prev => [newTable, ...prev]);
            closeDuplicateModal();
        } catch (err: any) {
            setError('Не удалось дублировать таблицу');
            console.error('Error duplicating table:', err);
            setIsDuplicating(false);
        }
    };

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('ru-RU', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };


    const handleSelectSuggestion = (table: DataTableResponse) => {
        setShowSuggestions(false);
        setSearchQuery('');
        navigate(`/data/${table.id}/rows`);
    };

    if (loading) {
        return (
            <div style={styles.loadingContainer}>
                <div style={styles.loadingSpinner}></div>
                <p>Загрузка таблиц...</p>
            </div>
        );
    }

    return (
        <div style={styles.container}>
            <SidebarWithToggle/>

            {/* Header */}
            <header style={styles.header}>
                <div style={styles.headerContent}>
                    <h1 style={styles.title}>Мои таблицы</h1>
                    <div style={styles.headerActions}>
                        <button
                            style={styles.createButton}
                            onClick={() => setShowCreateModal(true)}
                        >
                            + Новая таблица
                        </button>
                        <button
                            style={styles.trashButton}
                            onClick={() => navigate('/trash')}
                        >
                            🗑 Корзина
                        </button>

                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main style={styles.main}>
                {/* Search Bar */}
                <div style={styles.searchContainer}>
                    <div style={styles.searchWrapper}>
                        <input
                            style={styles.searchInput}
                            type="text"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            onFocus={() => searchResults.length > 0 && setShowSuggestions(true)}
                            onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
                            placeholder="Поиск таблиц..."
                        />
                        {isSearching && <div style={styles.searchSpinner}/>}
                        {showSuggestions && searchResults.length > 0 && (
                            <div style={styles.suggestions}>
                                {searchResults.map((table) => (
                                    <div
                                        key={table.id}
                                        style={styles.suggestionItem}
                                        onMouseDown={() => handleSelectSuggestion(table)}
                                    >
                                        <span style={styles.suggestionName}>{table.name}</span>
                                        {table.description && (
                                            <span style={styles.suggestionDesc}>{table.description}</span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                        {showSuggestions && searchResults.length === 0 && !isSearching && searchQuery.trim() && (
                            <div style={styles.suggestions}>
                                <div style={styles.noResults}>Ничего не найдено</div>
                            </div>
                        )}
                    </div>
                </div>
                {error && (
                    <div style={styles.error}>
                        {error}
                        <button onClick={() => setError('')} style={styles.closeError}>×</button>
                    </div>
                )}

                {tables.length === 0 ? (
                    <div style={styles.emptyState}>
                        <div style={styles.emptyIcon}>📊</div>
                        <h2>У вас пока нет таблиц</h2>
                        <p>Создайте свою первую таблицу чтобы начать работу</p>
                        <button
                            style={styles.emptyCreateButton}
                            onClick={() => setShowCreateModal(true)}
                        >
                            Создать таблицу
                        </button>
                    </div>
                ) : (
                    <div style={styles.tableGrid}>
                        {tables.map((table) => (
                            <div key={table.id} style={styles.tableCard}>
                                <div style={styles.tableHeader}>
                                    <h3 style={styles.tableName}>{table.name}</h3>
                                    <button
                                        style={styles.pinButton}
                                        onClick={(e) => handleTogglePin(e, table)}
                                        aria-label={table.is_pinned ? 'Открепить' : 'Закрепить'}
                                        title={table.is_pinned ? 'Открепить' : 'Закрепить'}
                                    >
                                        {table.is_pinned ? '★' : '☆'}
                                    </button>
                                    {table.is_public && (
                                        <span style={styles.publicBadge}>Публичная</span>
                                    )}
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
                                        <span style={styles.metaLabel}>Создана:</span>
                                        <span>{formatDate(table.created_at)}</span>
                                    </div>
                                </div>

                                <div style={styles.tableActions}>
                                    <button
                                        style={styles.actionButton}
                                        onClick={() => navigate(`/data/${table.id}/rows`)}
                                    >
                                        📊 Открыть
                                    </button>
                                    <button
                                        style={styles.actionButton}
                                        onClick={() => openDuplicateModal(table)}
                                    >
                                        📄 Дублировать
                                    </button>
                                    <button
                                        style={{...styles.actionButton, ...styles.deleteButton}}
                                        onClick={() => handleDeleteTable(table.id)}
                                    >
                                        🗑️ Удалить
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </main>

            {/* Create Table Modal */}
            {showCreateModal && (
                <div style={styles.modalOverlay}>
                    <div style={styles.modal}>
                        <h2 style={styles.modalTitle}>Создать новую таблицу</h2>

                        {/* Метод создания */}
                        <div style={styles.methodSelector}>
                            <button
                                type="button"
                                style={{
                                    ...styles.methodButton,
                                    ...(createMethod === 'manual' ? styles.methodButtonActive : {})
                                }}
                                onClick={() => setCreateMethod('manual')}
                            >
                                📝 Создать вручную
                            </button>
                            <button
                                type="button"
                                style={{
                                    ...styles.methodButton,
                                    ...(createMethod === 'excel' ? styles.methodButtonActive : {})
                                }}
                                onClick={() => setCreateMethod('excel')}
                            >
                                📊 Загрузить из Excel
                            </button>
                        </div>

                        <form onSubmit={handleCreateTable}>
                            {/* Общие поля */}
                            <div style={styles.formGroup}>
                                <label style={styles.label}>Название таблицы *</label>
                                <input
                                    style={styles.input}
                                    type="text"
                                    value={newTableName}
                                    onChange={(e) => setNewTableName(e.target.value)}
                                    placeholder="Введите название таблицы"
                                    required
                                    autoFocus
                                />
                            </div>

                            <div style={styles.formGroup}>
                                <label style={styles.label}>Описание</label>
                                <textarea
                                    style={styles.textarea}
                                    value={newTableDescription}
                                    onChange={(e) => setNewTableDescription(e.target.value)}
                                    placeholder="Необязательное описание таблицы"
                                    rows={3}
                                />
                            </div>

                            {/* Поля для загрузки Excel */}
                            {createMethod === 'excel' && (
                                <div style={styles.formGroup}>
                                    <label style={styles.label}>Файл Excel *</label>
                                    <div style={styles.fileUploadArea}>
                                        <input
                                            type="file"
                                            accept=".xlsx,.xls,.csv"
                                            onChange={handleFileSelect}
                                            style={styles.fileInput}
                                            id="file-upload"
                                        />
                                        <label htmlFor="file-upload" style={styles.fileUploadLabel}>
                                            {selectedFile ? (
                                                <div style={styles.fileSelected}>
                                                    <span>📎 {selectedFile.name}</span>
                                                    <span style={styles.fileSize}>
                            ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                          </span>
                                                </div>
                                            ) : (
                                                <div style={styles.filePlaceholder}>
                                                    <span>📁 Выберите файл Excel или CSV</span>
                                                    <span style={styles.fileHint}>Поддерживаемые форматы: .xlsx, .xls, .csv</span>
                                                </div>
                                            )}
                                        </label>
                                    </div>
                                </div>
                            )}

                            <div style={styles.modalActions}>
                                <button
                                    type="button"
                                    style={styles.cancelButton}
                                    onClick={resetModal}
                                    disabled={isUploading}
                                >
                                    Отмена
                                </button>
                                <button
                                    type="submit"
                                    style={styles.submitButton}
                                    disabled={isUploading || !newTableName.trim() || (createMethod === 'excel' && !selectedFile)}
                                >
                                    {isUploading ? (
                                        <div style={styles.buttonLoading}>
                                            <div style={styles.smallSpinner}></div>
                                            Загрузка...
                                        </div>
                                    ) : (
                                        createMethod === 'excel' ? 'Загрузить файл' : 'Создать таблицу'
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Duplicate Table Modal */}
            {duplicatingTable && (
                <div style={styles.modalOverlay}>
                    <div style={styles.modal}>
                        <h2 style={styles.modalTitle}>Дублировать таблицу</h2>

                        <form onSubmit={handleDuplicateTable}>
                            <div style={styles.formGroup}>
                                <label style={styles.label}>Название новой таблицы</label>
                                <input
                                    style={styles.input}
                                    type="text"
                                    value={duplicateName}
                                    onChange={(e) => setDuplicateName(e.target.value)}
                                    placeholder={duplicatingTable.name}
                                    autoFocus
                                />
                            </div>

                            <div style={styles.formGroup}>
                                <label style={styles.checkboxLabel}>
                                    <input
                                        type="checkbox"
                                        checked={duplicateWithRows}
                                        onChange={(e) => setDuplicateWithRows(e.target.checked)}
                                    />
                                    Скопировать данные (строки)
                                </label>
                            </div>

                            <div style={styles.modalActions}>
                                <button
                                    type="button"
                                    style={styles.cancelButton}
                                    onClick={closeDuplicateModal}
                                    disabled={isDuplicating}
                                >
                                    Отмена
                                </button>
                                <button
                                    type="submit"
                                    style={styles.submitButton}
                                    disabled={isDuplicating}
                                >
                                    {isDuplicating ? (
                                        <div style={styles.buttonLoading}>
                                            <div style={styles.smallSpinner}></div>
                                            Дублирование...
                                        </div>
                                    ) : (
                                        'Дублировать'
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

const styles: Record<string, React.CSSProperties> = {
    container: {
        minHeight: '100vh',
        background: colors.canvasSoft,
    },
    header: {
        background: colors.canvas,
        borderBottom: `1px solid ${colors.hairline}`,
        padding: `${spacing.md}px 0`,
    },
    headerContent: {
        maxWidth: '1200px',
        margin: '0 auto',
        padding: `0 ${spacing.lg}px`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    title: {
        ...typography.displayMd,
        color: colors.ink,
        margin: 0,
    },
    headerActions: {
        display: 'flex',
        gap: spacing.sm,
        alignItems: 'center',
    },
    createButton: {
        ...typography.buttonMd,
        background: colors.primary,
        color: colors.onPrimary,
        border: 'none',
        padding: `0 ${spacing.md}px`,
        height: 32,
        borderRadius: rounded.sm,
        cursor: 'pointer',
    },
    main: {
        maxWidth: '1200px',
        margin: '0 auto',
        padding: `${spacing.xl}px ${spacing.lg}px`,
    },
    loadingContainer: {
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '50vh',
        gap: spacing.md,
        color: colors.body,
    },
    loadingSpinner: {
        width: 40,
        height: 40,
        border: `4px solid ${colors.hairline}`,
        borderTop: `4px solid ${colors.primary}`,
        borderRadius: rounded.full,
        animation: 'spin 1s linear infinite',
    },
    error: {
        ...typography.bodySm,
        background: colors.errorSoft,
        border: `1px solid ${colors.errorSoft}`,
        color: colors.errorDeep,
        padding: spacing.md,
        borderRadius: rounded.sm,
        marginBottom: spacing.lg,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    closeError: {
        background: 'none',
        border: 'none',
        fontSize: 18,
        cursor: 'pointer',
        color: colors.errorDeep,
    },
    emptyState: {
        ...typography.bodyMd,
        textAlign: 'center',
        padding: `${spacing["4xl"]}px ${spacing.lg}px`,
        background: colors.canvasSoft,
        borderRadius: rounded.lg,
        color: colors.body,
    },
    emptyIcon: {
        fontSize: 64,
        marginBottom: spacing.md,
    },
    emptyCreateButton: {
        ...typography.buttonLg,
        background: colors.primary,
        color: colors.onPrimary,
        border: 'none',
        padding: `0 ${spacing.lg}px`,
        height: 48,
        borderRadius: rounded.pill,
        cursor: 'pointer',
        marginTop: spacing.md,
    },
    tableGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
        gap: spacing.lg,
    },
    tableCard: {
        background: colors.canvas,
        borderRadius: rounded.md,
        padding: spacing.lg,
        boxShadow: shadowLevel3,
        transition: 'box-shadow 0.2s',
        cursor: 'pointer',
    },
    tableHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: spacing.sm,
    },
    tableName: {
        ...typography.bodyMdStrong,
        color: colors.ink,
        margin: 0,
        flex: 1,
    },
    publicBadge: {
        ...typography.caption,
        background: colors.canvasSoft,
        color: colors.body,
        padding: `0 ${spacing.xs}px`,
        borderRadius: rounded.full,
    },
    tableDescription: {
        ...typography.bodySm,
        color: colors.body,
        marginBottom: spacing.md,
    },
    tableMeta: {
        display: 'flex',
        flexDirection: 'column',
        gap: spacing.xs,
        marginBottom: spacing.lg,
    },
    metaItem: {
        ...typography.bodySm,
        display: 'flex',
        justifyContent: 'space-between',
        color: colors.ink,
    },
    metaLabel: {
        color: colors.body,
        fontWeight: 500,
    },
    tableActions: {
        display: 'flex',
        gap: spacing.xs,
    },
    actionButton: {
        ...typography.bodySm,
        flex: 1,
        background: colors.canvasSoft,
        border: `1px solid ${colors.hairline}`,
        padding: `${spacing.xs}px ${spacing.sm}px`,
        borderRadius: rounded.sm,
        cursor: 'pointer',
        transition: 'background-color 0.2s',
    },
    deleteButton: {
        background: colors.errorSoft,
        borderColor: colors.errorSoft,
        color: colors.errorDeep,
        flex: 'none',
        width: 'auto',
    },
    modalOverlay: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(23, 23, 23, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
    },
    modal: {
        background: colors.canvas,
        borderRadius: rounded.lg,
        padding: spacing.xl,
        width: '90%',
        maxWidth: 500,
        boxShadow: shadowLevel5,
    },
    modalTitle: {
        ...typography.displaySm,
        marginBottom: spacing.lg,
        color: colors.ink,
    },
    methodSelector: {
        display: 'flex',
        gap: spacing.xs,
        marginBottom: spacing.lg,
        background: colors.canvasSoft,
        padding: spacing.xxs,
        borderRadius: rounded.sm,
    },
    methodButton: {
        ...typography.bodySmStrong,
        flex: 1,
        padding: `${spacing.sm}px ${spacing.md}px`,
        border: 'none',
        background: 'transparent',
        borderRadius: rounded.sm,
        cursor: 'pointer',
        color: colors.body,
        transition: 'all 0.2s',
    },
    methodButtonActive: {
        background: colors.canvas,
        boxShadow: shadowLevel2,
        color: colors.ink,
    },
    formGroup: {
        marginBottom: spacing.md,
    },
    label: {
        ...typography.bodySmStrong,
        display: 'block',
        marginBottom: spacing.xs,
        color: colors.body,
    },
    checkboxLabel: {
        ...typography.bodySm,
        display: 'flex',
        alignItems: 'center',
        gap: spacing.xs,
        color: colors.ink,
        cursor: 'pointer',
    },
    input: {
        ...typography.bodyMd,
        width: '100%',
        height: 40,
        padding: `0 ${spacing.sm}px`,
        border: `1px solid ${colors.hairline}`,
        borderRadius: rounded.sm,
        boxSizing: 'border-box',
        background: colors.canvas,
        color: colors.ink,
    },
    textarea: {
        ...typography.bodyMd,
        width: '100%',
        padding: spacing.sm,
        border: `1px solid ${colors.hairline}`,
        borderRadius: rounded.sm,
        fontFamily: 'inherit',
        resize: 'vertical',
        boxSizing: 'border-box',
        background: colors.canvas,
        color: colors.ink,
    },
    fileUploadArea: {
        border: `2px dashed ${colors.hairline}`,
        borderRadius: rounded.sm,
        padding: 0,
        transition: 'border-color 0.2s',
    },
    fileInput: {
        display: 'none',
    },
    fileUploadLabel: {
        display: 'block',
        padding: spacing.lg,
        textAlign: 'center',
        cursor: 'pointer',
        color: colors.body,
    },
    filePlaceholder: {
        display: 'flex',
        flexDirection: 'column',
        gap: spacing.xs,
    },
    fileSelected: {
        display: 'flex',
        flexDirection: 'column',
        gap: spacing.xxs,
        color: colors.link,
    },
    fileSize: {
        ...typography.caption,
        color: colors.mute,
    },
    fileHint: {
        ...typography.caption,
        color: colors.mute,
    },
    modalActions: {
        display: 'flex',
        gap: spacing.sm,
        justifyContent: 'flex-end',
        marginTop: spacing.lg,
    },
    cancelButton: {
        ...typography.bodySmStrong,
        background: colors.canvas,
        color: colors.ink,
        border: `1px solid ${colors.hairline}`,
        padding: `${spacing.xs}px ${spacing.lg}px`,
        borderRadius: rounded.pill,
        cursor: 'pointer',
    },
    submitButton: {
        ...typography.bodySmStrong,
        background: colors.primary,
        color: colors.onPrimary,
        border: 'none',
        padding: `${spacing.xs}px ${spacing.lg}px`,
        borderRadius: rounded.pill,
        cursor: 'pointer',
        minWidth: 120,
    },
    buttonLoading: {
        display: 'flex',
        alignItems: 'center',
        gap: spacing.xs,
        justifyContent: 'center',
    },
    smallSpinner: {
        width: 16,
        height: 16,
        border: '2px solid transparent',
        borderTop: `2px solid ${colors.onPrimary}`,
        borderRadius: rounded.full,
        animation: 'spin 1s linear infinite',
    },
    menuButton: {
        background: 'transparent',
        border: 'none',
        fontSize: 24,
        cursor: 'pointer',
        padding: spacing.xs,
        lineHeight: 1,
        color: colors.ink,
    },
    searchContainer: {
        marginBottom: spacing.lg,
    },
    searchWrapper: {
        position: 'relative',
        maxWidth: 480,
    },
    searchInput: {
        ...typography.bodyMd,
        width: '100%',
        height: 48,
        padding: `0 ${spacing.md}px`,
        border: `1px solid ${colors.hairline}`,
        borderRadius: rounded.sm,
        boxSizing: 'border-box' as const,
        outline: 'none',
        background: colors.canvas,
        color: colors.ink,
    },
    searchSpinner: {
        position: 'absolute',
        right: spacing.sm,
        top: '50%',
        transform: 'translateY(-50%)',
        width: 16,
        height: 16,
        border: `2px solid ${colors.hairline}`,
        borderTop: `2px solid ${colors.primary}`,
        borderRadius: rounded.full,
        animation: 'spin 1s linear infinite',
    },
    suggestions: {
        position: 'absolute',
        top: '100%',
        left: 0,
        right: 0,
        background: colors.canvas,
        borderRadius: rounded.sm,
        boxShadow: shadowLevel5,
        zIndex: 100,
        marginTop: spacing.xxs,
        overflow: 'hidden',
    },
    suggestionItem: {
        padding: `${spacing.sm}px ${spacing.md}px`,
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column' as const,
        gap: 2,
        borderBottom: `1px solid ${colors.hairline}`,
    },
    suggestionName: {
        ...typography.bodySmStrong,
        color: colors.ink,
    },
    suggestionDesc: {
        ...typography.caption,
        color: colors.body,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap' as const,
    },
    noResults: {
        ...typography.bodySm,
        padding: `${spacing.sm}px ${spacing.md}px`,
        color: colors.body,
        textAlign: 'center' as const,
    },
    trashButton: {
        ...typography.buttonMd,
        background: colors.canvas,
        color: colors.ink,
        border: `1px solid ${colors.hairline}`,
        padding: `0 ${spacing.md}px`,
        height: 32,
        borderRadius: rounded.sm,
        cursor: 'pointer',
    },

    pinButton: {
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        fontSize: 20,
        lineHeight: 1,
        padding: 0,
        color: colors.primary,
        flexShrink: 0,
    },
};

export default TablesPage;