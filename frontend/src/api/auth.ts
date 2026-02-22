import api from "./axiosInstance";

export const registerUser = async (data: {
    email: string;
    password: string;
    confirm_password: string;
    last_name: string;
    first_name: string;
}) => {
    const res = await api.post("/auth/register", data);
    return res.data;
};

export const loginUser = async (data: { email: string; password: string }) => {
    const res = await api.post("/auth/login", data);
    return res.data;
};

export const logoutUser = async () => {
    const res = await api.post("/auth/logout");
    return res.data;
};

export const refreshToken = async () => {
    const res = await api.post("/auth/refresh");
    return res.data;
};
