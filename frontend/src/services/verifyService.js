import api from './api';

export const verifyService = {
  /** POST /api/verify (multipart) */
  async verify(file, { claim = false, claimedBy = '' } = {}) {
    const form = new FormData();
    form.append('file', file);
    if (claim) {
      form.append('claim', 'true');
      if (claimedBy) form.append('claimed_by', claimedBy);
    }
    const { data } = await api.post('/api/verify', form, { headers: { 'Content-Type': 'multipart/form-data' } });
    return data;
  },
};

export default verifyService;
