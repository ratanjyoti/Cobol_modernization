import axios from 'axios';

export interface ProjectConfig {
  project_name: string;
  provider: string;
  model: string;
  lang: string;
  speed_profile: 'Turbo' | 'Fast' | 'Balanced' | 'Thorough';
  reasoning_effort?: 'Low' | 'Medium' | 'High';
  workers: number;
}

export interface FileRecord {
  id: string;
  filename: string;
  filepath: string;
  detected_lang: string;
  status: 'PENDING_CONFIRMATION' | 'CONFIRMED' | 'REJECTED';
  size?: number;
}

export interface ProjectSummary {
  run_id: string;
  name: string;
  status: string;
  created_at?: string | null;
  files_count: number;
  target?: string | null;
  llm_provider?: string | null;
  llm_model?: string | null;
  interaction_lang?: string | null;
  speed_profile?: string | null;
  reasoning_effort?: string | null;
  parallel_workers?: number | null;
  file_status_counts?: Record<string, number>;
  language_counts?: Record<string, number>;
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://cobol-modernization.onrender.com';
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws');

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

export const ProjectAPI = {
  create: async (config: ProjectConfig): Promise<{ run_id: string; name: string; status: string }> => {
    const response = await api.post('/projects', config);
    return response.data;
  },

  updateConfig: async (runId: string, config: Partial<ProjectConfig>) => {
    const response = await api.patch(`/projects/${runId}/config`, config);
    return response.data;
  },

  list: async (): Promise<ProjectSummary[]> => {
    const response = await api.get('/projects');
    return response.data;
  },

  get: async (runId: string): Promise<ProjectSummary> => {
    const response = await api.get(`/projects/${runId}`);
    return response.data;
  },

  delete: async (runId: string) => {
    const response = await api.delete(`/projects/${runId}`);
    return response.data;
  },

  listFiles: async (runId: string): Promise<{ files: FileRecord[] }> => {
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

  uploadZip: async (formData: FormData) => {
    const response = await api.post('/discovery/upload-zip', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  uploadFiles: async (formData: FormData) => {
    const response = await api.post('/discovery/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  ingestGithub: async (runId: string, url: string) => {
    const response = await api.post('/discovery/github', { run_id: runId, url });
    return response.data;
  },

  confirmLanguage: async (data: { run_id: string; filename: string; lang: string }) => {
    const response = await api.post('/discovery/confirm-language', data);
    return response.data;
  },

  launchPipeline: async (formData: FormData) => {
    const response = await api.post('/discovery/launch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

