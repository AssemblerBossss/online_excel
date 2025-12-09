import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { tablesAPI, DataTableResponse } from '../api/tables';
import api from "../api/axiosInstance";

const TablesPage: React.FC = () => {
  const navigate = useNavigate();
  const [tables, setTables] = useState<DataTableResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTableName, setNewTableName] = useState('');
  const [newTableDescription, setNewTableDescription] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [createMethod, setCreateMethod] = useState<'manual' | 'excel'>('manual');

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
          { name: 'A', type: 'string' },
          { name: 'B', type: 'number' },
          { name: 'C', type: 'string' }
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
      const response = await api.post('/tables/process_excel', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('ru-RU', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleLogout = async () => {
    try {
      await api.post("/auth/logout");
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      navigate('/login');
    }
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
              style={styles.logoutButton}
              onClick={handleLogout}
            >
              Выйти
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main style={styles.main}>
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
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: '100vh',
    background: '#f8fafc',
  },
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
  title: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#1a202c',
    margin: 0,
  },
  headerActions: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
  },
  createButton: {
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  logoutButton: {
    background: '#ef4444',
    color: 'white',
    border: 'none',
    padding: '8px 16px',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  main: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '32px 20px',
  },
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '50vh',
    gap: '16px',
  },
  loadingSpinner: {
    width: '40px',
    height: '40px',
    border: '4px solid #e2e8f0',
    borderTop: '4px solid #3b82f6',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
  error: {
    background: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#dc2626',
    padding: '16px',
    borderRadius: '8px',
    marginBottom: '24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  closeError: {
    background: 'none',
    border: 'none',
    fontSize: '18px',
    cursor: 'pointer',
    color: '#dc2626',
  },
  emptyState: {
    textAlign: 'center',
    padding: '80px 20px',
    color: '#64748b',
  },
  emptyIcon: {
    fontSize: '64px',
    marginBottom: '16px',
  },
  emptyCreateButton: {
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    padding: '12px 24px',
    borderRadius: '8px',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    marginTop: '16px',
  },
  tableGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
    gap: '24px',
  },
  tableCard: {
    background: 'white',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    padding: '24px',
    transition: 'transform 0.2s, box-shadow 0.2s',
    cursor: 'pointer',
  },
  tableHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '12px',
  },
  tableName: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#1a202c',
    margin: 0,
    flex: 1,
  },
  publicBadge: {
    background: '#dbeafe',
    color: '#1d4ed8',
    padding: '4px 8px',
    borderRadius: '12px',
    fontSize: '12px',
    fontWeight: '500',
  },
  tableDescription: {
    color: '#64748b',
    fontSize: '14px',
    lineHeight: '1.5',
    marginBottom: '16px',
  },
  tableMeta: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    marginBottom: '20px',
  },
  metaItem: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '14px',
  },
  metaLabel: {
    color: '#64748b',
    fontWeight: '500',
  },
  tableActions: {
    display: 'flex',
    gap: '8px',
  },
  actionButton: {
    flex: 1,
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    padding: '8px 12px',
    borderRadius: '6px',
    fontSize: '14px',
    cursor: 'pointer',
    transition: 'background-color 0.2s',
  },
  deleteButton: {
    background: '#fef2f2',
    borderColor: '#fecaca',
    color: '#dc2626',
    flex: 'none',
    width: 'auto',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    background: 'white',
    borderRadius: '12px',
    padding: '32px',
    width: '90%',
    maxWidth: '500px',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
  },
  modalTitle: {
    fontSize: '24px',
    fontWeight: '600',
    marginBottom: '24px',
    color: '#1a202c',
  },
  methodSelector: {
    display: 'flex',
    gap: '8px',
    marginBottom: '24px',
    background: '#f8fafc',
    padding: '4px',
    borderRadius: '8px',
  },
  methodButton: {
    flex: 1,
    padding: '12px 16px',
    border: 'none',
    background: 'transparent',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '14px',
    fontWeight: '500',
    transition: 'all 0.2s',
  },
  methodButtonActive: {
    background: 'white',
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    color: '#3b82f6',
  },
  formGroup: {
    marginBottom: '20px',
  },
  label: {
    display: 'block',
    marginBottom: '8px',
    fontWeight: '500',
    color: '#374151',
  },
  input: {
    width: '100%',
    padding: '12px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '16px',
    boxSizing: 'border-box',
  },
  textarea: {
    width: '100%',
    padding: '12px',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '16px',
    fontFamily: 'inherit',
    resize: 'vertical',
    boxSizing: 'border-box',
  },
  fileUploadArea: {
    border: '2px dashed #d1d5db',
    borderRadius: '8px',
    padding: '0',
    transition: 'border-color 0.2s',
  },
  fileInput: {
    display: 'none',
  },
  fileUploadLabel: {
    display: 'block',
    padding: '24px',
    textAlign: 'center',
    cursor: 'pointer',
    color: '#64748b',
  },
  filePlaceholder: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  fileSelected: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    color: '#059669',
  },
  fileSize: {
    fontSize: '12px',
    color: '#6b7280',
  },
  fileHint: {
    fontSize: '12px',
    color: '#9ca3af',
  },
  modalActions: {
    display: 'flex',
    gap: '12px',
    justifyContent: 'flex-end',
    marginTop: '24px',
  },
  cancelButton: {
    background: '#f3f4f6',
    color: '#374151',
    border: '1px solid #d1d5db',
    padding: '10px 20px',
    borderRadius: '8px',
    fontSize: '14px',
    cursor: 'pointer',
  },
  submitButton: {
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    minWidth: '120px',
  },
  buttonLoading: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    justifyContent: 'center',
  },
  smallSpinner: {
    width: '16px',
    height: '16px',
    border: '2px solid transparent',
    borderTop: '2px solid white',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
};

// Добавляем CSS анимацию
const styleSheet = document.styleSheets[0];
styleSheet.insertRule(`
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`, styleSheet.cssRules.length);

export default TablesPage;