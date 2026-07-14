import React, {useState} from "react";
import {useNavigate} from "react-router-dom";
import api from "../api/axiosInstance";
import {loginUser} from "../api/auth";
import {colors, rounded, shadowLevel2, spacing, typography} from "../styles/theme";


const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);


    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setIsLoading(true);

        try {
            const data = await loginUser({email, password});

            // Сохраняем токены из ответа
            if (data.access_token) {
                // Сохраняем в localStorage
                localStorage.setItem('access_token', data.access_token);
                localStorage.setItem('refresh_token', data.refresh_token);
                localStorage.setItem('token_type', data.token_type || 'Bearer');

                // Устанавливаем заголовок авторизации для axios
                api.defaults.headers.common['Authorization'] =
                    `${data.token_type || 'Bearer'} ${data.access_token}`;

                // Перенаправляем на страницу таблиц
                navigate("/tables");
            } else {
                setError("Не удалось получить токен доступа");
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || "Ошибка входа");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h2 style={styles.title}>Вход в аккаунт</h2>
                {error && <p style={styles.error}>{error}</p>}
                <form onSubmit={handleLogin} style={styles.form}>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Email</label>
                        <input
                            style={styles.input}
                            type="email"
                            placeholder="Введите ваш email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Пароль</label>
                        <input
                            style={styles.input}
                            type="password"
                            placeholder="Введите пароль"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </div>
                    <button style={styles.button} type="submit" disabled={isLoading}>
                        {isLoading ? "Вход..." : "Войти"}
                    </button>
                </form>
                <p style={styles.footerText}>
                    Нет аккаунта?{" "}
                    <span
                        style={styles.link}
                        onClick={() => navigate("/register")}
                    >
            Зарегистрироваться
          </span>
                </p>
            </div>
        </div>
    );
};

export default LoginPage;

const styles: Record<string, React.CSSProperties> = {
    container: {
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: colors.canvas,
    },
    card: {
        width: 400,
        padding: spacing.xl,
        borderRadius: rounded.lg,
        background: colors.canvasSoft,
        boxShadow: shadowLevel2,
        textAlign: "center",
    },
    title: {
        ...typography.displaySm,
        marginBottom: spacing.lg,
        color: colors.ink,
    },
    error: {
        ...typography.bodySm,
        color: colors.errorDeep,
        marginBottom: spacing.md,
        padding: spacing.sm,
        background: colors.errorSoft,
        borderRadius: rounded.sm,
    },
    form: {
        display: "flex",
        flexDirection: "column",
        gap: spacing.md,
    },
    inputGroup: {
        display: "flex",
        flexDirection: "column",
        gap: spacing.xxs,
        textAlign: "left",
    },
    label: {
        ...typography.bodySmStrong,
        color: colors.body,
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
    },
    button: {
        ...typography.buttonLg,
        height: 48,
        borderRadius: rounded.pill,
        border: "none",
        background: colors.primary,
        color: colors.onPrimary,
        cursor: "pointer",
        marginTop: spacing.xs,
    },
    footerText: {
        ...typography.bodySm,
        marginTop: spacing.lg,
        color: colors.body,
    },
    link: {
        color: colors.link,
        cursor: "pointer",
        textDecoration: "underline",
        fontWeight: 500,
    },
};
