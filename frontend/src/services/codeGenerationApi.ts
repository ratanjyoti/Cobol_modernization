import { API_BASE_URL } from './api';

export type TargetLanguage = 'java' | 'python' | 'csharp';

export type ConversionPlan = {
  run_id: string;
  file_id: number;
  source_file: string;
  source_language: string;
  target_language: string;
  target_framework: string;
  target_package_or_namespace?: string;
  summary?: string;
  classes?: Array<{
    class_name: string;
    file_path: string;
    layer: string;
    responsibility: string;
    source_mapping?: string[];
  }>;
  methods?: Array<{
    method_name: string;
    owning_class: string;
    responsibility: string;
    source_mapping?: string[];
    inputs?: string[];
    outputs?: string[];
  }>;
  unresolved_items?: string[];
  assumptions?: string[];
};

export type FixResponse = {
  run_id: string;
  target_language: TargetLanguage;
  status: string;
  message?: string;
  fixed_files: Array<{
    path: string;
    backup_path: string;
    fix_summary: string;
    warnings?: string[];
  }>;
  errors?: Array<{
    path: string;
    error: string;
  }>;
  error_text?: string;
};
export async function fixGeneratedCode(
  runId: string,
  targetLanguage: TargetLanguage,
  maxFiles = 3,
): Promise<FixResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/fix?target_language=${encodeURIComponent(targetLanguage)}&max_files=${maxFiles}`,
    {
      method: 'POST',
    },
  );

  return parseResponse<FixResponse>(response);
}

export type GeneratedFileSummary = {
  path: string;
  size: number;
};

export type GeneratedFileContent = {
  run_id: string;
  target_language: TargetLanguage;
  path: string;
  content: string;
};

export type CodeGenerationWorkflowMetadata = {
  conversion_agent?: string;
  conversion_agent_key?: string;
  fallback_used?: boolean;
  fallback_reason?: string;
  business_rules_used?: boolean;
  procedural_flow_used?: boolean;
  quality_gate_status?: string;
  validation_status?: string;
};

export type PlanResponse = {
  run_id: string;
  target_language: TargetLanguage;
  count: number;
  plans: ConversionPlan[];
  errors?: Array<{
    file_id: number;
    filename: string;
    error: string;
  }>;
  warnings?: string[];
};

export type GenerateResponse = {
  run_id: string;
  target_language: TargetLanguage;
  count: number;
  project_dir: string;
  manifest?: unknown;
  quality_gate?: {
    success: boolean;
    status: string;
    download_allowed?: boolean;
    failures?: string[];
    warnings?: string[];
    metrics?: Record<string, unknown>;
  };
  warnings?: string[];
  generated_files: Array<{
    path: string;
    language: TargetLanguage;
    file_type: string;
    content?: string;
    source_file?: string;
    notes?: string[];
  }>;
  errors?: Array<{
    file_id: number;
    filename: string;
    error: string;
  }>;
} & CodeGenerationWorkflowMetadata;

export type FileListResponse = {
  run_id: string;
  target_language: TargetLanguage;
  project_dir: string;
  count: number;
  files: GeneratedFileSummary[];
};

export type RegistryResponse = {
  run_id: string;
  target_language: TargetLanguage;
  locked: boolean;
  type_mapping_count: number;
  signature_count: number;
  type_mappings: Array<{
    source_name: string;
    target_name: string;
    source_type: string;
    target_type: string;
    evidence?: string;
  }>;
  signatures: Array<{
    source_paragraph: string;
    target_method: string;
    target_class?: string;
    return_type?: string;
    parameters?: string;
    evidence?: string;
  }>;
};

export type MigrationReportResponse = {
  run_id: string;
  target_language: TargetLanguage;
  json_report?: string;
  markdown_report?: string;
  path?: string;
  content?: string;
  report?: unknown;
};

export interface PipelineStep {
  step: string;
  count?: number;
  processed_source_file_count?: number;
  regenerated?: number;
  requested?: number;
  repaired?: number;
  before_count?: number;
  after_count?: number;
  errors?: unknown[];
  [key: string]: unknown;
}

export interface PipelineStatusResponse {
  run_id: string;
  target_language: TargetLanguage;
  target_display_name?: string;
  status:
    | 'NOT_STARTED'
    | 'RUNNING'
    | 'COMPLETED'
    | 'QUALITY_GATE_FAILED'
    | 'VALIDATION_FAILED'
    | 'FAILED'
    | 'STATUS_READ_FAILED'
    | string;
  stage: string;
  progress: number;
  download_allowed: boolean;
  updated_at?: string;
  current_agent?: string;
  conversion_agent?: string;
  conversion_agent_key?: string;
  total_files?: number;
  planned_files?: number;
  generated_files?: number;
  steps?: PipelineStep[];
  errors?: unknown[];
  quality_gate?: unknown;
  validation?: unknown;
  report?: unknown;
  cached?: boolean;
  already_running?: boolean;
}
export async function runFullCodeGeneration(
  runId: string,
  targetLanguage: TargetLanguage,
  force = false,
): Promise<PipelineStatusResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(
      runId,
    )}/run-full?target_language=${encodeURIComponent(targetLanguage)}&force=${force ? 'true' : 'false'}`,
    {
      method: 'POST',
    },
  );

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Failed to run full code generation pipeline');
  }

  return response.json();
}

