/**
 * DIAGNOSIS: Root cause of auth/API failures.
 * - VITE_API_BASE_URL pointed to http://localhost:8000 — bypasses Vite proxy, breaks in Docker.
 * - localStorage used for access_token — violates .cursorrules (NEVER localStorage for sensitive data).
 * - Cookies (httpOnly) are the auth mechanism; withCredentials must send them on every request.
 * - Relative baseURL ensures all requests go through Vite proxy to api:8000.
 * - In production (GitHub Pages), VITE_API_BASE_URL is set → use absolute URL to Render API.
 */
import axios, { AxiosError, AxiosInstance } from 'axios';
import type { ErrorResponse } from '@/types/api';

/** Base URL for API (used by api client and raw fetch for blob downloads). */
export const getApiBaseUrl = () =>
  import.meta.env.VITE_API_BASE_URL
    ? `${import.meta.env.VITE_API_BASE_URL}/api/v1`
    : '/api/v1';

const api: AxiosInstance = axios.create({
  baseURL: getApiBaseUrl(),
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  config.headers['X-Request-ID'] = crypto.randomUUID();
  return config;
});

let isRefreshing = false;
const failedQueue: Array<{ resolve: (v: unknown) => void; reject: (e: unknown) => void }> = [];

const processQueue = (error: unknown) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(undefined);
  });
  failedQueue.length = 0;
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ErrorResponse>) => {
    const originalRequest = error.config as typeof error.config & { _retry?: boolean };
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => api(originalRequest));
      }
      originalRequest._retry = true;
      isRefreshing = true;
      try {
        await api.post('/auth/refresh');
        processQueue(null);
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError);
        if (!window.location.pathname.includes('/login')) {
          const base = (import.meta.env.BASE_URL || '/').replace(/\/$/, '') || '';
          window.location.href = `${base}/login`;
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

export const apiGet = <T>(path: string) =>
  api.get<T>(path).then((r) => r.data);

export const apiPost = <T>(path: string, body?: unknown) =>
  api.post<T>(path, body).then((r) => r.data);

export const apiPatch = <T>(path: string, body?: unknown) =>
  api.patch<T>(path, body).then((r) => r.data);

export const apiClient = api;
export default api;
