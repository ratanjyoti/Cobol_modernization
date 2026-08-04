import { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  ScrollText,
  Braces,
  CheckCircle2,
  Code2,
  Download,
  Eye,
  FileCode2,
  FileText,
  Loader2,
  LockKeyhole,
  RefreshCcw,
  Route,
  Sparkles,
  Terminal,
  Wand2,
  XCircle,
} from 'lucide-react';
import PageHeader from '../components/PageHeader';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';
import type {
  CodeGenerationWorkflowMetadata,
  ConversionPlan,
  FixResponse,
  GeneratedFileContent,
  GeneratedFileSummary,
  MigrationReportResponse,
  PipelineStatusResponse,
  RegistryResponse,
  TargetLanguage,
  ValidationResponse,
} from '../services/codeGenerationApi';
import {
  createConversionPlan,
  finalizeSymbolRegistry,
  fixGeneratedCode,
  generatedProjectDownloadUrl,
  generateCode,
  generateMigrationReport,
  getSymbolRegistry,
  listConversionPlans,
  listGeneratedFiles,
  readGeneratedFile,
  readMigrationReport,
  validateGeneratedProject,
  runFullCodeGeneration,
  getCodeGenerationPipelineStatus,
} from '../services/codeGenerationApi';

const TARGETS: Array<{
  id: TargetLanguage;
  label: string;
  framework: string;
  description: string;
}> = [
  {
    id: 'java',
    label: 'Java',
    framework: 'Quarkus',
    description: 'Generate layered Java Quarkus services, resources, repositories, DTOs, and tests.',
  },
  {
    id: 'python',
    label: 'Python',
    framework: 'FastAPI',
    description: 'Generate Python FastAPI routers, services, repositories, schemas, and tests.',
  },
  {
    id: 'csharp',
    label: 'C#',
    framework: 'ASP.NET Core',
    description: 'Generate ASP.NET Core controllers, services, repositories, DTOs, and tests.',
  },
];

const getCurrentRunId = () => {
  return (
    localStorage.getItem('active_run_id') ||
    localStorage.getItem('current_run_id') ||
    localStorage.getItem('run_id') ||
    localStorage.getItem('selectedRunId') ||
    localStorage.getItem('current_project_id') ||
    localStorage.getItem('projectId') ||
    ''
  );
};

const getLockedTargetLanguage = (runId: string): TargetLanguage => {
  const runSpecific = localStorage.getItem(`modernizer_target_language_${runId}`);
  const global = localStorage.getItem('modernizer_target_language');
  const value = (runSpecific || global || 'java').toLowerCase().trim();

  if (value === 'python' || value === 'py' || value === 'fastapi') {
    return 'python';
  }

  if (
    value === 'csharp' ||
    value === 'c#' ||
    value === 'cs' ||
    value === 'dotnet'
  ) {
    return 'csharp';
  }

  return 'java';
};

const targetLanguageLabel = (target: TargetLanguage): string => {
  if (target === 'python') return 'Python / FastAPI';
  if (target === 'csharp') return 'C# / ASP.NET Core';
  return 'Java / Quarkus';
};

const conversionAgentName = (target: TargetLanguage): string => {
  if (target === 'python') return 'PythonConversionAgent';
  if (target === 'csharp') return 'CSharpConversionAgent';
  return 'JavaConversionAgent';
};

const yesNo = (value?: boolean) => (value ? 'Yes' : 'No');

