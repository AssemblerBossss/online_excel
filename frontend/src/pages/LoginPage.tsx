import React, {useState} from "react";
import {useNavigate} from "react-router-dom";
import api from "../api/axiosInstance";
import {loginUser} from "../api/auth";


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
                    <button style={styles.button} type="submit">
                        Войти
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
        background: "#f0f2f5",
        fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    },
    card: {
        width: 400,
        padding: 40,
        borderRadius: 12,
        background: "#fff",
        boxShadow: "0 8px 32px rgba(0,0,0,0.1)",
        textAlign: "center",
    },
    title: {
        marginBottom: 32,
        color: "#333",
        fontSize: 28,
        fontWeight: 600,
    },
    error: {
        color: "#ff4757",
        marginBottom: 16,
        padding: 12,
        background: "#ffe6e6",
        borderRadius: 6,
        fontSize: 14,
    },
    form: {
        display: "flex",
        flexDirection: "column",
        gap: 20,
    },
    inputGroup: {
        display: "flex",
        flexDirection: "column",
        gap: 8,
        textAlign: "left",
    },
    label: {
        fontSize: 14,
        fontWeight: 500,
        color: "#555",
    },
    input: {
        padding: 12,
        borderRadius: 6,
        border: "1px solid #ddd",
        fontSize: 16,
        transition: "border-color 0.2s",
    },
    button: {
        padding: 14,
        borderRadius: 6,
        border: "none",
        background: "#4CAF50",
        color: "#fff",
        fontSize: 16,
        fontWeight: 600,
        cursor: "pointer",
        transition: "background-color 0.2s",
        marginTop: 10,
    },
    footerText: {
        marginTop: 24,
        fontSize: 14,
        color: "#666",
    },
    link: {
        color: "#4CAF50",
        cursor: "pointer",
        textDecoration: "underline",
        fontWeight: 500,
    },
};