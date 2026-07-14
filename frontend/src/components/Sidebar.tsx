import React from 'react';
import {useLocation, useNavigate} from 'react-router-dom';
import api from '../api/axiosInstance';
import {colors, rounded, shadowLevel5, spacing, typography} from '../styles/theme';

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
    onOpenChat: () => void;
    unreadChatsCount: number;
}

const iconProps = {
    width: 18,
    height: 18,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.75,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
};

const TablesIcon = () => (
    <svg {...iconProps}>
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <path d="M3 9h18"/>
        <path d="M3 15h18"/>
        <path d="M9 3v18"/>
    </svg>
);

const ChatIcon = () => (
    <svg {...iconProps}>
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
);

const UserIcon = () => (
    <svg {...iconProps}>
        <circle cx="12" cy="8" r="4"/>
        <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
    </svg>
);

const InfoIcon = () => (
    <svg {...iconProps}>
        <circle cx="12" cy="12" r="9"/>
        <path d="M12 11v6"/>
        <path d="M12 7.5v.01"/>
    </svg>
);

const LogoutIcon = () => (
    <svg {...iconProps}>
        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
        <path d="M16 17l5-5-5-5"/>
        <path d="M21 12H9"/>
    </svg>
);

const Sidebar: React.FC<SidebarProps> = ({isOpen, onClose, onOpenChat, unreadChatsCount}) => {
    const navigate = useNavigate();
    const location = useLocation();

    const handleLogout = async () => {
        try {
            await api.post('/auth/logout');
            navigate('/login');
        } catch (err) {
            console.error('Logout error:', err);
            navigate('/login');
        }
    };

    const menuItems = [
        {label: 'Мои таблицы', path: '/tables', icon: <TablesIcon/>},
        {label: 'Чаты', action: onOpenChat, icon: <ChatIcon/>, badge: unreadChatsCount},
        {label: 'Аккаунт', path: '/profile', icon: <UserIcon/>},
        {label: 'О нас', path: '/about', icon: <InfoIcon/>},
        {label: 'Выйти', action: handleLogout, icon: <LogoutIcon/>},
    ];

    return (
        <>
            {isOpen && (
                <div style={styles.overlay} onClick={onClose}/>
            )}

            <div style={{
                ...styles.sidebar,
                transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
            }}>
                <button
                    style={styles.toggleButton}
                    onClick={onClose}
                    aria-label={isOpen ? "Закрыть меню" : "Открыть меню"}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = colors.canvasSoft2;
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                >
                    <div style={{
                        ...styles.line,
                        transform: isOpen ? 'rotate(45deg)' : 'rotate(0)',
                        top: isOpen ? '19px' : '12px',
                    }}/>
                    <div style={{
                        ...styles.line,
                        opacity: isOpen ? 0 : 1,
                        top: '19px',
                    }}/>
                    <div style={{
                        ...styles.line,
                        transform: isOpen ? 'rotate(-45deg)' : 'rotate(0)',
                        top: isOpen ? '19px' : '26px',
                    }}/>
                </button>

                <div style={styles.brand}>
                    <span style={styles.brandText}>Online Excel</span>
                </div>

                <div style={styles.content}>
                    <nav style={styles.nav}>
                        {menuItems.map((item, index) => {
                            const isActive = !!item.path && location.pathname.startsWith(item.path);
                            return (
                                <button
                                    key={index}
                                    style={{
                                        ...styles.menuItem,
                                        ...(isActive ? styles.menuItemActive : {}),
                                    }}
                                    onClick={() => {
                                        if (item.action) {
                                            item.action();
                                        } else if (item.path) {
                                            navigate(item.path);
                                            onClose();
                                        }
                                    }}
                                    onMouseEnter={(e) => {
                                        if (!isActive) e.currentTarget.style.backgroundColor = colors.canvasSoft2;
                                    }}
                                    onMouseLeave={(e) => {
                                        if (!isActive) e.currentTarget.style.backgroundColor = 'transparent';
                                    }}
                                >
                                    <span style={{...styles.icon, color: isActive ? colors.ink : colors.body}}>{item.icon}</span>
                                    <span style={styles.label}>{item.label}</span>
                                    {!!item.badge && (
                                        <span style={styles.badge}>{item.badge}</span>
                                    )}
                                </button>
                            );
                        })}
                    </nav>
                </div>
            </div>
        </>
    );
};

export default Sidebar;

const styles: Record<string, React.CSSProperties> = {
    overlay: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(23, 23, 23, 0.4)',
        zIndex: 999,
        animation: 'fadeIn 0.2s ease',
    },
    sidebar: {
        position: 'fixed',
        top: 0,
        left: 0,
        width: 260,
        height: '100%',
        backgroundColor: colors.canvas,
        boxShadow: shadowLevel5,
        zIndex: 1000,
        transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        display: 'flex',
        flexDirection: 'column',
    },
    toggleButton: {
        position: 'absolute',
        top: 16,
        left: 16,
        width: 38,
        height: 38,
        background: 'transparent',
        border: `1px solid ${colors.hairline}`,
        borderRadius: rounded.sm,
        cursor: 'pointer',
        padding: 0,
        zIndex: 10,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        transition: 'background-color 0.15s ease',
    },
    line: {
        position: 'absolute',
        width: 16,
        height: 1.5,
        backgroundColor: colors.ink,
        borderRadius: 2,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        left: '50%',
        marginLeft: -8,
    },
    brand: {
        height: 64,
        display: 'flex',
        alignItems: 'center',
        paddingLeft: 58,
        paddingRight: spacing.lg,
        borderBottom: `1px solid ${colors.hairline}`,
        flexShrink: 0,
    },
    brandText: {
        ...typography.bodySmStrong,
        color: colors.ink,
        letterSpacing: '-0.28px',
    },
    content: {
        display: 'flex',
        flexDirection: 'column',
        padding: `${spacing.md}px ${spacing.xs}px`,
    },
    nav: {
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
    },
    menuItem: {
        ...typography.bodySm,
        display: 'flex',
        alignItems: 'center',
        gap: spacing.sm,
        padding: `${spacing.sm}px ${spacing.sm}px`,
        border: 'none',
        borderLeft: '2px solid transparent',
        background: 'transparent',
        cursor: 'pointer',
        color: colors.body,
        transition: 'background-color 0.15s ease, color 0.15s ease',
        textAlign: 'left',
        borderRadius: rounded.sm,
    },
    menuItemActive: {
        backgroundColor: colors.canvasSoft2,
        borderLeft: `2px solid ${colors.primary}`,
        color: colors.ink,
    },
    icon: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 20,
        flexShrink: 0,
    },
    label: {
        fontWeight: 400,
        flex: 1,
    },
    badge: {
        background: '#4CAF50',
        color: '#fff',
        borderRadius: 10,
        fontSize: 11,
        fontWeight: 600,
        padding: '2px 7px',
        marginLeft: 8,
        flexShrink: 0,
    },
};