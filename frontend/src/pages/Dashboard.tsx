import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Code2,
  Database,
  FileText,
  GitBranch,
  Layers,
  Lightbulb,
  Loader2,
  Rocket,
  ShieldCheck,
  Target,
  Trash2,
  Zap,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { ProjectAPI } from '../services/api';
import type { DependencyRelation, FileRecord, ProjectSummary, ServiceHealth, ServiceStatus } from '../services/api';
import Tooltip from '../components/Tooltip';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';

type BlueprintActivity = string | { name: string; progress: number };

interface BlueprintStage {
  id: number;
  name: string;
  status: 'Complete' | 'In Progress' | 'Pending';
  desc: string;
  activities: BlueprintActivity[];
}

interface KPICardProps {
  label: string;
  value: string | number;
  icon: React.ElementType;
  status: 'Healthy' | 'Review' | 'Action';
  featured?: boolean;
  description?: string;
}

type RuleRecord = { status?: string };
type ComplexityFile = { score?: number; tier?: string; chunks?: number };
type DashboardMetrics = {
  files: FileRecord[];
  relations: DependencyRelation[];
  rules: RuleRecord[];
  complexityFiles: ComplexityFile[];
};

const JOURNEY_STEPS = [
  { name: 'Select Project', path: '/initial-setup', icon: Database, desc: 'Create a new migration run or resume a previous project.' },
  { name: 'Upload Source', path: '/initial-setup', icon: FileText, desc: 'Ingest ZIP archives or GitHub repos and perform language detection.' },
  { name: 'Discovery', path: '/discovery', icon: BrainCircuit, desc: 'Scan for CALLs, COPY-books, and SQL tables to build the dependency graph.' },
  { name: 'Knowledge Extraction', path: '/business-logic', icon: Layers, desc: 'Convert technical COBOL logic into human-readable business rules.' },
  { name: 'Plan Migration', path: '/dashboard', icon: Target, desc: 'Review backend-backed project health and readiness.' },
  { name: 'Generate Code', path: '/code-generation', icon: Code2, desc: 'Run the AI Factory to generate production-ready Java/C# code.' },
  { name: 'Refinement', path: '/mission-control', icon: ShieldCheck, desc: 'Run compile-test-fix loops to ensure syntactical health.' },
  { name: 'Deploy', path: '/code-generation', icon: Rocket, desc: 'Export the final codebase and generate the modernization audit report.' },
];

const emptyMetrics: DashboardMetrics = { files: [], relations: [], rules: [], complexityFiles: [] };
const emptyHealth: ServiceHealth = {
  ai_api: { active: false, detail: 'No active project selected.' },
  neo4j: { active: false, detail: 'No active project selected.' },
};

const KPICard = ({ label, value, icon: Icon, status, featured = false, description }: KPICardProps) => (
  <div className={`glass-card ${featured ? 'kpi-featured p-7' : 'p-5'} flex flex-col border border-slate-800 bg-slate-900/50`}>
    <div className="flex items-start justify-between gap-4">
      <span className="label">{label}</span>
      <span className="rounded-lg border border-slate-800 bg-slate-950/50 p-2 text-[var(--corporate-accent)]">
        <Icon size={featured ? 24 : 18} />
      </span>
    </div>
    <div className={featured ? 'text-display mt-8' : 'mt-5 text-3xl font-black tracking-tight text-[var(--corporate-text)]'}>{value}</div>
    <p className="text-body-sm mt-2">{description}</p>
    <div className="mt-auto pt-5">
      <StatusBadge status={status} />
    </div>
  </div>
);

const HealthIndicator = ({ label, status, loading }: { label: string; status: ServiceStatus; loading: boolean }) => (
  <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs font-black uppercase tracking-widest text-slate-500">{label}</span>
      <span
        className={`h-3 w-3 shrink-0 rounded-full ${
          loading ? 'bg-amber-400 shadow-[0_0_14px_rgba(251,191,36,0.75)]' : status.active ? 'bg-emerald-400 shadow-[0_0_14px_rgba(52,211,153,0.75)]' : 'bg-red-500 shadow-[0_0_14px_rgba(239,68,68,0.75)]'
        }`}
        aria-label={loading ? `${label} checking` : status.active ? `${label} active` : `${label} inactive`}
      />
    </div>
    <p className="mt-2 truncate text-xs text-slate-300">{status.provider || label}</p>
    <p className="mt-1 line-clamp-2 text-[11px] text-slate-500">{loading ? 'Checking service...' : status.detail || 'Status unavailable.'}</p>
  </div>
);
const normalizeRelationType = (value?: string) => String(value || '').toUpperCase();