export async function getCodeGenerationPipelineStatus(
  runId: string,
  targetLanguage: TargetLanguage,
): Promise<PipelineStatusResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(
      runId,
    )}/pipeline-status?target_language=${encodeURIComponent(targetLanguage)}`,
  );

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Failed to get code generation pipeline status');
  }

  return response.json();
}
export type ValidationResponse = {
  success: boolean;
  status?: string;
  download_allowed?: boolean;
  target_language: TargetLanguage;
  project_dir: string;
  command: string;
  stdout: string;
  stderr: string;
  returncode: number;
  quality_gate?: {
    success: boolean;
    status: string;
    download_allowed?: boolean;
    failures?: string[];
    warnings?: string[];
    metrics?: Record<string, unknown>;
  };
  checked_files?: string[];
  failed_files?: string[];
} & CodeGenerationWorkflowMetadata;

export async function generateMigrationReport(
  runId: string,
  targetLanguage: TargetLanguage,
): Promise<MigrationReportResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/report?target_language=${encodeURIComponent(targetLanguage)}`,
    {
      method: 'POST',
    },
  );

  return parseResponse<MigrationReportResponse>(response);
}

export async function readMigrationReport(
  runId: string,
  targetLanguage: TargetLanguage,
): Promise<MigrationReportResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/report?target_language=${encodeURIComponent(targetLanguage)}`,
  );

  return parseResponse<MigrationReportResponse>(response);
}

export async function finalizeSymbolRegistry(
  runId: string,
  targetLanguage: TargetLanguage,
): Promise<RegistryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/registry/finalize?target_language=${encodeURIComponent(targetLanguage)}`,
    {
      method: 'POST',
    },
  );

  return parseResponse<RegistryResponse>(response);
}

export async function getSymbolRegistry(
  runId: string,
  targetLanguage: TargetLanguage,
): Promise<RegistryResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/registry?target_language=${encodeURIComponent(targetLanguage)}`,
  );

  return parseResponse<RegistryResponse>(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed with HTTP ${response.status}`;

    try {
      const payload = await response.json();
      message = payload.detail || payload.message || JSON.stringify(payload);
    } catch {
      const text = await response.text();
      message = text || message;
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function createConversionPlan(
  runId: string,
  targetLanguage: TargetLanguage,
): Promise<PlanResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/plan?target_language=${encodeURIComponent(targetLanguage)}`,
    { method: 'POST' },
  );

  return parseResponse<PlanResponse>(response);
}

export async function listConversionPlans(
  runId: string,
  targetLanguage: TargetLanguage,
): Promise<PlanResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/plans?target_language=${encodeURIComponent(targetLanguage)}`,
  );

  return parseResponse<PlanResponse>(response);
}

export async function generateCode(
  runId: string,
  targetLanguage: TargetLanguage,
): Promise<GenerateResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/generate?target_language=${encodeURIComponent(targetLanguage)}`,
    { method: 'POST' },
  );

  return parseResponse<GenerateResponse>(response);
}

export async function validateGeneratedProject(
  runId: string,
  targetLanguage: TargetLanguage,
): Promise<ValidationResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/validate?target_language=${encodeURIComponent(targetLanguage)}`,
    { method: 'POST' },
  );

  return parseResponse<ValidationResponse>(response);
}

export async function listGeneratedFiles(
  runId: string,
  targetLanguage: TargetLanguage,
): Promise<FileListResponse> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/files?target_language=${encodeURIComponent(targetLanguage)}`,
  );

  return parseResponse<FileListResponse>(response);
}

export async function readGeneratedFile(
  runId: string,
  targetLanguage: TargetLanguage,
  path: string,
): Promise<GeneratedFileContent> {
  const response = await fetch(
    `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/file?target_language=${encodeURIComponent(targetLanguage)}&path=${encodeURIComponent(path)}`,
  );

  return parseResponse<GeneratedFileContent>(response);
}

export function generatedProjectDownloadUrl(
  runId: string,
  targetLanguage: TargetLanguage,
  requireValid = true,
): string {
  return `${API_BASE_URL}/code-generation/${encodeURIComponent(runId)}/download?target_language=${encodeURIComponent(targetLanguage)}&require_valid=${requireValid ? 'true' : 'false'}`;
}
