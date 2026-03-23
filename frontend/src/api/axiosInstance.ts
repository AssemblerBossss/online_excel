import axios, {AxiosError, InternalAxiosRequestConfig} from 'axios';
import { refreshToken } from './auth';

const API_BASE_URL = import.meta.env.VITE_APP_API_URL || 'http://localhost:3000/api';

export const api = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    const tokenType = localStorage.getItem('token_type') || 'Bearer';

    if (token && config.headers) {
        config.headers.Authorization = `${tokenType} ${token}`;
    }

    return config;
});

// Флаг для предотвращения множественных одновременных refresh запросов
let isRefreshing = false;
let failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (error?: any) => void;
}> = [];

const processQueue = (error: any = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve();
        }
    });
    failedQueue = [];
};

// Response interceptor
api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        if (
            error.response?.status === 401 &&
            originalRequest &&
            !originalRequest._retry &&
            !originalRequest.url?.includes('/auth/login') &&
            !originalRequest.url?.includes('/auth/register') &&
            !originalRequest.url?.includes('/auth/logout')
        ) {
            // Проверяем наличие refresh token
            const storedRefreshToken = localStorage.getItem('refresh_token');
            if (!storedRefreshToken) {
                window.location.href = '/login';
                return Promise.reject(error);
            }

            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({resolve, reject});
                })
                    .then(() => {
                        return api(originalRequest);
                    })
                    .catch((err) => {
                        return Promise.reject(err);
                    });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                const refreshResponse = await refreshToken(storedRefreshToken);

                if (refreshResponse.access_token) {
                    localStorage.setItem('access_token', refreshResponse.access_token);
                    localStorage.setItem('token_type', refreshResponse.token_type || 'Bearer');
                    if (refreshResponse.refresh_token) {
                        localStorage.setItem('refresh_token', refreshResponse.refresh_token);
                    }
                    if (originalRequest.headers) {
                        originalRequest.headers.Authorization =
                            `${refreshResponse.token_type || 'Bearer'} ${refreshResponse.access_token}`;
                    }
                }

                processQueue(null);
                return api(originalRequest);
            } catch (refreshError) {
                processQueue(refreshError);
                localStorage.removeItem('access_token');
                localStorage.removeItem('refresh_token');
                localStorage.removeItem('token_type');
                window.location.href = '/login';
                return Promise.reject(refreshError);
            } finally {
                isRefreshing = false;
            }
        }

        return Promise.reject(error);
    }
);

export default api;