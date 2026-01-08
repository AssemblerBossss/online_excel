import React from 'react';
import { useNavigate } from 'react-router-dom';
import SidebarWithToggle from '../components/SidebarWithToggle';

const AboutPage: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div style={styles.container}>
            <SidebarWithToggle />

            <div style={styles.header}>
                <h1 style={styles.headerTitle}>О нас</h1>
            </div>

            <div style={styles.content}>
                <div style={styles.card}>
                    <h2 style={styles.title}>О проекте</h2>

                    <div style={styles.section}>
                        <h3 style={styles.subtitle}>Описание</h3>
                        <p style={styles.text}>
                            Онлайн Excel - это современное веб-приложение для работы с табличными данными.
                            Создавайте, редактируйте и управляйте своими таблицами прямо в браузере.
                        </p>
                    </div>

                    <div style={styles.section}>
                        <h3 style={styles.subtitle}>Возможности</h3>
                        <ul style={styles.list}>
                            <li style={styles.listItem}>Создание и редактирование таблиц</li>
                            <li style={styles.listItem}>Импорт данных из Excel файлов</li>
                            <li style={styles.listItem}>Автоматическое определение типов данных</li>
                            <li style={styles.listItem}>Управление доступом к таблицам</li>
                            <li style={styles.listItem}>Публичные и приватные таблицы</li>
                        </ul>
                    </div>

                    <div style={styles.section}>
                        <h3 style={styles.subtitle}>Версия</h3>
                        <p style={styles.text}>1.0.0</p>
                    </div>

                    <button style={styles.button} onClick={() => navigate('/tables')}>
                        Вернуться к таблицам
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AboutPage;

const styles: Record<string, React.CSSProperties> = {
    container: {
        minHeight: '100vh',
        background: '#f0f2f5',
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    },
    header: {
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '16px 24px',
        backgroundColor: '#fff',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
    },
    headerTitle: {
        margin: 0,
        fontSize: 20,
        fontWeight: 600,
        color: '#333',
    },
    content: {
        display: 'flex',
        justifyContent: 'center',
        padding: 40,
    },
    card: {
        width: '100%',
        maxWidth: 800,
        padding: 40,
        borderRadius: 12,
        background: '#fff',
        boxShadow: '0 8px 32px rgba(0,0,0,0.1)',
    },
    title: {
        marginBottom: 32,
        color: '#333',
        fontSize: 28,
        fontWeight: 600,
    },
    section: {
        marginBottom: 32,
    },
    subtitle: {
        fontSize: 20,
        fontWeight: 600,
        color: '#333',
        marginBottom: 12,
    },
    text: {
        fontSize: 16,
        lineHeight: 1.6,
        color: '#555',
        margin: 0,
    },
    list: {
        margin: 0,
        paddingLeft: 24,
    },
    listItem: {
        fontSize: 16,
        lineHeight: 1.8,
        color: '#555',
        marginBottom: 8,
    },
    button: {
        padding: 14,
        paddingLeft: 28,
        paddingRight: 28,
        borderRadius: 6,
        border: 'none',
        background: '#4CAF50',
        color: '#fff',
        fontSize: 16,
        fontWeight: 600,
        cursor: 'pointer',
        transition: 'background-color 0.2s',
        marginTop: 16,
    },
};
