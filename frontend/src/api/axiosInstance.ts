import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

// В проде идём через /api (Nginx проксирует на бэк); можно переопределить переменной окружения
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // для работы с cookies
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

api.interceptors.request.use((config) => config);

// Response interceptor для автоматического обновления токена
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Если ошибка 401 и это не запрос на refresh/login/logout
    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/auth/login') &&
      !originalRequest.url?.includes('/auth/register') &&
      !originalRequest.url?.includes('/auth/logout')
    ) {
      if (isRefreshing) {
        // Если уже идет refresh, добавляем запрос в очередь
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
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
        // Пытаемся обновить токен
        await api.post('/auth/refresh');
        processQueue(null);
        // Повторяем оригинальный запрос
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError);
        // Если refresh не удался, редиректим на логин
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

export default api;