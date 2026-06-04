import React, {useState, useEffect} from "react";
import {useNavigate} from "react-router-dom";
import {getUserProfile, updateUser, uploadAvatar, UserProfile} from "../api/users";
import SidebarWithToggle from '../components/SidebarWithToggle';

const ProfilePage: React.FC = () => {
    const navigate = useNavigate();
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [uploading, setUploading] = useState(false);

    // Флаг: открыта ли форма редактирования (true) или режим просмотра (false)
    const [isEditing, setIsEditing] = useState(false);
    // Флаг: идёт ли сейчас отправка данных на сервер (для блокировки кнопки и показа спиннера)
    const [saving, setSaving] = useState(false);
    const [formData, setFormData] = useState({
        first_name: "",
        last_name: ""
    });


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

    const handleAvatarChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file || !profile) return;
        setUploading(true);
        setError("");
        try {
            const updated = await uploadAvatar(profile.id, file);
            setProfile(updated);
        } catch (err: any) {
            setError(err.response?.data?.detail || "Не удалось загрузить аватар");
        } finally {
            setUploading(false);
            e.target.value = "";            // чтобы можно было выбрать тот же файл снова
        }
    };

    const handleEditClick = () => {
        if (!profile) return;
        // Заполняем форму текущими значениями профиля
        setFormData({
            first_name: profile.first_name,
            last_name: profile.last_name
        })
        setIsEditing(true);
    };

    const handleCancel = () => {
        setIsEditing(false);
        setError("");
    };

    const handleSave = async () => {
        if (!profile) return;
        if (formData.first_name.trim().length < 3 || formData.last_name.trim().length < 3) {
            setError("Имя и фамилия должны содержать не менее 3 символов");
            return;
        }
        setSaving(true);
        setError("");
        try {
            const updated = await updateUser(profile.id, formData);
            setProfile(updated); //обновляем отображение
            setIsEditing(false); //выходим из режима редактирования
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            if (Array.isArray(detail)) {
                // Берём сообщение из первой ошибки
                setError(detail[0]?.msg || "Не удалось сохранить изменения");
            } else {
                setError(detail || "Не удалось сохранить изменения");
            }
        } finally {
            setSaving(false);
        }
    };

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
                        <div style={styles.avatarSection}>
                            <img
                                src={profile.avatar_url ?? "/default-avatar.png"}
                                alt="Аватар"
                                style={styles.avatar}
                                onError={(e) => {
                                    const img = e.target as HTMLImageElement;
                                    img.onerror = null;
                                    img.src = "/default-avatar.png";
                                }}
                            />
                            <label style={styles.avatarUploadBtn}>
                                {uploading ? "Загрузка..." : "Изменить фото"}
                                <input
                                    type="file"
                                    accept="image/jpeg,image/png,image/webp"
                                    onChange={handleAvatarChange}
                                    disabled={uploading}
                                    style={{display: "none"}}
                                />
                            </label>
                        </div>
                    )}

                    {profile && (
                        <div style={styles.profileInfo}>
                            <div style={styles.infoRow}>
                                <span style={styles.label}>Email:</span>
                                <span style={styles.value}>{profile.email}</span>
                            </div>

                            <div style={styles.infoRow}>
                                <span style={styles.label}>Имя:</span>
                                {isEditing ? (
                                    <input
                                        style={styles.input}
                                        value={formData.first_name}
                                        onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                                    />
                                ) : (
                                    <span style={styles.value}>{profile.first_name}</span>
                            )}
                        </div>

                        <div style={styles.infoRow}>
                            <span style={styles.label}>Фамилия:</span>
                            {isEditing ? (
                                <input
                                    style={styles.input}
                                    value={formData.last_name}
                                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                                />
                            ) : (
                                <span style={styles.value}>{profile.last_name}</span>
                            )}
                        </div>

                        {/* Роль, Статус, Дата — только просмотр, без изменений */}
                        <div style={styles.infoRow}>
                            <span style={styles.label}>Роль:</span>
                            <span style={styles.value}>{getRoleText(profile.role)}</span>
                        </div>

                        <div style={styles.infoRow}>
                            <span style={styles.label}>Статус:</span>
                            <span style={styles.value}>
                            {profile.is_active
                                ? <span style={styles.statusActive}>Активен</span>
                                : <span style={styles.statusInactive}>Неактивен</span>
                            }
                            </span>
                        </div>

                        <div style={styles.infoRow}>
                            <span style={styles.label}>Дата регистрации:</span>
                            <span style={styles.value}>{formatDate(profile.created_at)}</span>
                        </div>
                    </div>
                    )}
                    {error && <p style={styles.error}>{error}</p>}
                    <div style={styles.buttonGroup}>
                        {isEditing ? (
                            <>
                                <button style={styles.button} onClick={handleSave} disabled={saving}>
                                    {saving ? "Сохранение..." : "Сохранить"}
                                </button>
                                <button style={{...styles.button, background: "#aaa"}} onClick={handleCancel}>
                                    Отмена
                                </button>
                            </>
                        ) : (
                            <>
                                <button style={styles.button} onClick={handleEditClick}>
                                    Редактировать профиль
                                </button>
                                <button style={{...styles.button, background: "#aaa"}} onClick={() => navigate("/tables")}>
                                    К таблицам
                                </button>
                            </>
                        )}
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
    avatarSection: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 12,
        marginBottom: 28,
    },
    avatar: {
        width: 120,
        height: 120,
        borderRadius: "50%",
        objectFit: "cover",
        border: "3px solid #4CAF50",
        background: "#f0f2f5",
    },
    avatarUploadBtn: {
        fontSize: 14,
        fontWeight: 600,
        color: "#4CAF50",
        cursor: "pointer",
    },

    input: {
    fontSize: 15,
    padding: "6px 10px",
    borderRadius: 6,
    border: "1px solid #4CAF50",
    outline: "none",
    width: 220,
    color: "#333",
    },
};