const statusFromPayload = (value: unknown): string => {
  if (!value) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'object' && 'status' in value) {
    const status = (value as { status?: unknown }).status;
    return typeof status === 'string' ? status : '';
  }
  return '';
};
const formatBytes = (bytes: number) => {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

const CodeGeneration = () => {
  const [runId, setRunId] = useState(getCurrentRunId());
  const [targetLanguage, setTargetLanguage] = useState<TargetLanguage>(
    getLockedTargetLanguage(getCurrentRunId())
  );
  const [plans, setPlans] = useState<ConversionPlan[]>([]);
  const [generatedFiles, setGeneratedFiles] = useState<GeneratedFileSummary[]>([]);
  const [selectedFile, setSelectedFile] = useState<GeneratedFileContent | null>(null);
  const [activePlan, setActivePlan] = useState<ConversionPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [validationResult, setValidationResult] = useState<ValidationResponse | null>(null);
  const [validating, setValidating] = useState(false);
  const [fixResult, setFixResult] = useState<FixResponse | null>(null);
  const [fixing, setFixing] = useState(false);
  const [reportResult, setReportResult] = useState<MigrationReportResponse | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [registry, setRegistry] = useState<RegistryResponse | null>(null);
  const [lockingRegistry, setLockingRegistry] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatusResponse | null>(null);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [workflowMetadata, setWorkflowMetadata] = useState<CodeGenerationWorkflowMetadata>({});
  const [showAdvanced, setShowAdvanced] = useState(false);

  const selectedTarget = useMemo(
    () => TARGETS.find((item) => item.id === targetLanguage) || TARGETS[0],
    [targetLanguage],
  );

  const hasRunId = Boolean(runId.trim());
  const isPipelineSuccessful =
    pipelineStatus?.status === 'COMPLETED' && pipelineStatus?.download_allowed === true;
  const isPipelineFailed =
    pipelineStatus?.status === 'QUALITY_GATE_FAILED' ||
    pipelineStatus?.status === 'VALIDATION_FAILED' ||
    pipelineStatus?.status === 'FAILED';
  const pipelineProgress = Math.max(
    0,
    Math.min(100, Number(pipelineStatus?.progress || 0)),
  );
  const targetDisplayName =
    pipelineStatus?.target_display_name || targetLanguageLabel(targetLanguage);

  const loadExistingData = async () => {
    if (!hasRunId) return;

    setLoadingFiles(true);
    setError('');
    setMessage('');

    try {
      const [planResponse, fileResponse] = await Promise.allSettled([
        listConversionPlans(runId, targetLanguage),
        listGeneratedFiles(runId, targetLanguage),
      ]);
      const registryResponse = await getSymbolRegistry(runId, targetLanguage).catch(() => null);

      if (planResponse.status === 'fulfilled') {
        setPlans(planResponse.value.plans || []);
        setActivePlan(planResponse.value.plans?.[0] || null);
      }

      if (fileResponse.status === 'fulfilled') {
        setGeneratedFiles(fileResponse.value.files || []);
      }

      if (registryResponse) {
        setRegistry(registryResponse);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load code generation data');
    } finally {
      setLoadingFiles(false);
    }
  };

  useEffect(() => {
    loadExistingData();
  }, [hasRunId, runId, targetLanguage]);

  useEffect(() => {
    if (!hasRunId || !targetLanguage) return;

    let cancelled = false;

    const loadStatus = async () => {
      try {
        const status = await getCodeGenerationPipelineStatus(runId, targetLanguage);

        if (!cancelled) {
          setPipelineStatus(status);
          setWorkflowMetadata((prev) => ({
            ...prev,
            conversion_agent: status.conversion_agent || status.current_agent || prev.conversion_agent,
            conversion_agent_key: status.conversion_agent_key || prev.conversion_agent_key,
            quality_gate_status: statusFromPayload(status.quality_gate) || prev.quality_gate_status,
            validation_status: statusFromPayload(status.validation) || prev.validation_status,
          }));
          setPipelineRunning(status.status === 'RUNNING');
        }
      } catch (err) {
        console.error('Failed to load pipeline status:', err);
      }
    };

    loadStatus();

    return () => {
      cancelled = true;
    };
  }, [hasRunId, runId, targetLanguage]);

  useEffect(() => {
    if (!hasRunId || !targetLanguage) return;

    if (!pipelineRunning && pipelineStatus?.status !== 'RUNNING') return;

    const interval = window.setInterval(async () => {
      try {
        const status = await getCodeGenerationPipelineStatus(runId, targetLanguage);

        setPipelineStatus(status);
        setWorkflowMetadata((prev) => ({
          ...prev,
          conversion_agent: status.conversion_agent || status.current_agent || prev.conversion_agent,
          conversion_agent_key: status.conversion_agent_key || prev.conversion_agent_key,
          quality_gate_status: statusFromPayload(status.quality_gate) || prev.quality_gate_status,
          validation_status: statusFromPayload(status.validation) || prev.validation_status,
        }));

        if (status.status !== 'RUNNING') {
          setPipelineRunning(false);
          window.clearInterval(interval);

          if (status.download_allowed) {
            await loadExistingData();
          }
        }
      } catch (err) {
        console.error('Failed to poll pipeline status:', err);
      }
    }, 2500);

    return () => window.clearInterval(interval);
  }, [hasRunId, runId, targetLanguage, pipelineRunning, pipelineStatus?.status]);

  const handleGenerateWorkingCode = async (force = false) => {
    if (!hasRunId) {
      setError('Please select or enter a run id first.');
      return;
    }
    if (force && !window.confirm('Regenerate code and replace the saved generated output for this run?')) return;

    setError('');
    setMessage('');
    setPipelineRunning(true);
    setValidationResult(null);
    setWorkflowMetadata({});
    setFixResult(null);
    setReportResult(null);

    const startingStatus: PipelineStatusResponse = {
      run_id: runId,
      target_language: targetLanguage,
      target_display_name: targetLanguageLabel(targetLanguage),
      status: 'RUNNING',
      stage: `Starting ${targetLanguageLabel(targetLanguage)} code generation pipeline...`,
      progress: 1,
      download_allowed: false,
    };

    setPipelineStatus(startingStatus);

    try {
      const result = await runFullCodeGeneration(runId, targetLanguage, force);

      setPipelineStatus(result);
      setWorkflowMetadata((prev) => ({
        ...prev,
        conversion_agent: result.conversion_agent || result.current_agent || prev.conversion_agent,
        conversion_agent_key: result.conversion_agent_key || prev.conversion_agent_key,
        quality_gate_status: statusFromPayload(result.quality_gate) || prev.quality_gate_status,
        validation_status: statusFromPayload(result.validation) || prev.validation_status,
      }));
      setPipelineRunning(result.status === 'RUNNING');

      if (result.status === 'COMPLETED' && result.download_allowed) {
        setMessage(result.cached ? 'Using saved generated code.' : 'Generated working code is ready to download.');
        await loadExistingData();
      } else {
        setError(
          result.stage ||
            'Code generation completed but the output is not ready for download.',
        );
      }
    } catch (err) {
      setPipelineRunning(false);
      setError(err instanceof Error ? err.message : 'Failed to generate working code');
    }
  };

  const handleFinalizeRegistry = async () => {
    if (!hasRunId) {
      setError('Please select or enter a run id first.');
      return;
    }

    setLockingRegistry(true);
    setError('');
    setMessage('');

    try {
      const response = await finalizeSymbolRegistry(runId, targetLanguage);
      setRegistry(response);
      setMessage(
        `Registry locked: ${response.type_mapping_count} type mappings and ${response.signature_count} method signatures.`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to finalize symbol registry');
    } finally {
      setLockingRegistry(false);
    }
  };

  const handleGenerateReport = async () => {
    if (!hasRunId) {
      setError('Please select or enter a run id first.');
      return;
    }

    setReportLoading(true);
    setError('');
    setMessage('');

    try {
      await generateMigrationReport(runId, targetLanguage);
      const report = await readMigrationReport(runId, targetLanguage);
      setReportResult(report);
      setMessage('Migration report generated successfully.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate migration report');
    } finally {
      setReportLoading(false);
    }
  };

  const handleCreatePlan = async () => {
    if (!hasRunId) {
      setError('Please select or enter a run id first.');
      return;
    }

    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await createConversionPlan(runId, targetLanguage);
      setPlans(response.plans || []);
      setActivePlan(response.plans?.[0] || null);

      if (response.errors?.length) {
        setError(response.errors.map((item) => `${item.filename}: ${item.error}`).join('\n'));
      }

      setMessage(`Created ${response.count} ${selectedTarget.label} conversion plan(s).`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversion plan');
    } finally {
      setLoading(false);
    }
  };

  const handleFixGeneratedCode = async () => {
    if (!hasRunId) {
      setError('Please select or enter a run id first.');
      return;
    }

    setFixing(true);
    setError('');
    setMessage('');

    try {
      const response = await fixGeneratedCode(runId, targetLanguage, 3);
      setFixResult(response);
      setValidationResult(null);
      setReportResult(null);

      if (response.status === 'FIXED' && response.fixed_files.length > 0) {
        setMessage(`Fixed ${response.fixed_files.length} generated file(s). Run validation again.`);
        const files = await listGeneratedFiles(runId, targetLanguage);
        setGeneratedFiles(files.files || []);
        setSelectedFile(null);
      } else {
        setError(response.message || 'No files were fixed.');
      }

      if (response.errors?.length) {
        setError(response.errors.map((item) => `${item.path}: ${item.error}`).join('\n'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fix generated code');
    } finally {
      setFixing(false);
    }
  };

  const handleValidateProject = async () => {
    if (!hasRunId) {
      setError('Please select or enter a run id first.');
      return;
    }

    setValidating(true);
    setError('');
    setMessage('');

    try {
      const response = await validateGeneratedProject(runId, targetLanguage);
      setValidationResult(response);
      setWorkflowMetadata((prev) => ({ ...prev, ...response }));

      if (response.success) {
        setMessage(`Validation passed using: ${response.command}`);
      } else {
        setError(`Validation failed using: ${response.command}\n${response.stderr || response.stdout}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to validate generated project');
    } finally {
      setValidating(false);
    }
  };

  const handleGenerateCode = async () => {
    if (!hasRunId) {
      setError('Please select or enter a run id first.');
      return;
    }

    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await generateCode(runId, targetLanguage);
      setWorkflowMetadata((prev) => ({ ...prev, ...response }));

      if (response.errors?.length) {
        setError(response.errors.map((item) => `${item.filename}: ${item.error}`).join('\n'));
      }

      setMessage(`Generated ${response.count} file(s) for ${selectedTarget.label} ${selectedTarget.framework}.`);

      const files = await listGeneratedFiles(runId, targetLanguage);
      setGeneratedFiles(files.files || []);
      setSelectedFile(null);
      setValidationResult(null);
      setFixResult(null);
      setReportResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate code');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenFile = async (file: GeneratedFileSummary) => {
    setLoadingFiles(true);
    setError('');

    try {
      const content = await readGeneratedFile(runId, targetLanguage, file.path);
      setSelectedFile(content);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to read generated file');
    } finally {
      setLoadingFiles(false);
    }
  };

  const draftDownloadUrl = hasRunId
    ? generatedProjectDownloadUrl(runId, targetLanguage, false)
    : '#';
  const verifiedDownloadUrl = hasRunId
    ? generatedProjectDownloadUrl(runId, targetLanguage, true)
    : '#';
  const canDownloadDraft = hasRunId && generatedFiles.length > 0;
  const canDownloadZip =
    pipelineStatus?.download_allowed === true ||
    validationResult?.download_allowed === true;
  const canDownloadVerified =
    hasRunId &&
    generatedFiles.length > 0 &&
    canDownloadZip &&
    validationResult?.quality_gate?.success !== false;
  const resolvedQualityGateStatus =
    workflowMetadata.quality_gate_status ||
    statusFromPayload(pipelineStatus?.quality_gate) ||
    validationResult?.quality_gate?.status ||
    'PENDING';
  const resolvedValidationStatus =
    workflowMetadata.validation_status ||
    statusFromPayload(pipelineStatus?.validation) ||
    validationResult?.status ||
    'PENDING';
  const resolvedConversionAgent =
    workflowMetadata.conversion_agent ||
    pipelineStatus?.conversion_agent ||
    pipelineStatus?.current_agent ||
    conversionAgentName(targetLanguage);
  const resolvedConversionAgentKey =
    workflowMetadata.conversion_agent_key ||
    pipelineStatus?.conversion_agent_key ||
    targetLanguage;
  const resolvedBusinessRulesUsed = workflowMetadata.business_rules_used ?? Boolean(plans.length);
  const resolvedProceduralFlowUsed = workflowMetadata.procedural_flow_used ?? Boolean(pipelineStatus?.steps?.length);
  const manualDebugActions = (
    <div className="flex flex-wrap gap-2">
      <button
        onClick={handleFinalizeRegistry}
        className="btn-secondary flex items-center gap-2"
        disabled={lockingRegistry || loading || !hasRunId}
      >
        {lockingRegistry ? <Loader2 className="animate-spin" size={18} /> : <LockKeyhole size={18} />}
        Lock Registry
      </button>

      <button
        onClick={handleCreatePlan}
        className="btn-secondary flex items-center gap-2"
        disabled={loading || !hasRunId}
      >
        {loading ? <Loader2 className="animate-spin" size={18} /> : <Route size={18} />}
        Create Plan
      </button>

      <button
        onClick={handleGenerateCode}
        className="btn-glow"
        disabled={loading || !hasRunId}
      >
        {loading ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
        Generate Code
      </button>
      <button
        onClick={handleValidateProject}
        className="btn-secondary flex items-center gap-2"
        disabled={validating || loading || !hasRunId || generatedFiles.length === 0}
      >
        {validating ? <Loader2 className="animate-spin" size={18} /> : <Terminal size={18} />}
        Validate
      </button>
      <button
        onClick={handleFixGeneratedCode}
        className="btn-secondary flex items-center gap-2"
        disabled={fixing || validating || loading || !hasRunId || !validationResult || validationResult.success}
      >
        {fixing ? <Loader2 className="animate-spin" size={18} /> : <Wand2 size={18} />}
        Fix Errors
      </button>
      <button
        onClick={handleGenerateReport}
        className="btn-secondary flex items-center gap-2"
        disabled={reportLoading || loading || !hasRunId || generatedFiles.length === 0}
      >
        {reportLoading ? <Loader2 className="animate-spin" size={18} /> : <ScrollText size={18} />}
        Report
      </button>
    </div>
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Code Generation"
        description="Create conversion plans and generate modern Java, Python, or C# code from COBOL/Telon analysis."
        meta={<StatusBadge status={generatedFiles.length ? 'Generated' : plans.length ? 'Planned' : 'Ready'} pulse={loading} />}
      />

      <section className="glass-card p-5">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_240px]">
          <div>
            <label className="text-body-sm font-semibold uppercase tracking-wide">
              Run ID
            </label>
            <input
              value={runId}
              onChange={(event) => {
                const nextRunId = event.target.value;
                setRunId(nextRunId);
                localStorage.setItem('current_run_id', nextRunId);
                setTargetLanguage(getLockedTargetLanguage(nextRunId));
                setSelectedFile(null);
                setRegistry(null);
                setValidationResult(null);
                setWorkflowMetadata({});
                setFixResult(null);
                setReportResult(null);
              }}
              placeholder="Enter selected run_id"
              className="mt-2 w-full rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] px-4 py-3 font-mono text-sm text-[var(--terminal-text)] outline-none focus:ring-2 focus:ring-[var(--corporate-accent)]"
            />
            <p className="mt-2 text-body-sm">
              This should match the project run id used for discovery, technical YAML, and business logic extraction.
            </p>
          </div>

          <div>
            <label className="text-body-sm font-semibold uppercase tracking-wide">
              Locked Target
            </label>

            <div className="mt-2 rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] px-4 py-3">
              <p className="text-sm font-bold text-[var(--terminal-text)]">
                {selectedTarget.label} - {selectedTarget.framework}
              </p>
              <p className="mt-1 text-xs text-[var(--text-muted)]">
                Selected during Initial Setup. Change it there before creating a new run.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="glass-card p-5">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-[var(--corporate-accent-soft)] p-2 text-[var(--corporate-accent)]">
            <Code2 size={18} />
          </div>

          <div>
            <h3 className="text-heading">
              Generating {selectedTarget.label} - {selectedTarget.framework}
            </h3>
            <p className="mt-2 text-body-sm">
              {selectedTarget.description}
            </p>
            <p className="mt-2 text-xs text-[var(--text-muted)]">
              Target language is fixed from Initial Setup to avoid duplicate planning and token waste.
            </p>
          </div>
        </div>
      </section>

      <section className="glass-card p-5">
        <SectionLabel
          icon={<Route size={18} />}
          title="Agentic Workflow"
          subtitle="Conversion agent, source context usage, fallback, and gate status for this run."
        />

        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Target</p>
            <p className="mt-1 font-mono text-sm font-bold text-[var(--terminal-text)]">{targetDisplayName}</p>
          </div>
          <div className="rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Agent</p>
            <p className="mt-1 truncate font-mono text-sm font-bold text-[var(--terminal-text)]" title={resolvedConversionAgent}>
              {resolvedConversionAgent}
            </p>
            <p className="mt-1 font-mono text-[10px] text-[var(--text-muted)]">{resolvedConversionAgentKey}</p>
          </div>
          <div className="rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Business Rules Used</p>
            <p className="mt-1 font-mono text-sm font-bold text-[var(--terminal-text)]">{yesNo(resolvedBusinessRulesUsed)}</p>
          </div>
          <div className="rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Program Flow Used</p>
            <p className="mt-1 font-mono text-sm font-bold text-[var(--terminal-text)]">{yesNo(resolvedProceduralFlowUsed)}</p>
          </div>
          <div className="rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Fallback Used</p>
            <p className="mt-1 font-mono text-sm font-bold text-[var(--terminal-text)]">{yesNo(workflowMetadata.fallback_used)}</p>
            <p className="mt-1 truncate text-xs text-[var(--text-muted)]" title={workflowMetadata.fallback_reason || 'None'}>
              {workflowMetadata.fallback_reason || 'None'}
            </p>
          </div>
          <div className="rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Quality Gate Status</p>
            <div className="mt-2">
              <StatusBadge status={resolvedQualityGateStatus} pulse={pipelineStatus?.status === 'RUNNING'} />
            </div>
          </div>
          <div className="rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Validation Status</p>
            <div className="mt-2">
              <StatusBadge status={resolvedValidationStatus} pulse={pipelineStatus?.status === 'RUNNING'} />
            </div>
          </div>
          <div className="rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--text-muted)]">Files</p>
            <p className="mt-1 font-mono text-sm font-bold text-[var(--terminal-text)]">
              {pipelineStatus?.generated_files ?? generatedFiles.length} generated
            </p>
            <p className="mt-1 font-mono text-[10px] text-[var(--text-muted)]">
              {pipelineStatus?.planned_files ?? plans.length} planned / {pipelineStatus?.total_files ?? 'unknown'} total
            </p>
          </div>
        </div>
      </section>

      <section className="glass-card p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-body-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              Code Generation
            </p>
            <h2 className="mt-1 text-2xl font-black text-[var(--text-primary)]">
              Generate {targetDisplayName} Code
            </h2>
            <p className="mt-2 text-body-sm">
              The system will plan, generate, repair, validate, and prepare the ZIP automatically.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => handleGenerateWorkingCode(false)}
              disabled={pipelineRunning || !hasRunId}
              className="btn-glow flex items-center gap-2 px-5 py-3 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {pipelineRunning ? <Loader2 className="animate-spin" size={18} /> : <Sparkles size={18} />}
              {pipelineRunning ? 'Generating...' : 'Generate Working Code'}
            </button>
            <button
              type="button"
              onClick={() => handleGenerateWorkingCode(true)}
              disabled={pipelineRunning || !hasRunId}
              className="btn-secondary flex items-center gap-2 px-5 py-3 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {pipelineRunning ? <Loader2 className="animate-spin" size={18} /> : <RefreshCcw size={18} />}
              Regenerate
            </button>

            <a
              href={isPipelineSuccessful ? generatedProjectDownloadUrl(runId, targetLanguage) : '#'}
              onClick={(event) => {
                if (!isPipelineSuccessful) {
                  event.preventDefault();
                }
              }}
              className={[
                'btn-secondary flex items-center gap-2 px-5 py-3',
                !isPipelineSuccessful ? 'pointer-events-none opacity-50' : '',
              ].join(' ')}
              title={
                isPipelineSuccessful
                  ? 'Download validation-passed generated code ZIP.'
                  : 'Download unlocks after the full pipeline completes successfully.'
              }
            >
              <Download size={18} />
              Download ZIP
            </a>

            <button
              type="button"
              onClick={handleGenerateReport}
              disabled={reportLoading || pipelineRunning || !hasRunId || !isPipelineSuccessful}
              className="btn-secondary flex items-center gap-2 px-5 py-3 disabled:cursor-not-allowed disabled:opacity-50"
              title={
                isPipelineSuccessful
                  ? 'Generate or refresh the migration report.'
                  : 'Report unlocks after the full pipeline completes successfully.'
              }
            >
              {reportLoading ? <Loader2 className="animate-spin" size={18} /> : <ScrollText size={18} />}
              Report
            </button>
          </div>
        </div>

        <div className="mt-6">
          <div className="mb-2 flex items-center justify-between gap-4">
            <span className="min-w-0 text-sm font-semibold text-[var(--text-primary)]">
              {pipelineStatus?.stage || 'Code generation has not started.'}
            </span>
            <span className="shrink-0 font-mono text-sm font-bold text-[var(--terminal-text)]">
              {pipelineProgress}%
            </span>
          </div>

          <div className="h-3 overflow-hidden rounded-full bg-[var(--corporate-border)]">
            <div
              className={[
                'h-full rounded-full transition-all duration-500',
                isPipelineFailed
                  ? 'bg-[var(--corporate-danger)]'
                  : isPipelineSuccessful
                    ? 'bg-[var(--corporate-success)]'
                    : 'bg-[var(--corporate-accent)]',
              ].join(' ')}
              style={{ width: `${pipelineProgress}%` }}
            />
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
            <StatusBadge
              status={pipelineStatus?.status || 'NOT_STARTED'}
              pulse={pipelineStatus?.status === 'RUNNING'}
            />

            <span className="text-[var(--text-muted)]">
              Target: {targetDisplayName}
            </span>

            <span className="text-[var(--text-muted)]">
              Download: {pipelineStatus?.download_allowed ? 'Allowed' : 'Locked until validation passes'}
            </span>
          </div>
        </div>
      </section>

      <section className="glass-card p-5">
        <button
          type="button"
          onClick={() => setShowAdvanced((value) => !value)}
          className="flex w-full items-center justify-between gap-4 text-left"
        >
          <span className="font-semibold text-[var(--text-primary)]">
            Advanced generation details
          </span>
          <span className="text-sm text-[var(--text-muted)]">
            {showAdvanced ? 'Hide' : 'Show'}
          </span>
        </button>

        {showAdvanced && (
          <div className="mt-5 space-y-5">
            <div className="rounded-lg border border-dashed border-[var(--corporate-border)] bg-[var(--surface-soft)] p-5">
              <h3 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">
                Manual debug actions
              </h3>
              {manualDebugActions}
            </div>

            <div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">
                Pipeline steps
              </h3>

              {pipelineStatus?.steps?.length ? (
                <div className="mt-2 overflow-hidden rounded-lg border border-[var(--corporate-border)]">
                  {pipelineStatus.steps.map((step, index) => (
                    <div
                      key={`${step.step}-${index}`}
                      className="border-b border-[var(--corporate-border)] px-4 py-3 last:border-b-0"
                    >
                      <div className="font-mono text-xs font-bold text-[var(--terminal-text)]">
                        {step.step}
                      </div>
                      <pre className="mt-2 max-h-48 overflow-auto rounded-lg bg-[var(--terminal-bg)] p-3 text-xs text-[var(--terminal-text)]">
                        {JSON.stringify(step, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-2 text-body-sm">
                  No pipeline steps recorded yet.
                </p>
              )}
            </div>

            {pipelineStatus?.errors?.length ? (
              <div>
                <h3 className="text-sm font-semibold text-[var(--corporate-danger)]">Errors</h3>
                <pre className="mt-2 max-h-72 overflow-auto rounded-lg border border-[var(--corporate-danger)] bg-[var(--terminal-bg)] p-4 text-xs text-[var(--terminal-text)]">
                  {JSON.stringify(pipelineStatus.errors, null, 2)}
                </pre>
              </div>
            ) : null}
          </div>
        )}
      </section>

      {(message || error) && (
        <section className="glass-card p-4">
          {message && (
            <div className="flex items-center gap-2 text-sm font-semibold text-[var(--corporate-success)]">
              <Sparkles size={16} />
              <span>{message}</span>
            </div>
          )}

          {error && (
            <div className="mt-2 flex items-start gap-2 whitespace-pre-wrap text-sm font-semibold text-[var(--corporate-danger)]">
              <AlertTriangle size={16} className="mt-0.5" />
              <span>{error}</span>
            </div>
          )}
        </section>
      )}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[420px_1fr]">
        <div className="space-y-6">
          <section className="glass-card p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-lg bg-[var(--corporate-accent-soft)] p-2 text-[var(--corporate-accent)]">
                <LockKeyhole size={18} />
              </div>
              <div>
                <h3 className="text-heading">Locked Symbol Registry</h3>
                <p className="text-body-sm">
                  Locks COBOL/Telon variable names, target types, and paragraph-to-method mappings before conversion.
                </p>
              </div>
            </div>

            {!registry ? (
              <div className="rounded-lg border border-dashed border-[var(--corporate-border)] p-5 text-body-sm">
                No registry loaded yet. Click <b>Lock Registry</b> before creating a conversion plan.
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-[var(--corporate-border)] p-4">
                  <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">
                    Type Mappings
                  </p>
                  <p className="mt-2 text-2xl font-black">
                    {registry.type_mapping_count}
                  </p>
                </div>

                <div className="rounded-lg border border-[var(--corporate-border)] p-4">
                  <p className="text-xs uppercase tracking-wide text-[var(--text-muted)]">
                    Method Signatures
                  </p>
                  <p className="mt-2 text-2xl font-black">
                    {registry.signature_count}
                  </p>
                </div>

                <div className="max-h-60 overflow-auto rounded-lg border border-[var(--corporate-border)] p-3 sm:col-span-2">
                  {registry.type_mappings.slice(0, 30).map((item) => (
                    <p key={`${item.source_name}-${item.target_name}`} className="font-mono text-xs">
                      {item.source_name} -&gt; {item.target_name}: {item.target_type}
                    </p>
                  ))}

                  {registry.signatures.slice(0, 30).map((item) => (
                    <p key={`${item.source_paragraph}-${item.target_method}`} className="font-mono text-xs">
                      {item.source_paragraph} -&gt; {item.target_method}()
                    </p>
                  ))}
                </div>
              </div>
            )}
          </section>

          <section className="glass-card p-5">
            <div className="mb-4 flex items-center justify-between">
              <SectionLabel>Conversion Plans</SectionLabel>
              <button
                onClick={loadExistingData}
                className="btn-secondary flex items-center gap-2 px-3 py-2"
                disabled={loadingFiles || !hasRunId}
              >
                {loadingFiles ? <Loader2 className="animate-spin" size={14} /> : <RefreshCcw size={14} />}
                Refresh
              </button>
            </div>

            {plans.length === 0 ? (
              <div className="rounded-lg border border-dashed border-[var(--corporate-border)] p-5 text-body-sm">
                No conversion plans loaded yet. Click <b>Create Plan</b>.
              </div>
            ) : (
              <div className="space-y-3">
                {plans.map((plan) => (
                  <button
                    key={`${plan.file_id}-${plan.source_file}`}
                    onClick={() => setActivePlan(plan)}
                    className={[
                      'w-full rounded-lg border p-4 text-left transition-all',
                      activePlan?.file_id === plan.file_id
                        ? 'border-[var(--corporate-accent)] bg-[var(--corporate-accent-soft)]'
                        : 'border-[var(--corporate-border)] bg-[var(--surface)] hover:border-[var(--corporate-accent)]',
                    ].join(' ')}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-semibold">{plan.source_file}</h3>
                      <StatusBadge status={plan.target_framework} pulse={false} />
                    </div>
                    <p className="mt-2 line-clamp-2 text-body-sm">
                      {plan.summary || 'No summary returned.'}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2 text-xs">
                      <span className="rounded-full border border-[var(--corporate-border)] px-2 py-1">
                        {plan.classes?.length || 0} classes
                      </span>
                      <span className="rounded-full border border-[var(--corporate-border)] px-2 py-1">
                        {plan.methods?.length || 0} methods
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>

        </div>

        <div className="space-y-6">
          <section className="glass-card p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-lg bg-[var(--corporate-accent-soft)] p-2 text-[var(--corporate-accent)]">
                <Braces size={18} />
              </div>
              <div>
                <h3 className="text-heading">Plan Preview</h3>
                <p className="text-body-sm">
                  Shows target classes, methods, assumptions, and unresolved dependencies.
                </p>
              </div>
            </div>

            {!activePlan ? (
              <div className="rounded-lg border border-dashed border-[var(--corporate-border)] p-5 text-body-sm">
                Select a conversion plan to preview it.
              </div>
            ) : (
              <div className="space-y-5">
                <div>
                  <h4 className="font-semibold">{activePlan.source_file}</h4>
                  <p className="mt-1 text-body-sm">{activePlan.summary}</p>
                </div>

                <div>
                  <h4 className="mb-2 text-sm font-bold uppercase tracking-wide">Target Structure</h4>
                  <div className="space-y-2">
                    {(activePlan.classes || []).map((item) => (
                      <div key={`${item.class_name}-${item.file_path}`} className="rounded-lg border border-[var(--corporate-border)] p-3">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="font-semibold">{item.class_name}</span>
                          <span className="rounded-full bg-[var(--corporate-accent-soft)] px-2 py-1 text-xs font-semibold text-[var(--corporate-accent)]">
                            {item.layer}
                          </span>
                        </div>
                        <p className="mt-1 break-all font-mono text-xs text-[var(--text-muted)]">
                          {item.file_path}
                        </p>
                        <p className="mt-2 text-body-sm">{item.responsibility}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {(activePlan.unresolved_items?.length || 0) > 0 && (
                  <div>
                    <h4 className="mb-2 text-sm font-bold uppercase tracking-wide text-[var(--corporate-warning)]">
                      Unresolved Items
                    </h4>
                    <ul className="space-y-1 text-body-sm">
                      {activePlan.unresolved_items?.map((item) => (
                        <li key={item}>• {item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>

          <section className="glass-card p-5">
            <div className="mb-4 flex items-center justify-between">
              <SectionLabel>Generated Files</SectionLabel>

              <div className="flex flex-wrap gap-2">
                <a
                  href={draftDownloadUrl}
                  className={[
                    'btn-secondary flex items-center gap-2 px-3 py-2',
                    !canDownloadDraft ? 'pointer-events-none opacity-50' : '',
                  ].join(' ')}
                  title={canDownloadDraft ? 'Download current generated code ZIP' : 'Generate code before downloading ZIP.'}
                >
                  <Download size={14} />
                  Download ZIP
                </a>

                <a
                  href={verifiedDownloadUrl}
                  className={[
                    'btn-secondary flex items-center gap-2 px-3 py-2',
                    !canDownloadVerified ? 'pointer-events-none opacity-50' : '',
                  ].join(' ')}
                  title={canDownloadVerified ? 'Download validation-passed generated code ZIP' : 'Validate successfully before downloading verified ZIP.'}
                >
                  <LockKeyhole size={14} />
                  Verified ZIP
                </a>
              </div>
            </div>

            {generatedFiles.length === 0 ? (
              <div className="rounded-lg border border-dashed border-[var(--corporate-border)] p-5 text-body-sm">
                No generated files yet. Click <b>Generate Code</b> after creating a plan.
              </div>
            ) : (
              <div className="max-h-[460px] space-y-2 overflow-auto pr-1">
                {generatedFiles.map((file) => (
                  <button
                    key={file.path}
                    onClick={() => handleOpenFile(file)}
                    className={[
                      'w-full rounded-lg border p-3 text-left transition-all',
                      selectedFile?.path === file.path
                        ? 'border-[var(--corporate-accent)] bg-[var(--corporate-accent-soft)]'
                        : 'border-[var(--corporate-border)] bg-[var(--surface)] hover:border-[var(--corporate-accent)]',
                    ].join(' ')}
                  >
                    <div className="flex items-start gap-2">
                      <FileCode2 size={16} className="mt-0.5 text-[var(--corporate-accent)]" />
                      <div className="min-w-0 flex-1">
                        <p className="break-all font-mono text-xs font-semibold">
                          {file.path}
                        </p>
                        <p className="mt-1 text-xs text-[var(--text-muted)]">
                          {formatBytes(file.size)}
                        </p>
                      </div>
                      <Eye size={14} />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </section>

          <section className="glass-card p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-lg bg-[var(--corporate-accent-soft)] p-2 text-[var(--corporate-accent)]">
                <Terminal size={18} />
              </div>
              <div>
                <h3 className="text-heading">Validation Result</h3>
                <p className="text-body-sm">
                  Runs compile or syntax checks against the generated project.
                </p>
              </div>
            </div>

            {!validationResult ? (
              <div className="rounded-lg border border-dashed border-[var(--corporate-border)] p-5 text-body-sm">
                No validation result yet. Click <b>Validate</b> after generating code.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  {validationResult.success ? (
                    <CheckCircle2 className="text-[var(--corporate-success)]" size={22} />
                  ) : (
                    <XCircle className="text-[var(--corporate-danger)]" size={22} />
                  )}

                  <div>
                    <p className="font-semibold">
                      {validationResult.success ? 'Validation Passed' : 'Validation Failed'}
                    </p>
                    <p className="font-mono text-xs text-[var(--text-muted)]">
                      {validationResult.command}
                    </p>
                  </div>

                  <StatusBadge
                    status={validationResult.returncode === 0 ? 'Return Code 0' : `Return Code ${validationResult.returncode}`}
                    pulse={false}
                  />
                </div>

                {validationResult.checked_files?.length ? (
                  <div>
                    <h4 className="mb-2 text-sm font-bold uppercase tracking-wide">
                      Checked Files
                    </h4>
                    <div className="max-h-32 overflow-auto rounded-lg border border-[var(--corporate-border)] p-3">
                      {validationResult.checked_files.map((file) => (
                        <p key={file} className="font-mono text-xs">
                          {file}
                        </p>
                      ))}
                    </div>
                  </div>
                ) : null}

                {(validationResult.stdout || validationResult.stderr) && (
                  <pre className="max-h-72 overflow-auto rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4 text-xs text-[var(--terminal-text)]">
                    <code>{validationResult.stderr || validationResult.stdout}</code>
                  </pre>
                )}
              </div>
            )}
          </section>
          <section className="glass-card p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-lg bg-[var(--corporate-accent-soft)] p-2 text-[var(--corporate-accent)]">
                <Wand2 size={18} />
              </div>
              <div>
                <h3 className="text-heading">Auto-Fix Result</h3>
                <p className="text-body-sm">
                  Uses compiler or syntax errors to repair generated files.
                </p>
              </div>
            </div>

            {!fixResult ? (
              <div className="rounded-lg border border-dashed border-[var(--corporate-border)] p-5 text-body-sm">
                No fix attempt yet. Run <b>Validate</b>, then click <b>Fix Errors</b> if validation fails.
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <StatusBadge status={fixResult.status} pulse={false} />
                  <p className="text-body-sm">
                    {fixResult.fixed_files.length} file(s) fixed.
                  </p>
                </div>

                {fixResult.fixed_files.length > 0 && (
                  <div className="space-y-2">
                    {fixResult.fixed_files.map((file) => (
                      <div key={file.path} className="rounded-lg border border-[var(--corporate-border)] p-3">
                        <p className="break-all font-mono text-xs font-semibold">{file.path}</p>
                        <p className="mt-2 text-body-sm">{file.fix_summary}</p>
                        <p className="mt-2 break-all font-mono text-[11px] text-[var(--text-muted)]">
                          Backup: {file.backup_path}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {fixResult.errors?.length ? (
                  <pre className="max-h-64 overflow-auto rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4 text-xs text-[var(--terminal-text)]">
                    <code>
                      {fixResult.errors.map((item) => `${item.path}: ${item.error}`).join('\n')}
                    </code>
                  </pre>
                ) : null}
              </div>
            )}
          </section>
          <section className="glass-card p-5">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-lg bg-[var(--corporate-accent-soft)] p-2 text-[var(--corporate-accent)]">
                <ScrollText size={18} />
              </div>
              <div>
                <h3 className="text-heading">Migration Report</h3>
                <p className="text-body-sm">
                  Summarizes source files, generated files, business rules, dependencies, validation, and fix attempts.
                </p>
              </div>
            </div>

            {!reportResult?.content ? (
              <div className="rounded-lg border border-dashed border-[var(--corporate-border)] p-5 text-body-sm">
                No migration report generated yet. Click <b>Report</b> after generating and validating code.
              </div>
            ) : (
              <div className="space-y-3">
                <div className="rounded-lg border border-[var(--corporate-border)] p-3">
                  <p className="break-all font-mono text-xs font-semibold">
                    {reportResult.path}
                  </p>
                </div>

                <pre className="max-h-[680px] overflow-auto rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4 text-xs text-[var(--terminal-text)] whitespace-pre-wrap">
                  <code>{reportResult.content}</code>
                </pre>
              </div>
            )}
          </section>
          <section className="glass-card p-5">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-[var(--corporate-accent-soft)] p-2 text-[var(--corporate-accent)]">
                  <FileText size={18} />
                </div>
                <div>
                  <h3 className="text-heading">Generated File Viewer</h3>
                  <p className="text-body-sm">
                    Open generated code files from the project output folder.
                  </p>
                </div>
              </div>

              <a
                href={draftDownloadUrl}
                className={[
                  'btn-secondary flex items-center gap-2 px-3 py-2',
                  !canDownloadDraft ? 'pointer-events-none opacity-50' : '',
                ].join(' ')}
                title={canDownloadDraft ? 'Download current generated code ZIP' : 'Generate code before downloading ZIP.'}
              >
                <Download size={14} />
                Download ZIP
              </a>
            </div>

            {!selectedFile ? (
              <div className="rounded-lg border border-dashed border-[var(--corporate-border)] p-5 text-body-sm">
                Select a generated file to view its content.
              </div>
            ) : (
              <div>
                <div className="mb-3 rounded-lg border border-[var(--corporate-border)] p-3">
                  <p className="break-all font-mono text-xs font-semibold">
                    {selectedFile.path}
                  </p>
                </div>

                <pre className="max-h-[680px] overflow-auto rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4 text-sm text-[var(--terminal-text)]">
                  <code>{selectedFile.content}</code>
                </pre>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};

export default CodeGeneration;
