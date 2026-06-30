import axios from 'axios';

const api = axios.create({ baseURL: 'http://localhost:8001' });

// Add JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const ProjectAPI = {
  create: (config: any) => api.post('/projects/create', config),
  updateConfig: (runId: string, updates: any) => api.patch(`/projects/${runId}/config`, updates),
  getProject: (runId: string) => api.get(`/projects/${runId}`),
  
  // This is the missing function you need to add!
  confirmLanguage: async (data: { run_id: string; filename: string; lang: string }) => {
    const response = await api.post('/discovery/confirm-language', data);
    return response.data;
  },

  uploadFiles: async (formData: FormData) => {
    const response = await api.post('/discovery/upload', formData);
    return response.data; 
  },

  uploadZip: async (formData: FormData) => {
    const response = await api.post('/discovery/upload-zip', formData);
    return response.data;
  },

  ingestGithub: async (runId: string, url: string) => {
    // Note: I changed this to match how you call it in SourceFiles.tsx 
    // where you pass (runId, githubUrl) instead of formData
    const response = await api.post('/discovery/github', { run_id: runId, url: url });
    return response.data;
  },

  listFiles: async (runId: string) => {
    const response = await api.get(`/projects/${runId}/files`);
    return response.data;
  },
  clearAllFiles: async (runId: string) => {
    const response = await api.delete(`/projects/${runId}/files`);
    return response.data;
  },

  deleteAllRuns: async () => {
    const response = await api.delete('/projects/runs');
    return response.data;
  },
};
