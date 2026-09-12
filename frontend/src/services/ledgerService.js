import api from './api';

export const ledgerService = {
  async list(params = {}) {
    const { data } = await api.get('/api/ledger', { params });
    return data;
  },
  async get(certId) {
    const { data } = await api.get(`/api/ledger/${encodeURIComponent(certId)}`);
    return data;
  },
  async history(certId) {
    const { data } = await api.get(`/api/ledger/${encodeURIComponent(certId)}/history`);
    return data;
  },
  async stats() {
    const { data } = await api.get('/api/ledger/stats');
    return data;
  },
  async claim(certId, claimedBy) {
    const { data } = await api.post(`/api/ledger/${encodeURIComponent(certId)}/claim`, claimedBy ? { claimed_by: claimedBy } : {});
    return data;
  },
  async revoke(certId) {
    const { data } = await api.post(`/api/ledger/${encodeURIComponent(certId)}/revoke`);
    return data;
  },
  async dashboard(days = 14) {
    const { data } = await api.get('/api/admin/dashboard', { params: { days } });
    return data;
  },
  async anomalies(resolved = false) {
    const { data } = await api.get('/api/admin/anomalies', { params: { resolved } });
    return data;
  },
  async resolveAnomaly(id) {
    const { data } = await api.post(`/api/admin/anomalies/${id}/resolve`);
    return data;
  },
  async issuers() {
    const { data } = await api.get('/api/issuers');
    return data;
  },
};

export default ledgerService;
