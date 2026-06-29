import axios from 'axios';

const api = axios.create({ baseURL: 'http://localhost:8000' });

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
  uploadFiles: async (formData: FormData) => {
        const response = await api.post('/discovery/upload', formData);
        return response.data; 
    },

    ingestGithub: async (formData: FormData) => {
        const response = await api.post('/discovery/github', formData);
        return response.data;
    },
 };