import axios, {AxiosError, InternalAxiosRequestConfig} from 'axios';

const API_BASE_URL = import.meta.env.VITE_APP_API_URL || 'http://localhost:3000/api';

export const api = axios.create({
    baseURL: API_BASE_URL,
    withCredentials: true,
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem('access_token');
    const tokenType = localStorage.getItem('token_type') || 'Bearer';

    console.log('🔵 Request Details:', {
        url: config.url,
        fullURL: `${API_BASE_URL}${config.url}`,
        method: config.method,
        token: token ? 'present' : 'missing',
        headers: config.headers
    });


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
            const refreshToken = localStorage.getItem('refresh_token');
            if (!refreshToken) {
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
                // Отправляем refresh token в теле запроса
                const refreshResponse = await api.post('/auth/refresh', {
                    refresh_token: refreshToken
                });

                if (refreshResponse.data.access_token) {
                    localStorage.setItem('access_token', refreshResponse.data.access_token);
                    if (refreshResponse.data.token_type) {
                        localStorage.setItem('token_type', refreshResponse.data.token_type);
                    }

                    // Обновляем заголовок для оригинального запроса
                    if (originalRequest.headers) {
                        originalRequest.headers.Authorization =
                            `${refreshResponse.data.token_type || 'Bearer'} ${refreshResponse.data.access_token}`;
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