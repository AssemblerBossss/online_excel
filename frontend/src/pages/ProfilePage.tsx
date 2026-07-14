import React, {useState, useEffect} from "react";
import {useNavigate} from "react-router-dom";
import {changePassword, getUserProfile, updateUser, uploadAvatar, UserProfile} from "../api/users";
import SidebarWithToggle from '../components/SidebarWithToggle';
import {colors, rounded, shadowLevel4, spacing, typography} from '../styles/theme';

const LockIcon = () => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
        <rect x="4" y="11" width="16" height="10" rx="2"/>
        <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
    </svg>
);

const ProfilePage: React.FC = () => {
    const navigate = useNavigate();
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [uploading, setUploading] = useState(false);

    const [isEditing, setIsEditing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [formData, setFormData] = useState({
        first_name: "",
        last_name: ""
    });

    const [isChangingPassword, setIsChangingPassword] = useState(false);
    const [passwordForm, setPasswordForm] = useState({
        old_password: "",
        new_password: "",
        confirm_password: ""
    });
    const [passwordError, setPasswordError] = useState("");
    const [passwordSaving, setPasswordSaving] = useState(false);

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
            e.target.value = ""; // чтобы можно было выбрать тот же файл снова
        }
    };

    const handleEditClick = () => {
        if (!profile) return;
        setFormData({
            first_name: profile.first_name,
            last_name: profile.last_name
        });
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
            setProfile(updated);
            setIsEditing(false);
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            if (Array.isArray(detail)) {
                setError(detail[0]?.msg || "Не удалось сохранить изменения");
            } else {
                setError(detail || "Не удалось сохранить изменения");
            }
        } finally {
            setSaving(false);
        }
    };

    const handlePasswordOpen = () => {
        setIsChangingPassword(true);
        setPasswordError("");
        setPasswordForm({
            old_password: "",
            new_password: "",
            confirm_password: ""
        });
    };

    const handlePasswordCancel = () => {
        setIsChangingPassword(false);
        setPasswordError("");
    };

    const handlePasswordSave = async () => {
        if (passwordForm.new_password !== passwordForm.confirm_password) {
            setPasswordError("Новый пароль и подтверждение не совпадают");
            return;
        }
        if (passwordForm.new_password === passwordForm.old_password) {
            setPasswordError("Новый пароль совпадает со старым");
            return;
        }
        if (passwordForm.new_password.length < 5) {
            setPasswordError("Пароль должен содержать не менее 5 символов");
            return;
        }

        setPasswordSaving(true);
        setPasswordError("");
        try {
            await changePassword(passwordForm);
            setIsChangingPassword(false);
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            if (Array.isArray(detail)) {
                setPasswordError(detail[0]?.msg || "Не удалось сменить пароль");
            } else {
                setPasswordError(detail || "Не удалось сменить пароль");
            }
        } finally {
            setPasswordSaving(false);
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
            <div style={styles.pageContainer}>
                <SidebarWithToggle/>
                <div style={styles.loadingContainer}>
                    <div style={styles.loadingSpinner}/>
                </div>
            </div>
        );
    }

    return (
        <div style={styles.pageContainer}>
            <SidebarWithToggle/>

            <header style={styles.header}>
                <div style={styles.headerContent}>
                    <h1 style={styles.headerTitle}>Профиль</h1>
                </div>
            </header>

            <main style={styles.main}>
                <div style={styles.card}>
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
                                <span style={styles.label}>Email</span>
                                <span style={styles.value}>{profile.email}</span>
                            </div>

                            <div style={styles.infoRow}>
                                <span style={styles.label}>Имя</span>
                                {isEditing ? (
                                    <input
                                        style={styles.input}
                                        value={formData.first_name}
                                        onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                                    />
                                ) : (
                                    <span style={styles.value}>{profile.first_name}</span>
                                )}
                            </div>

                            <div style={styles.infoRow}>
                                <span style={styles.label}>Фамилия</span>
                                {isEditing ? (
                                    <input
                                        style={styles.input}
                                        value={formData.last_name}
                                        onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                                    />
                                ) : (
                                    <span style={styles.value}>{profile.last_name}</span>
                                )}
                            </div>

                            <div style={styles.infoRow}>
                                <span style={styles.label}>Роль</span>
                                <span style={styles.value}>{getRoleText(profile.role)}</span>
                            </div>

                            <div style={styles.infoRow}>
                                <span style={styles.label}>Статус</span>
                                {profile.is_active
                                    ? <span style={{...styles.badge, ...styles.badgeActive}}>Активен</span>
                                    : <span style={{...styles.badge, ...styles.badgeInactive}}>Неактивен</span>
                                }
                            </div>

                            <div style={{...styles.infoRow, borderBottom: 'none'}}>
                                <span style={styles.label}>Дата регистрации</span>
                                <span style={styles.value}>{formatDate(profile.created_at)}</span>
                            </div>
                        </div>
                    )}

                    {error && <p style={styles.error}>{error}</p>}

                    <div style={styles.securitySection}>
                        <span style={styles.sectionTitle}><LockIcon/> Безопасность</span>

                        {isChangingPassword ? (
                            <div style={styles.passwordForm}>
                                <input
                                    style={styles.inputFull}
                                    type="password"
                                    placeholder="Текущий пароль"
                                    value={passwordForm.old_password}
                                    onChange={(e) => setPasswordForm({...passwordForm, old_password: e.target.value})}
                                />
                                <input
                                    style={styles.inputFull}
                                    type="password"
                                    placeholder="Новый пароль"
                                    value={passwordForm.new_password}
                                    onChange={(e) => setPasswordForm({...passwordForm, new_password: e.target.value})}
                                />
                                <input
                                    style={styles.inputFull}
                                    type="password"
                                    placeholder="Подтвердите новый пароль"
                                    value={passwordForm.confirm_password}
                                    onChange={(e) => setPasswordForm({...passwordForm, confirm_password: e.target.value})}
                                />
                                {passwordError && <p style={styles.error}>{passwordError}</p>}
                                <div style={styles.passwordButtons}>
                                    <button style={styles.buttonPrimary} onClick={handlePasswordSave} disabled={passwordSaving}>
                                        {passwordSaving ? "Сохранение..." : "Сохранить"}
                                    </button>
                                    <button style={styles.buttonSecondary} onClick={handlePasswordCancel}>
                                        Отмена
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <button style={styles.buttonSecondary} onClick={handlePasswordOpen}>
                                Сменить пароль
                            </button>
                        )}
                    </div>

                    <div style={styles.buttonGroup}>
                        {isEditing ? (
                            <>
                                <button style={styles.buttonPrimary} onClick={handleSave} disabled={saving}>
                                    {saving ? "Сохранение..." : "Сохранить"}
                                </button>
                                <button style={styles.buttonSecondary} onClick={handleCancel}>
                                    Отмена
                                </button>
                            </>
                        ) : (
                            <>
                                <button style={styles.buttonPrimary} onClick={handleEditClick}>
                                    Редактировать профиль
                                </button>
                                <button style={styles.buttonSecondary} onClick={() => navigate("/tables")}>
                                    К таблицам
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
};

export default ProfilePage;

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
        maxWidth: 640,
        margin: '0 auto',
        padding: `${spacing.xl}px ${spacing.lg}px`,
    },
    loadingContainer: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '50vh',
    },
    loadingSpinner: {
        width: 40,
        height: 40,
        border: `4px solid ${colors.hairline}`,
        borderTop: `4px solid ${colors.primary}`,
        borderRadius: rounded.full,
        animation: 'spin 1s linear infinite',
    },
    card: {
        background: colors.canvas,
        borderRadius: rounded.lg,
        padding: spacing.xl,
        boxShadow: shadowLevel4,
    },
    error: {
        ...typography.bodySm,
        color: colors.errorDeep,
        marginTop: spacing.md,
        padding: spacing.sm,
        background: colors.errorSoft,
        borderRadius: rounded.sm,
    },
    profileInfo: {
        display: "flex",
        flexDirection: "column",
    },
    infoRow: {
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: `${spacing.sm}px 0`,
        borderBottom: `1px solid ${colors.hairline}`,
    },
    label: {
        ...typography.bodySmStrong,
        color: colors.body,
    },
    value: {
        ...typography.bodyMd,
        color: colors.ink,
    },
    badge: {
        ...typography.caption,
        padding: `2px ${spacing.xs}px`,
        borderRadius: rounded.full,
        fontWeight: 500,
    },
    badgeActive: {
        color: colors.success,
        background: colors.linkBgSoft,
    },
    badgeInactive: {
        color: colors.errorDeep,
        background: colors.errorSoft,
    },
    buttonGroup: {
        marginTop: spacing.xl,
        display: "flex",
        gap: spacing.sm,
        justifyContent: "flex-end",
    },
    buttonPrimary: {
        ...typography.buttonLg,
        height: 44,
        padding: `0 ${spacing.lg}px`,
        borderRadius: rounded.pill,
        border: "none",
        background: colors.primary,
        color: colors.onPrimary,
        cursor: "pointer",
    },
    buttonSecondary: {
        ...typography.buttonLg,
        height: 44,
        padding: `0 ${spacing.lg}px`,
        borderRadius: rounded.pill,
        border: `1px solid ${colors.hairline}`,
        background: colors.canvas,
        color: colors.ink,
        cursor: "pointer",
    },
    avatarSection: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: spacing.sm,
        marginBottom: spacing.lg,
    },
    avatar: {
        width: 96,
        height: 96,
        borderRadius: rounded.full,
        objectFit: "cover",
        boxShadow: `0 0 0 1px ${colors.hairline}`,
        background: colors.canvasSoft,
    },
    avatarUploadBtn: {
        ...typography.bodySmStrong,
        color: colors.link,
        cursor: "pointer",
    },
    input: {
        ...typography.bodySm,
        height: 40,
        padding: `0 ${spacing.sm}px`,
        borderRadius: rounded.sm,
        border: `1px solid ${colors.hairline}`,
        background: colors.canvas,
        color: colors.ink,
        outline: "none",
        width: 220,
    },
    inputFull: {
        ...typography.bodySm,
        height: 40,
        padding: `0 ${spacing.sm}px`,
        borderRadius: rounded.sm,
        border: `1px solid ${colors.hairline}`,
        background: colors.canvas,
        color: colors.ink,
        outline: "none",
        width: "100%",
        boxSizing: "border-box",
    },
    securitySection: {
        marginTop: spacing.lg,
        paddingTop: spacing.lg,
        borderTop: `1px solid ${colors.hairline}`,
        display: "flex",
        flexDirection: "column",
        gap: spacing.md,
    },
    sectionTitle: {
        ...typography.bodySmStrong,
        display: "flex",
        alignItems: "center",
        gap: spacing.xs,
        color: colors.ink,
    },
    passwordForm: {
        display: "flex",
        flexDirection: "column",
        gap: spacing.sm,
    },
    passwordButtons: {
        display: "flex",
        gap: spacing.sm,
        marginTop: spacing.xxs,
        justifyContent: "flex-end",
    },
};