const Dashboard = () => {
  const navigate = useNavigate();
  const [runId, setRunId] = useState<string | null>(localStorage.getItem('active_run_id'));
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetrics>(emptyMetrics);
  const [serviceHealth, setServiceHealth] = useState<ServiceHealth>(emptyHealth);
  const [healthLoading, setHealthLoading] = useState(false);
  const [metricsLoading, setMetricsLoading] = useState(false);
  const [isDeletingRuns, setIsDeletingRuns] = useState(false);

  const activeProject = useMemo(() => projects.find((p) => p.run_id === runId) || null, [projects, runId]);

  const derived = useMemo(() => {
    const confirmedFiles = metrics.files.filter((file) => file.status === 'CONFIRMED').length;
    const totalFiles = activeProject?.files_count ?? metrics.files.length;
    const complexModules = metrics.complexityFiles.filter((file) => {
      const tier = String(file.tier || '').toLowerCase();
      return tier === 'high' || tier === 'very high' || (file.score || 0) >= 15;
    }).length;
    const analysisChunks = metrics.complexityFiles.reduce((sum, file) => sum + Number(file.chunks || 0), 0);
    const verifiedRules = metrics.rules.filter((rule) => rule.status === 'VERIFIED').length;
    const pendingRules = metrics.rules.filter((rule) => (rule.status || 'PENDING') === 'PENDING').length;
    const criticalPaths = metrics.relations.filter((relation) => ['CALLS', 'EXECUTES', 'MAPS_TO'].includes(normalizeRelationType(relation.relation_type))).length;
    const sharedAssets = metrics.relations.filter((relation) => ['INCLUDES', 'ACCESSES', 'READS', 'WRITES'].includes(normalizeRelationType(relation.relation_type))).length;
    const progress = totalFiles === 0 ? 0 : Math.round((confirmedFiles / totalFiles) * 100);

    return { totalFiles, confirmedFiles, complexModules, analysisChunks, verifiedRules, pendingRules, criticalPaths, sharedAssets, progress };
  }, [activeProject?.files_count, metrics]);

  const blueprintStages: BlueprintStage[] = useMemo(() => [
    {
      id: 1,
      name: 'Environment Setup',
      status: activeProject ? 'Complete' : 'Pending',
      desc: activeProject ? 'Project and AI configuration are available.' : 'Create or select a run in Initial Setup.',
      activities: [activeProject?.ai_mode || activeProject?.llm_provider || 'AI pending', activeProject?.llm_model || 'Model pending', activeProject?.interaction_lang || 'Language pending'],
    },
    {
      id: 2,
      name: 'Discovery & Analysis',
      status: derived.totalFiles === 0 ? 'Pending' : derived.confirmedFiles === derived.totalFiles ? 'Complete' : 'In Progress',
      desc: `${derived.confirmedFiles} of ${derived.totalFiles} files confirmed.` ,
      activities: [`${metrics.relations.length} relations`, `${derived.analysisChunks} chunks`, `${derived.complexModules} complex modules`],
    },
    {
      id: 3,
      name: 'Knowledge Extraction',
      status: metrics.rules.length === 0 ? 'Pending' : derived.pendingRules === 0 ? 'Complete' : 'In Progress',
      desc: `${derived.verifiedRules} verified rules, ${derived.pendingRules} pending review.`,
      activities: [{ name: 'Rule Verification', progress: metrics.rules.length ? Math.round((derived.verifiedRules / metrics.rules.length) * 100) : 0 }],
    },
    {
      id: 4,
      name: 'Modern Code Generation',
      status: metrics.rules.length > 0 && derived.verifiedRules / Math.max(metrics.rules.length, 1) >= 0.8 ? 'In Progress' : 'Pending',
      desc: 'Unlocked after business rules reach the verification gate.',
      activities: ['DTO Generation', 'Domain Models', 'Service Layer'],
    },
    {
      id: 5,
      name: 'Agentic Refinement',
      status: 'Pending',
      desc: 'Compile-test-fix loops run after generated code is available.',
      activities: ['Compile-Test-Fix', 'Unit Tests', 'Optimization'],
    },
  ], [activeProject, derived, metrics.relations.length, metrics.rules.length]);

  useEffect(() => {
    void fetchProjectHistory();
  }, []);

  useEffect(() => {
    void loadDashboardMetrics(runId);
  }, [runId]);

  const fetchProjectHistory = async () => {
    try {
      const data = await ProjectAPI.list();
      setProjects(data);
      if (!runId && data[0]?.run_id) {
        setRunId(data[0].run_id);
        localStorage.setItem('active_run_id', data[0].run_id);
      }
      return data;
    } catch (e) {
      toast.error('Failed to load project history');
      return [] as ProjectSummary[];
    }
  };

  const loadDashboardMetrics = async (currentRunId: string | null) => {
    if (!currentRunId) {
      setMetrics(emptyMetrics);
      setServiceHealth(emptyHealth);
      return;
    }

    setMetricsLoading(true);
    setHealthLoading(true);
    try {
      const [projectDetail, discovery, complexity, rules, health] = await Promise.all([
        ProjectAPI.get(currentRunId),
        ProjectAPI.getDiscoveryData(currentRunId),
        ProjectAPI.getComplexity(currentRunId),
        ProjectAPI.getBusinessRules(currentRunId),
        ProjectAPI.getServiceHealth(currentRunId),
      ]);

      setProjects((current) => {
        const exists = current.some((project) => project.run_id === projectDetail.run_id);
        return exists ? current.map((project) => project.run_id === projectDetail.run_id ? projectDetail : project) : [projectDetail, ...current];
      });
      setMetrics({
        files: discovery.files || [],
        relations: discovery.relations || [],
        complexityFiles: complexity.files || [],
        rules: rules || [],
      });
      setServiceHealth(health || emptyHealth);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to load dashboard metrics');
      setMetrics(emptyMetrics);
      setServiceHealth(emptyHealth);
    } finally {
      setMetricsLoading(false);
      setHealthLoading(false);
    }
  };

  const handleProjectChange = (id: string) => {
    const project = projects.find((item) => item.run_id === id);
    setRunId(id);
    localStorage.setItem('active_run_id', id);
    toast.success(`Switched to ${project?.name || id}`);
    navigate('/initial-setup');
  };

  const handleDeleteAllRuns = async () => {
    if (projects.length === 0) {
      toast.error('No runs to delete');
      return;
    }
    if (!window.confirm('Delete all runs and uploaded files?')) return;

    setIsDeletingRuns(true);
    try {
      await ProjectAPI.deleteAllRuns();
      setProjects([]);
      setRunId(null);
      setMetrics(emptyMetrics);
      setServiceHealth(emptyHealth);
      localStorage.removeItem('active_run_id');
      localStorage.removeItem('modernizer_files');
      localStorage.removeItem('modernizer_pipeline_status');
      toast.success('All runs deleted');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to delete runs');
    } finally {
      setIsDeletingRuns(false);
    }
  };

  const stageProgress = (stage: BlueprintStage) => {
    if (stage.status === 'Complete') return 100;
    if (stage.status === 'In Progress') return 56;
    return 0;
  };

  const recommendation = derived.totalFiles === 0
    ? 'Upload source files in Initial Setup to populate discovery, complexity, and business-rule metrics.'
    : metrics.rules.length === 0
      ? `Run business-rule extraction for ${derived.totalFiles} uploaded files after discovery is ready.`
      : derived.pendingRules > 0
        ? `Review ${derived.pendingRules} pending business rules to unlock code generation.`
        : 'Business rules are verified. Continue to code generation or refinement.';

  return (
    <div className="space-y-12 pb-24 animate-in fade-in duration-700">
      <section className="premium-hero relative overflow-hidden rounded-3xl p-8 lg:p-10 shadow-2xl">
        <div className="premium-hero-watermark">Modernize</div>
        <div className="relative z-10">
          <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/20 px-4 py-2 text-xs font-black uppercase tracking-[0.18em] text-indigo-400">
            <Rocket size={14} /> Executive Command Center
          </div>
          <h1 className="text-hero max-w-5xl">Modernizer<span className="text-[var(--corporate-accent)]">AI</span></h1>
          <p className="text-body mt-5 max-w-2xl text-[var(--corporate-muted)]">
            Backend-backed project health for the active modernization run.
          </p>

          <div className="mt-8 grid gap-6 md:grid-cols-[minmax(0,270px)_minmax(0,260px)_auto] md:items-end">
            <div className="space-y-2">
              <p className="label">Active Project</p>
              <div className="relative group">
                <select
                  value={runId || ''}
                  onChange={(e) => handleProjectChange(e.target.value)}
                  className="w-full appearance-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 pr-10 text-sm font-bold text-white outline-none transition-all focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="" disabled>Select a Project</option>
                  {projects.map((proj) => (
                    <option key={proj.run_id} value={proj.run_id}>{proj.name || proj.run_id} ({proj.status})</option>
                  ))}
                </select>
                <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
                  <ChevronDown size={14} className="text-slate-500" />
                </div>
              </div>
              {activeProject && <StatusBadge status={activeProject.status} />}
            </div>

            <div className="space-y-2">
              <p className="label">File Confirmation</p>
              <div className="flex items-center gap-3">
                <p className="text-2xl font-black tracking-tight text-white">{derived.progress}%</p>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
                  <div className="h-full rounded-full bg-indigo-500 transition-all duration-700" style={{ width: `${derived.progress}%` }} />
                </div>
              </div>
              {metricsLoading && <p className="text-xs text-slate-500">Refreshing from backend...</p>}
            </div>

            <button onClick={handleDeleteAllRuns} disabled={isDeletingRuns || projects.length === 0} className="btn-glow disabled:cursor-not-allowed disabled:opacity-50">
              {isDeletingRuns ? <Loader2 className="animate-spin" size={16} /> : <Trash2 size={16} />}
              Delete Runs
            </button>
          </div>

          <div className="mt-6 grid gap-3 md:grid-cols-2">
            <HealthIndicator label="AI API Key" status={serviceHealth.ai_api} loading={healthLoading} />
            <HealthIndicator label="Neo4j" status={serviceHealth.neo4j} loading={healthLoading} />
          </div>
        </div>
      </section>

      <section>
        <SectionLabel>Modernization Journey</SectionLabel>
        <div className="timeline-scroll flex items-start overflow-x-auto pb-3">
          {JOURNEY_STEPS.map((step, i) => {
            const isDone = i < 2 && derived.totalFiles > 0;
            const isActive = step.path === '/dashboard';
            return (
              <Tooltip key={step.name} text={step.desc} position="top">
                <div className="flex min-w-[148px] items-start">
                  <button type="button" onClick={() => navigate(step.path)} className="group flex w-[128px] flex-col items-center text-center">
                    <span className={`mb-3 flex h-11 w-11 items-center justify-center rounded-full border transition-all group-hover:scale-110 ${isDone || isActive ? 'border-indigo-500/40 bg-indigo-500/20 text-indigo-400 shadow-lg shadow-indigo-500/20' : 'border-slate-800 bg-slate-900/50 text-slate-500'}`}>
                      <step.icon size={18} />
                    </span>
                    <span className="label mb-1">{String(i + 1).padStart(2, '0')}</span>
                    <span className={`text-xs font-extrabold ${isDone || isActive ? 'text-white' : 'text-slate-500'}`}>{step.name}</span>
                  </button>
                  {i < JOURNEY_STEPS.length - 1 && <span className={`mt-[22px] h-0.5 min-w-[34px] flex-1 ${isDone ? 'bg-indigo-500' : 'bg-slate-800'}`} />}
                </div>
              </Tooltip>
            );
          })}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-8">
          <SectionLabel>Project Health Snapshot</SectionLabel>
          <div className="kpi-bento">
            <KPICard featured label="Total Source Files" value={derived.totalFiles} icon={FileText} status="Healthy" description="Files stored for the active run." />
            <KPICard label="Complex Modules" value={derived.complexModules} icon={AlertCircle} status={derived.complexModules > 0 ? 'Review' : 'Healthy'} description="High-complexity files from backend complexity scoring." />
            <KPICard label="Analysis Chunks" value={derived.analysisChunks} icon={Layers} status={derived.analysisChunks > 0 ? 'Healthy' : 'Review'} description="Chunk count reported by complexity analysis." />
            <KPICard label="Verified Rules" value={`${derived.verifiedRules}/${metrics.rules.length}`} icon={CheckCircle2} status={derived.pendingRules > 0 ? 'Review' : 'Healthy'} description="Human verification state from stored business rules." />
            <KPICard label="Critical Paths" value={derived.criticalPaths} icon={GitBranch} status={derived.criticalPaths > 0 ? 'Action' : 'Healthy'} description="CALLS, EXECUTES, and MAPS_TO dependency relations." />
          </div>
        </div>
        <div className="lg:col-span-4">
          <SectionLabel>AI Recommendations</SectionLabel>
          <div className="glass-card flex h-full flex-col gap-5 border border-indigo-500/30 bg-indigo-500/5 p-6">
            <div className="flex items-center gap-3 text-indigo-400">
              <Lightbulb size={20} />
              <h3 className="text-heading">Recommended Next Move</h3>
            </div>
            <p className="text-body text-slate-300">{recommendation}</p>
            <div className="mt-auto grid grid-cols-1 gap-3">
              <button onClick={() => navigate(derived.totalFiles === 0 ? '/initial-setup' : '/business-logic')} className="btn-glow w-full">
                {derived.totalFiles === 0 ? 'Open Initial Setup' : 'Review Business Logic'} <ChevronRight size={14} />
              </button>
              <button onClick={() => navigate('/discovery')} className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-xs font-black text-white transition-all hover:bg-slate-700">
                Open System Discovery
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div>
          <SectionLabel>Modernization Blueprint</SectionLabel>
          <h2 className="text-page-title">Execution roadmap</h2>
          <p className="text-body-sm mt-2 max-w-2xl">Pipeline state calculated from project, discovery, complexity, and business-rule backend data.</p>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          {blueprintStages.map((stage, i) => {
            const progressValue = stageProgress(stage);
            const isActive = stage.status === 'In Progress';
            return (
              <div key={stage.id} className={`glass-card flex min-h-[230px] flex-col gap-4 border p-5 ${isActive ? 'border-amber-500/50 bg-amber-500/5 shadow-lg shadow-amber-500/10' : 'border-slate-800 bg-slate-900/50'}`}>
                <div className="flex items-start justify-between gap-3">
                  <span className="label">Stage {String(i + 1).padStart(2, '0')}</span>
                  <StatusBadge status={stage.status} />
                </div>
                <div>
                  <h3 className="text-card-title">{stage.name}</h3>
                  <p className="text-body-sm mt-2">{stage.desc}</p>
                </div>
                <div className="space-y-2">
                  {stage.activities.slice(0, 3).map((act, index) => {
                    const label = typeof act === 'object' ? act.name : act;
                    const value = typeof act === 'object' ? `${act.progress}%` : '';
                    return (
                      <div key={`${label}-${index}`} className="flex items-center justify-between gap-3 text-[11px] font-bold text-slate-400">
                        <span className="truncate">{label}</span>
                        {value && <span className="font-mono text-slate-500">{value}</span>}
                      </div>
                    );
                  })}
                </div>
                <div className="pipeline-card-progress"><span style={{ width: `${progressValue}%` }} /></div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="space-y-6">
        <SectionLabel>Backend Data Used</SectionLabel>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="glass-card space-y-3 border border-slate-800 bg-slate-900/50 p-6">
            <div className="flex items-center gap-2 text-xs font-black uppercase text-slate-500"><Database size={14} /> Project</div>
            <p className="text-body-sm">{activeProject ? `${activeProject.name} - ${activeProject.status}` : 'No active project selected.'}</p>
          </div>
          <div className="glass-card space-y-3 border border-slate-800 bg-slate-900/50 p-6">
            <div className="flex items-center gap-2 text-xs font-black uppercase text-slate-500"><GitBranch size={14} /> Discovery</div>
            <p className="text-body-sm">{metrics.relations.length} relations, {derived.sharedAssets} shared data/copybook links.</p>
          </div>
          <div className="glass-card space-y-3 border border-slate-800 bg-slate-900/50 p-6">
            <div className="flex items-center gap-2 text-xs font-black uppercase text-slate-500"><ShieldCheck size={14} /> Knowledge Gate</div>
            <p className="text-body-sm">{metrics.rules.length} rules stored, {derived.pendingRules} pending verification.</p>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;