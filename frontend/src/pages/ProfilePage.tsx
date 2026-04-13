import React, {useState, useEffect} from "react";
import {useNavigate} from "react-router-dom";
import {getUserProfile, UserProfile} from "../api/users";
import SidebarWithToggle from '../components/SidebarWithToggle';

const ProfilePage: React.FC = () => {
    const navigate = useNavigate();
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        const fetchProfile = async () => {
            try {
                const data = await getUserProfile();
                setProfile(data);
            } catch (err: any) {
                setError(err.response?.data?.detail || "Ошибка загрузки профиля");
            } finally {
                setLoading(false);
            }
        };

        fetchProfile();
    }, []);

    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString("ru-RU", {
            year: "numeric",
            month: "long",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    const getRoleText = (role: string) => {
        const roles: Record<string, string> = {
            admin: "Администратор",
            editor: "Редактор",
            viewer: "Просмотр",
        };
        return roles[role.toLowerCase()] || role;
    };

    if (loading) {
        return (
            <div style={styles.container}>
                <div style={styles.card}>
                    <p>Загрузка...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div style={styles.container}>
                <div style={styles.card}>
                    <p style={styles.error}>{error}</p>
                    <button style={styles.button} onClick={() => navigate("/tables")}>
                        Вернуться к таблицам
                    </button>
                </div>
            </div>
        );
    }


    return (
        <div style={styles.pageContainer}>
            <SidebarWithToggle/>

            <div style={styles.header}>
                <h1 style={styles.headerTitle}>Профиль</h1>
            </div>

            <div style={styles.container}>  {/* ← ДОБАВИТЬ внутренний container */}
                <div style={styles.card}>
                    <h2 style={styles.title}>Профиль пользователя</h2>

                    {profile && (
                        <div style={styles.profileInfo}>
                            <div style={styles.infoRow}>
                                <span style={styles.label}>Email:</span>
                                <span style={styles.value}>{profile.email}</span>
                            </div>

                            <div style={styles.infoRow}>
                                <span style={styles.label}>Имя:</span>
                                <span style={styles.value}>{profile.first_name}</span>
                            </div>

                            <div style={styles.infoRow}>
                                <span style={styles.label}>Фамилия:</span>
                                <span style={styles.value}>{profile.last_name}</span>
                            </div>

                            <div style={styles.infoRow}>
                                <span style={styles.label}>Роль:</span>
                                <span style={styles.value}>{getRoleText(profile.role)}</span>
                            </div>

                            <div style={styles.infoRow}>
                                <span style={styles.label}>Статус:</span>
                                <span style={styles.value}>
                {profile.is_active ? (
                    <span style={styles.statusActive}>Активен</span>
                ) : (
                    <span style={styles.statusInactive}>Неактивен</span>
                )}
              </span>
                            </div>

                            <div style={styles.infoRow}>
                                <span style={styles.label}>Дата регистрации:</span>
                                <span style={styles.value}>{formatDate(profile.created_at)}</span>
                            </div>
                        </div>
                    )}

                    <div style={styles.buttonGroup}>
                        <button
                            style={styles.button}
                            onClick={() => navigate("/tables")}
                        >
                            Вернуться к таблицам
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProfilePage;

const styles: Record<string, React.CSSProperties> = {
    pageContainer: {  // ← ДОБАВИТЬ (новый контейнер для всей страницы)
        minHeight: '100vh',
        background: '#f0f2f5',
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
    container: {  // ← ИЗМЕНИТЬ (убери minHeight и background)
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 40,
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    },
    card: {
        width: 500,
        padding: 40,
        borderRadius: 12,
        background: "#fff",
        boxShadow: "0 8px 32px rgba(0,0,0,0.1)",
    },
    title: {
        marginBottom: 32,
        color: "#333",
        fontSize: 28,
        fontWeight: 600,
        textAlign: "center",
    },
    error: {
        color: "#ff4757",
        marginBottom: 16,
        padding: 12,
        background: "#ffe6e6",
        borderRadius: 6,
        fontSize: 14,
        textAlign: "center",
    },
    profileInfo: {
        display: "flex",
        flexDirection: "column",
        gap: 20,
    },
    infoRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: 16,
        background: "#f8f9fa",
        borderRadius: 8,
        borderLeft: "4px solid #4CAF50",
    },
    label: {
        fontSize: 14,
        fontWeight: 600,
        color: "#555",
    },
    value: {
        fontSize: 16,
        color: "#333",
        fontWeight: 500,
    },
    statusActive: {
        color: "#4CAF50",
        fontWeight: 600,
    },
    statusInactive: {
        color: "#ff4757",
        fontWeight: 600,
    },
    buttonGroup: {
        marginTop: 32,
        display: "flex",
        gap: 12,
        justifyContent: "center",
    },
    button: {
        padding: 14,
        paddingLeft: 28,
        paddingRight: 28,
        borderRadius: 6,
        border: "none",
        background: "#4CAF50",
        color: "#fff",
        fontSize: 16,
        fontWeight: 600,
        cursor: "pointer",
        transition: "background-color 0.2s",
    },
};