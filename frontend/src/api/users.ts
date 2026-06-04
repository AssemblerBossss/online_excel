import api from "./axiosInstance";

export interface UserProfile {
    id: number;
    email: string;
    first_name: string;
    last_name: string;
    role: string;
    is_active: boolean;
    created_at: string;
    avatar_url: string | null;
}

// Схема данных для обновления профиля
export interface UserProfileUpdate {
    first_name?: string;
    last_name?: string;
}

export const getUserProfile = async (): Promise<UserProfile> => {
    const response = await api.get("/users/me/");
    return response.data;
};

export const uploadAvatar = async (userId: number, file: File): Promise<UserProfile> => {
    const formData = new FormData();
    formData.append("file", file);
    const { data } = await api.post(`/users/${userId}/avatar`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
    });
    return data;
};


// API-вызов на PATCH /users/{id}
export const updateUser = async (userId: number, data: UserProfileUpdate): Promise<UserProfile> => {
    const response = await api.patch(`/users/${userId}`, data);
    return response.data
};

