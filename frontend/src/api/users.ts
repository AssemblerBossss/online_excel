import api from "./axiosInstance";

export interface UserProfile {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
    role: string;
    is_active: boolean;
    created_at: string;
}

export const getUserProfile = async (): Promise<UserProfile> => {
    const response = await api.get("/users/me/");
    return response.data;
};