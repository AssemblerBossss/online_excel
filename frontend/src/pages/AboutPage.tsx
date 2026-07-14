import React from 'react';
import {useNavigate} from 'react-router-dom';
import SidebarWithToggle from '../components/SidebarWithToggle';
import {colors, rounded, shadowLevel4, spacing, typography} from '../styles/theme';

const AboutPage: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div style={styles.pageContainer}>
            <SidebarWithToggle/>

            <header style={styles.header}>
                <div style={styles.headerContent}>
                    <h1 style={styles.headerTitle}>О нас</h1>
                </div>
            </header>

            <main style={styles.main}>
                <div style={styles.card}>
                    <div style={styles.section}>
                        <h2 style={styles.subtitle}>Описание</h2>
                        <p style={styles.text}>
                            Онлайн Excel — это современное веб-приложение для работы с табличными данными.
                            Создавайте, редактируйте и управляйте своими таблицами прямо в браузере.
                        </p>
                    </div>

                    <div style={styles.section}>
                        <h2 style={styles.subtitle}>Возможности</h2>
                        <ul style={styles.list}>
                            <li style={styles.listItem}>Создание и редактирование таблиц</li>
                            <li style={styles.listItem}>Импорт данных из Excel файлов</li>
                            <li style={styles.listItem}>Автоматическое определение типов данных</li>
                            <li style={styles.listItem}>Управление доступом к таблицам</li>
                            <li style={styles.listItem}>Публичные и приватные таблицы</li>
                        </ul>
                    </div>

                    <div style={{...styles.section, marginBottom: 0}}>
                        <h2 style={styles.subtitle}>Версия</h2>
                        <span style={styles.versionBadge}>v1.0.0</span>
                    </div>

                    <div style={styles.buttonGroup}>
                        <button style={styles.buttonSecondary} onClick={() => navigate('/tables')}>
                            Вернуться к таблицам
                        </button>
                    </div>
                </div>
            </main>
        </div>
    );
};

export default AboutPage;

const styles: Record<string, React.CSSProperties> = {
    pageContainer: {
        minHeight: '100vh',
        background: colors.canvasSoft,
    },
    header: {
        background: colors.canvas,
        borderBottom: `1px solid ${colors.hairline}`,
        padding: `${spacing.md}px 0`,
    },
    headerContent: {
        maxWidth: 1200,
        margin: '0 auto',
        padding: `0 ${spacing.lg}px`,
    },
    headerTitle: {
        ...typography.displayMd,
        color: colors.ink,
        margin: 0,
    },
    main: {
        maxWidth: 720,
        margin: '0 auto',
        padding: `${spacing.xl}px ${spacing.lg}px`,
    },
    card: {
        background: colors.canvas,
        borderRadius: rounded.lg,
        padding: spacing.xl,
        boxShadow: shadowLevel4,
    },
    section: {
        marginBottom: spacing.xl,
    },
    subtitle: {
        ...typography.displaySm,
        color: colors.ink,
        marginTop: 0,
        marginBottom: spacing.sm,
    },
    text: {
        ...typography.bodyMd,
        color: colors.body,
        lineHeight: '26px',
        margin: 0,
    },
    list: {
        margin: 0,
        paddingLeft: spacing.lg,
        display: 'flex',
        flexDirection: 'column',
        gap: spacing.xs,
    },
    listItem: {
        ...typography.bodyMd,
        color: colors.body,
    },
    versionBadge: {
        ...typography.code,
        color: colors.body,
        background: colors.canvasSoft2,
        padding: `${spacing.xxs}px ${spacing.sm}px`,
        borderRadius: rounded.sm,
        display: 'inline-block',
    },
    buttonGroup: {
        marginTop: spacing.xl,
        paddingTop: spacing.lg,
        borderTop: `1px solid ${colors.hairline}`,
        display: 'flex',
        justifyContent: 'flex-end',
    },
    buttonSecondary: {
        ...typography.buttonLg,
        height: 44,
        padding: `0 ${spacing.lg}px`,
        borderRadius: rounded.pill,
        border: `1px solid ${colors.hairline}`,
        background: colors.canvas,
        color: colors.ink,
        cursor: 'pointer',
    },
};