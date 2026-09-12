import api, { fileUrl } from './api';

export const issueService = {
  /** POST /api/issue */
  async issue(payload) {
    const { data } = await api.post('/api/issue', payload);
    return data;
  },
  downloadUrl: (fileName) => fileUrl(`/api/certificate/${fileName}`),
  previewUrl: (fileName) => fileUrl(`/api/certificate/${fileName}/preview`),
};

export default issueService;
