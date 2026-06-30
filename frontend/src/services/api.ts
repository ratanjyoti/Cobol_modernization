import axios from 'axios';

// --- Types & Interfaces ---
// Defining these prevents "any" errors and makes the code maintainable
export interface ProjectConfig {
  project_name: string;
  llm_provider: 'azure' | 'ollama';
  llm_model: string;
  interaction_lang: string;
  speed_profile: 'Turbo' | 'Fast' | 'Balanced' | 'Thorough';
  reasoning_effort: 'Low' | 'Medium' | 'High';
  parallel_workers: number;
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
}

// --- API Configuration ---
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';
export const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws'); 

const api = axios.create({ 
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Interceptor for JWT Token: Automatically attaches token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const ProjectAPI = {
  // ==========================================
  // 🟢 PHASE 1: ONBOARDING
  // ==========================================
  
  // Create a new project
  create: async (config: ProjectConfig) => {
    const response = await api.post('/projects', config);
    return response.data; 
  },

  // Update existing project config (Language, LLM, etc.)
  updateConfig: async (runId: string, config: Partial<ProjectConfig>) => {
    const response = await api.patch(`/projects/${runId}/config`, config);
    return response.data;
  },

  // List project history for the dashboard
  list: async (): Promise<ProjectSummary[]> => {
    const response = await api.get('/projects');
    return response.data; 
  },

  // ==========================================
  // 🔵 PHASE 2: INGESTION & DISCOVERY
  // ==========================================

  // List all files mapped to a specific project
  listFiles: async (runId: string): Promise<{ files: FileRecord[] }> => {
    const response = await api.get(`/projects/${runId}/files`);
    return response.data;
  },

  // Upload a ZIP archive (Unzips on backend)
  uploadZip: async (formData: FormData) => {
    const response = await api.post('/discovery/upload-zip', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data; 
  },

  // Upload multiple individual files
  uploadFiles: async (formData: FormData) => {
    const response = await api.post('/discovery/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  // Ingest from GitHub URL
  ingestGithub: async (runId: string, url: string) => {
    const response = await api.post('/discovery/github', { run_id: runId, url });
    return response.data;
  },

  // Confirm or correct the auto-detected language
  confirmLanguage: async (data: { run_id: string; filename: string; lang: string }) => {
    const response = await api.post('/discovery/confirm-language', data);
    return response.data;
  },

  // ==========================================
  // 🟠 PHASE 4: EXECUTION
  // ==========================================

  // Launch the actual AI Modernization Pipeline
  launchPipeline: async (formData: FormData) => {
    const response = await api.post('/discovery/launch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },
};

