import api from './api';

export const authService = {
  async login(email, password) {
    const { data } = await api.post('/api/auth/login', { email, password });
    return data;
  },
  async register({ email, password, role, organisation }) {
    const { data } = await api.post('/api/auth/register', { email, password, role, organisation });
    return data;
  },
  async me() {
    const { data } = await api.get('/api/auth/me');
    return data;
  },
};

export default authService;
