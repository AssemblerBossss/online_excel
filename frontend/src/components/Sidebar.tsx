import React from 'react';
import {useNavigate} from 'react-router-dom';
import api from '../api/axiosInstance';

interface SidebarProps {
    isOpen: boolean;
    onClose: () => void;
    onOpenChat: () => void;
    unreadChatsCount: number;
}

const Sidebar: React.FC<SidebarProps> = ({isOpen, onClose, onOpenChat, unreadChatsCount}) => {
    const navigate = useNavigate();

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
        {label: 'Мои таблицы', path: '/tables', icon: '📊'},
        {label: 'Чаты', action: onOpenChat, icon: '💬', badge: unreadChatsCount},
        {label: 'Аккаунт', path: '/profile', icon: '👤'},
        {label: 'О нас', path: '/about', icon: 'ℹ️'},
        {label: 'Выйти', action: handleLogout, icon: '🚪'},
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
                >
                    <div style={{
                        ...styles.line,
                        transform: isOpen ? 'rotate(45deg)' : 'rotate(0)',
                        top: isOpen ? '13px' : '6px',
                    }}/>
                    <div style={{
                        ...styles.line,
                        opacity: isOpen ? 0 : 1,
                        top: '13px',
                    }}/>
                    <div style={{
                        ...styles.line,
                        transform: isOpen ? 'rotate(-45deg)' : 'rotate(0)',
                        top: isOpen ? '13px' : '20px',
                    }}/>
                </button>

                <div style={styles.content}>
                    <nav style={styles.nav}>
                        {menuItems.map((item, index) => (
                            <button
                                key={index}
                                style={styles.menuItem}
                                onClick={() => {
                                    if (item.action) {
                                        item.action();
                                    } else if (item.path) {
                                        navigate(item.path);
                                        onClose();
                                    }
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.backgroundColor = '#f0f0f0';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.backgroundColor = 'transparent';
                                }}
                            >
                                <span style={styles.icon}>{item.icon}</span>
                                <span style={styles.label}>{item.label}</span>
                                {!!item.badge && (
                                    <span style={styles.badge}>{item.badge}</span>
                                )}
                            </button>
                        ))}
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
        backgroundColor: 'rgba(0, 0, 0, 0.3)',
        zIndex: 999,
        animation: 'fadeIn 0.2s ease',
    },
    sidebar: {
        position: 'fixed',
        top: 0,
        left: 0,
        width: 260,
        height: '100%',
        backgroundColor: '#fff',
        boxShadow: '2px 0 12px rgba(0, 0, 0, 0.1)',
        zIndex: 1000,
        transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        display: 'flex',
        flexDirection: 'column',
    },
    toggleButton: {
        position: 'absolute',
        top: 16,
        left: 16,
        width: 30,
        height: 30,
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        padding: 0,
        zIndex: 10,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
    },
    line: {
        position: 'absolute',
        width: 24,
        height: 2,
        backgroundColor: '#333',
        borderRadius: 2,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        left: '50%',
        marginLeft: -12,
    },
    content: {
        display: 'flex',
        flexDirection: 'column',
        padding: '16px 0',
        paddingTop: '70px',
    },
    nav: {
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
    },
    menuItem: {
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '12px 20px',
        border: 'none',
        background: 'transparent',
        cursor: 'pointer',
        fontSize: 15,
        color: '#2d2d2d',
        transition: 'background-color 0.15s ease',
        textAlign: 'left',
        fontWeight: 400,
        borderRadius: 0,
    },
    icon: {
        fontSize: 18,
        width: 20,
        textAlign: 'center',
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
    },
};