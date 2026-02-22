import React, {useState} from "react";
import {useNavigate} from "react-router-dom";
import {registerUser} from "../api/auth"

const RegisterPage: React.FC = () => {
    const navigate = useNavigate();
    const [email, setEmail] = useState("");
    const [firstName, setFirstName] = useState("");
    const [lastName, setLastName] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [error, setError] = useState("");

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");

        if (password !== confirmPassword) {
            setError("Пароли не совпадают");
            return;
        }

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
        }
    };

    return (
        <div style={styles.container}>
            <div style={styles.card}>
                <h2 style={styles.title}>Регистрация</h2>
                {error && <p style={styles.error}>{error}</p>}
                <form onSubmit={handleRegister} style={styles.form}>
                    <input
                        style={styles.input}
                        type="email"
                        placeholder="Email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                    <input
                        style={styles.input}
                        type="text"
                        placeholder="Имя"
                        value={firstName}
                        onChange={(e) => setFirstName(e.target.value)}
                        required
                        minLength={3}
                        maxLength={50}
                    />
                    <input
                        style={styles.input}
                        type="text"
                        placeholder="Фамилия"
                        value={lastName}
                        onChange={(e) => setLastName(e.target.value)}
                        required
                        minLength={3}
                        maxLength={50}
                    />
                    <input
                        style={styles.input}
                        type="password"
                        placeholder="Пароль"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        minLength={5}
                        maxLength={50}
                    />
                    <input
                        style={styles.input}
                        type="password"
                        placeholder="Подтвердите пароль"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        required
                        minLength={5}
                        maxLength={50}
                    />
                    <button style={styles.button} type="submit">
                        Зарегистрироваться
                    </button>
                </form>
                <p style={styles.footerText}>
                    Уже есть аккаунт?{" "}
                    <span
                        style={styles.link}
                        onClick={() => navigate("/login/")}
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
        background: "#f0f2f5",
    },
    card: {
        width: 400,
        padding: 32,
        borderRadius: 12,
        background: "#fff",
        boxShadow: "0 4px 16px rgba(0,0,0,0.1)",
        textAlign: "center",
    },
    title: {
        marginBottom: 24,
        color: "#333",
    },
    error: {
        color: "red",
        marginBottom: 16,
    },
    form: {
        display: "flex",
        flexDirection: "column",
        gap: 16,
    },
    input: {
        padding: 12,
        borderRadius: 6,
        border: "1px solid #ccc",
        fontSize: 16,
    },
    button: {
        padding: 12,
        borderRadius: 6,
        border: "none",
        background: "#4CAF50",
        color: "#fff",
        fontSize: 16,
        cursor: "pointer",
    },
    footerText: {
        marginTop: 16,
        fontSize: 14,
        color: "#555",
    },
    link: {
        color: "#4CAF50",
        cursor: "pointer",
        textDecoration: "underline",
    },
};
