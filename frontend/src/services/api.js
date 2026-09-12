// Axios API client — attaches the JWT and normalises errors.
import axios from 'axios';

export const API_BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
export const TOKEN_KEY = 'rec_guard_token';
export const USER_KEY = 'rec_guard_user';

export const api = axios.create({ baseURL: API_BASE, timeout: 90000 });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const data = err.response?.data;
    const message = data?.error || data?.message || err.message || 'Request failed';
    const error = new Error(message);
    error.status = err.response?.status;
    error.details = data?.details;
    error.data = data;
    return Promise.reject(error);
  },
);

/** Absolute URL for a backend-relative path such as /api/certificate/x.png */
export const fileUrl = (path) => (path?.startsWith('http') ? path : `${API_BASE}${path || ''}`);

export default api;
