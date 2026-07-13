import React, {useState} from "react";
import {useNavigate} from "react-router-dom";
import {registerUser} from "../api/auth"
import {colors, rounded, shadowLevel2, spacing, typography} from "../styles/theme";

const RegisterPage: React.FC = () => {
    const navigate = useNavigate();
    const [email, setEmail] = useState("");
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");
    const [isLoading, setIsLoading] = useState(false);

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (password !== confirmPassword) {
            setError("Пароли не совпадают");
            return;
        }

        setIsLoading(true);
        try {
            await registerUser({
                email,
                first_name: firstName,
                last_name: lastName,
                password,
                confirm_password: confirmPassword,
            });
            navigate("/login");
        } catch (err: any) {
            setError(err.response?.data?.detail || "Ошибка регистрации");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h2 style={styles.title}>Регистрация</h2>
                {error && <p style={styles.error}>{error}</p>}
                <form onSubmit={handleRegister} style={styles.form}>
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
                        <label style={styles.label}>Имя</label>
                        <input
                            style={styles.input}
                            type="text"
                            placeholder="Введите имя"
                            value={firstName}
                            onChange={(e) => setFirstName(e.target.value)}
                            required
                            minLength={3}
                            maxLength={50}
                        />
                    </div>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Фамилия</label>
                        <input
                            style={styles.input}
                            type="text"
                            placeholder="Введите фамилию"
                            value={lastName}
                            onChange={(e) => setLastName(e.target.value)}
                            required
                            minLength={3}
                            maxLength={50}
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
                            minLength={5}
                            maxLength={50}
                        />
                    </div>
                    <div style={styles.inputGroup}>
                        <label style={styles.label}>Подтвердите пароль</label>
                        <input
                            style={styles.input}
                            type="password"
                            placeholder="Повторите пароль"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                            minLength={5}
                            maxLength={50}
                        />
                    </div>
                    <button style={styles.button} type="submit" disabled={isLoading}>
                        {isLoading ? "Регистрация..." : "Зарегистрироваться"}
                    </button>
                </form>
                <p style={styles.footerText}>
                    Уже есть аккаунт?{" "}
                    <span
                        style={styles.link}
                        onClick={() => navigate("/login")}
                    >
            Войти
          </span>
                </p>
            </div>
        </div>
    );
};

export default RegisterPage;

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
