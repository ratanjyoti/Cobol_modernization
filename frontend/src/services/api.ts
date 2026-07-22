import axios from 'axios';

export interface ProjectConfig {
  project_name?: string;
  mode?: string;
  provider?: string;
  key?: string;
  url?: string;
  model?: string;
  lang?: string;
  speed_profile?: 'Turbo' | 'Fast' | 'Balanced' | 'Thorough';
  reasoning_effort?: 'Low' | 'Medium' | 'High';
  workers?: number;
}

export interface FileRecord {
  id: string;
  filename: string;
  filepath: string;
  detected_lang: string;
  status: 'PENDING_CONFIRMATION' | 'CONFIRMED' | 'REJECTED';
  size?: number;
}

export interface DependencyRelation {
  id: string;
  source_file: string;
  target_item: string;
  relation_type: string;
}

export interface ServiceStatus {
  active: boolean;
  provider?: string;
  model?: string;
  detail?: string;
}

export interface ServiceHealth {
  ai_api: ServiceStatus;
  neo4j: ServiceStatus;
}
export interface ProjectSummary {
  run_id: string;
  name: string;
  status: string;
  created_at?: string | null;
  files_count: number;
  target?: string | null;
  llm_provider?: string | null;
  ai_mode?: string | null;
  custom_api_base_url?: string | null;
  has_custom_api_key?: boolean;
  llm_model?: string | null;
  interaction_lang?: string | null;
  speed_profile?: string | null;
  reasoning_effort?: string | null;
  parallel_workers?: number | null;
  file_status_counts?: Record<string, number>;
  language_counts?: Record<string, number>;
}

const getDefaultApiBaseUrl = () => {
  if (typeof window === 'undefined') {
    return 'http://localhost:8000';
  }

  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return import.meta.env.VITE_API_BASE_URL || 'http://localhost:8010';
  }

  return import.meta.env.VITE_API_BASE_URL || 'https://cobol-modernization.onrender.com';
};

export const API_BASE_URL = getDefaultApiBaseUrl();
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

  getConfig: async (runId: string): Promise<ProjectConfig> => {
    const response = await api.get(`/projects/${runId}/config`);
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

  getServiceHealth: async (runId: string): Promise<ServiceHealth> => {
    const response = await api.get(`/projects/${runId}/service-health`);
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

  getComplexity: async (runId: string) => {
    const response = await api.get(`/discovery/complexity/${runId}`);
    return response.data;
  },
  getGraph: async (runId: string) => {
    const response = await api.get(`/discovery/graph/${runId}`);
    return response.data;
  },
  getDDD: async (runId: string) => {
    const response = await api.get(`/discovery/ddd/${runId}`);
    return response.data;
  },

  listFiles: async (runId: string): Promise<{ files: FileRecord[] }> => {
    const response = await api.get(`/projects/${runId}/files`);
    return response.data;
  },

  listRelations: async (runId: string): Promise<{ relations: DependencyRelation[] }> => {
    const response = await api.get(`/projects/${runId}/relations`);
    return response.data;
  },

  getDiscoveryData: async (runId: string): Promise<{ files: FileRecord[]; relations: DependencyRelation[] }> => {
    const response = await api.get(`/projects/${runId}/discovery-data`);
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

  uploadFolder: async (formData: FormData) => {
    const response = await api.post('/discovery/upload-folder', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  ingestLocalRepo: async (formData: FormData) => {
    const response = await api.post('/discovery/local-repo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  ingestGithub: async (formData: FormData) => {
    const response = await api.post('/discovery/github', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  confirmLanguage: async (data: { run_id: string; filename: string; lang: string; file_id?: string; filepath?: string }) => {
    const response = await api.post('/discovery/confirm-language', data);
    return response.data;
  },

  launchPipeline: async (formData: FormData) => {
    const response = await api.post('/discovery/launch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  getBusinessRules: async (runId: string) => {
    const response = await api.get(`/business-rules/${runId}`);
    return response.data;
  },

  extractBusinessRules: async (runId: string) => {
    const response = await api.post(`/business-rules/${runId}/extract`);
    return Array.isArray(response.data) ? response.data : (response.data.rules || []);
  },

  verifyRule: async (ruleId: number, data: { status: string; text?: string }) => {
    const response = await api.patch(`/business-rules/${ruleId}`, data);
    return response.data;
  },
};



