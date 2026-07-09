import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FileText, Activity, Layers, Database,
  GitBranch, Play, ChevronRight, PlusCircle,
  BrainCircuit, Rocket, ShieldCheck, Info, Lightbulb,
  CheckCircle2, Loader2, Clock, Zap,
  Languages, Settings,
  Target, Code2, AlertCircle, ChevronDown, Trash2
} from 'lucide-react';
import toast from 'react-hot-toast';
import ConfigPanel from '../components/ConfigPanel';
import { ProjectAPI } from '../services/api';
import type { ProjectSummary } from '../services/api';
import Tooltip from '../components/Tooltip';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';

type BlueprintActivity = string | { name: string; progress: number };

interface BlueprintStage {
  id: number;
  name: string;
  status: 'Complete' | 'In Progress' | 'Pending';
  indicator: 'green' | 'amber' | 'gray';
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

const BLUEPRINT_STAGES: BlueprintStage[] = [
  { id: 1, name: 'Environment Setup', status: 'Complete', indicator: 'green', desc: 'Prerequisites validated.', activities: ['AI Model Config', 'Token Budget', 'Source Lang Config'] },
  { id: 2, name: 'Discovery & Analysis', status: 'Complete', indicator: 'green', desc: 'Structure analyzed.', activities: ['Adaptive Chunking', 'Dependency Mapping', 'Complexity Analysis'] },
  { id: 3, name: 'Knowledge Extraction', status: 'In Progress', indicator: 'amber', desc: 'Business understanding construction.', activities: [{ name: 'Rule Extraction', progress: 80 }, { name: 'DDD Discovery', progress: 45 }, { name: 'HITL Validation', progress: 20 }] },
  { id: 4, name: 'Modern Code Generation', status: 'Pending', indicator: 'gray', desc: 'Components generation.', activities: ['DTO Generation', 'Domain Models', 'Service Layer'] },
  { id: 5, name: 'Agentic Refinement', status: 'Pending', indicator: 'gray', desc: 'Production hardening.', activities: ['Compile-Test-Fix', 'Unit Tests', 'Optimization'] },
];

const JOURNEY_STEPS = [
  { name: 'Select Project', path: '/projects', icon: Database, desc: 'Create a new migration run or resume a previous project.' },
  { name: 'Upload Source', path: '/source-files', icon: FileText, desc: 'Ingest ZIP archives or GitHub repos and perform language detection.' },
  { name: 'Discovery', path: '/discovery', icon: BrainCircuit, desc: 'Scan for CALLs, COPY-books, and SQL tables to build the dependency graph.' },
  { name: 'Knowledge Extraction', path: '/business-logic', icon: Layers, desc: 'Convert technical COBOL logic into human-readable business rules.' },
  { name: 'Plan Migration', path: '/dashboard', icon: Target, desc: 'Define target architecture and map legacy paragraphs to modern methods.' },
  { name: 'Generate Code', path: '/code-generation', icon: Code2, desc: 'Run the AI Factory to generate production-ready Java/C# code.' },
  { name: 'Refinement', path: '/mission-control', icon: ShieldCheck, desc: 'Run compile-test-fix loops to ensure syntactical health.' },
  { name: 'Deploy', path: '/code-generation', icon: Rocket, desc: 'Export the final codebase and generate the modernization audit report.' },
];

const KPICard = ({ label, value, icon: Icon, status, featured = false, description }: KPICardProps) => (
  <div className={`glass-card ${featured ? 'kpi-featured p-7' : 'p-5'} flex flex-col border border-slate-800 bg-slate-900/50`}>
    <div className="flex items-start justify-between gap-4">
      <span className="label">{label}</span>
      <span className="rounded-lg border border-slate-800 bg-slate-950/50 p-2 text-[var(--corporate-accent)]">
        <Icon size={featured ? 24 : 18} />
      </span>
    </div>
    <div className={featured ? 'text-display mt-8' : 'mt-5 text-3xl font-black tracking-tight text-[var(--corporate-text)]'}>{value}</div>
    <p className="text-body-sm mt-2">{description || 'Modernization signal tracked by the pipeline.'}</p>
    <div className="mt-auto pt-5">
      <StatusBadge status={status} />
    </div>
  </div>
);

const stageProgress = (stage: BlueprintStage) => {
  if (stage.status === 'Complete') return 100;
  if (stage.status === 'In Progress') return 56;
  return 0;
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [runId, setRunId] = useState<string | null>(localStorage.getItem('active_run_id'));
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isDeletingRuns, setIsDeletingRuns] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [hasTriggeredNewProject, setHasTriggeredNewProject] = useState(false);
  const [sourceMetaLang, setSourceMetaLang] = useState('en');
  const [aiMode, setAiMode] = useState<'api' | 'local'>('api');
  const [aiConfig, setAiConfig] = useState({ key: '', url: 'http://localhost:11434', model: 'gpt-4o' });

  const activeProject = useMemo(() =>
    projects.find((p) => p.run_id === runId),
    [projects, runId]
  );

  const applySavedAIConfig = (savedAiConfig = localStorage.getItem('ai_config')) => {
    if (!savedAiConfig) {
      setAiMode('api');
      setAiConfig({ key: '', url: 'http://localhost:11434', model: 'gpt-4o' });
      return;
    }
    try {
      const parsed = typeof savedAiConfig === 'string' ? JSON.parse(savedAiConfig) : savedAiConfig;
      setAiMode(parsed.mode || 'api');
      setAiConfig({ key: parsed.key || '', url: parsed.url || 'http://localhost:11434', model: parsed.model || 'gpt-4o' });
    } catch (e) { console.error('Config parse error', e); }
  };

  useEffect(() => {
    if (searchParams.get('new') !== 'true') {
      void fetchProjectHistory();
    }
    const savedLang = localStorage.getItem('modernizer_source_lang');
    if (savedLang) setSourceMetaLang(savedLang);
    applySavedAIConfig();

    const handleAIConfigUpdate = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (detail) applySavedAIConfig(JSON.stringify(detail));
      else applySavedAIConfig();
    };

    window.addEventListener('ai-config-updated', handleAIConfigUpdate);
    return () => window.removeEventListener('ai-config-updated', handleAIConfigUpdate);
  }, []);

  useEffect(() => {
    if (searchParams.get('new') === 'true' && !hasTriggeredNewProject) {
      setHasTriggeredNewProject(true);
      void handleStartNewProject();
    }
  }, [searchParams, hasTriggeredNewProject]);

  const fetchProjectHistory = async () => {
    try {
      const data = await ProjectAPI.list();
      setProjects(data);
      return data;
    } catch (e) {
      toast.error('Failed to load project history');
      return [] as ProjectSummary[];
    }
  };

  const handleProjectChange = (id: string) => {
    const project = projects.find((item) => item.run_id === id);
    setRunId(id);
    localStorage.setItem('active_run_id', id);
    toast.success(`Switched to ${project?.name || id}`);
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

  const saveLang = async (lang: string) => {
    setSourceMetaLang(lang);
    localStorage.setItem('modernizer_source_lang', lang);
    if (runId) {
      try {
        await ProjectAPI.updateConfig(runId, { lang });
        toast.success('Language updated in project');
      } catch (e) {
        toast.error('Failed to sync language to server');
      }
    }
  };

  const getNextRunName = (projectList: ProjectSummary[] = projects) => {
    const runRegex = /^Run_(\d+)$/;
    const usedNumbers = projectList
      .map((project) => {
        const match = project.name.match(runRegex);
        return match ? match[1] : null;
      })
      .filter((val): val is string => val !== null)
      .map(Number);

    const nextNumber = usedNumbers.length > 0 ? Math.max(...usedNumbers) + 1 : projectList.length + 1;
    return `Run_${nextNumber}`;
  };

  const handleStartNewProject = async () => {
    if (isCreatingProject) return;

    const runName = getNextRunName();
    const config = {
      project_name: runName,
      provider: aiMode,
      model: aiConfig.model,
      lang: sourceMetaLang,
      speed_profile: 'Balanced' as const,
      workers: 4
    };

    setIsCreatingProject(true);
    try {
      const response = await ProjectAPI.create(config);
      const newRunId = response.run_id;

      if (!newRunId) throw new Error('Backend did not return a run_id');

      localStorage.setItem('active_run_id', newRunId);
      setRunId(newRunId);
      setProjects((current) => [{
        run_id: newRunId,
        name: response.name || runName,
        status: 'CONFIGURING',
        files_count: 0,
        llm_provider: aiMode,
        llm_model: aiConfig.model,
        interaction_lang: sourceMetaLang,
        speed_profile: 'Balanced',
        parallel_workers: 4,
        file_status_counts: {},
        language_counts: {},
      }, ...current]);
      toast.success(`Project created: ${runName}`);
      navigate('/source-files');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || e.message || 'Error creating project');
    } finally {
      setIsCreatingProject(false);
    }
  };

  const calculateOverallProgress = () => {
    if (!activeProject) return 0;
    const counts = activeProject.file_status_counts || {};
    const total = activeProject.files_count || 0;
    if (total === 0) return 0;
    const confirmed = counts.CONFIRMED || 0;
    return Math.round((confirmed / total) * 100);
  };

  const progress = calculateOverallProgress();

  return (
    <div className="space-y-12 pb-24 animate-in fade-in duration-700">
      <section className="premium-hero relative overflow-hidden rounded-3xl p-8 lg:p-10 shadow-2xl">
        <div className="premium-hero-watermark">Modernize</div>
        <div className="relative z-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_240px] lg:items-center">
          <div>
            <div className="mb-8 inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/20 px-4 py-2 text-xs font-black uppercase tracking-[0.18em] text-indigo-400">
              <Rocket size={14} /> Executive Command Center
            </div>
            <h1 className="text-hero max-w-5xl">Modernizer<span className="text-[var(--corporate-accent)]">AI</span></h1>
            <p className="text-body mt-5 max-w-2xl text-[var(--corporate-muted)]">
              A governed command center for converting legacy COBOL estates into reviewed, traceable, modern application code.
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
                      <option key={proj.run_id} value={proj.run_id}>
                        {proj.name || proj.run_id} ({proj.status})
                      </option>
                    ))}
                  </select>
                  <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
                    <ChevronDown size={14} className="text-slate-500" />
                  </div>
                </div>
                {activeProject && <StatusBadge status={activeProject.status} />}
              </div>

              <div className="space-y-2">
                <p className="label">Overall Progress</p>
                <div className="flex items-center gap-3">
                  <p className="text-2xl font-black tracking-tight text-white">{progress}%</p>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
                    <div className="h-full rounded-full bg-indigo-500 transition-all duration-700" style={{ width: `${progress}%` }} />
                  </div>
                </div>
              </div>

              <button
                onClick={handleDeleteAllRuns}
                disabled={isDeletingRuns || projects.length === 0}
                className="btn-glow disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isDeletingRuns ? <Loader2 className="animate-spin" size={16} /> : <Trash2 size={16} />}
                Delete Runs
              </button>
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <button onClick={() => navigate('/projects')} className="btn-glow min-h-[5rem] text-center">
              Continue Current Project <ChevronRight size={18} />
            </button>
            <button onClick={handleStartNewProject} disabled={isCreatingProject} className="rounded-xl border border-slate-700 bg-slate-800 px-6 py-4 font-black text-white transition-all hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60">
              <span className="flex items-center justify-center gap-2">
                {isCreatingProject ? <Loader2 className="animate-spin" size={18} /> : <PlusCircle size={18} />}
                Start New Project
              </span>
            </button>
          </div>
        </div>
      </section>

      <section>
        <SectionLabel>System & AI Configuration</SectionLabel>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="glass-card space-y-5 border border-slate-800 bg-slate-900/50 p-6">
            <div className="flex items-center gap-3">
              <Languages size={20} className="text-indigo-400" />
              <div>
                <h3 className="text-heading">Regional Language</h3>
                <p className="text-body-sm">Sets the language for prompts and source comments.</p>
              </div>
            </div>
            <select
              value={sourceMetaLang}
              onChange={(e) => saveLang(e.target.value)}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="jp">Japanese</option>
              <option value="de">German</option>
              <option value="fr">French</option>
              <option value="es">Spanish</option>
            </select>
          </div>
          <div className="glass-card border border-slate-800 bg-slate-900/50 p-6 lg:col-span-2">
            <ConfigPanel runId={runId} onSave={(saved) => applySavedAIConfig(JSON.stringify(saved))} />
          </div>
        </div>
      </section>

      <section>
        <SectionLabel>Modernization Journey</SectionLabel>
        <div className="timeline-scroll flex items-start overflow-x-auto pb-3">
          {JOURNEY_STEPS.map((step, i) => {
            const isDone = i < 3;
            const isActive = i === 3;
            return (
              <Tooltip key={step.name} text={step.desc} position="top">
                <div className="flex min-w-[148px] items-start">
                  <button
                    type="button"
                    onClick={() => navigate(step.path)}
                    className="group flex w-[128px] flex-col items-center text-center"
                  >
                    <span className={`mb-3 flex h-11 w-11 items-center justify-center rounded-full border transition-all group-hover:scale-110 ${isDone || isActive ? 'border-indigo-500/40 bg-indigo-500/20 text-indigo-400 shadow-lg shadow-indigo-500/20' : 'border-slate-800 bg-slate-900/50 text-slate-500'}`}>
                      <step.icon size={18} />
                    </span>
                    <span className="label mb-1">{String(i + 1).padStart(2, '0')}</span>
                    <span className={`text-xs font-extrabold ${isDone || isActive ? 'text-white' : 'text-slate-500'}`}>{step.name}</span>
                  </button>
                  {i < JOURNEY_STEPS.length - 1 && (
                    <span className={`mt-[22px] h-0.5 min-w-[34px] flex-1 ${i < 2 ? 'bg-indigo-500' : 'bg-slate-800'}`} />
                  )}
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
            <KPICard featured label="Total COBOL Files" value={activeProject?.files_count || 0} icon={FileText} status="Healthy" description="Files loaded into the active modernization pipeline." />
            <KPICard label="Complex Modules" value="14" icon={AlertCircle} status="Review" />
            <KPICard label="Pending Chunks" value="35" icon={Layers} status="Review" />
            <KPICard label="Verified Rules" value="16" icon={CheckCircle2} status="Healthy" />
            <KPICard label="Critical Paths" value="8" icon={GitBranch} status="Action" />
          </div>
        </div>
        <div className="lg:col-span-4">
          <SectionLabel>AI Recommendations</SectionLabel>
          <div className="glass-card flex h-full flex-col gap-5 border border-indigo-500/30 bg-indigo-500/5 p-6">
            <div className="flex items-center gap-3 text-indigo-400">
              <Lightbulb size={20} />
              <h3 className="text-heading">Recommended Next Move</h3>
            </div>
            <p className="text-body text-slate-300">
              Extract business rules before migration because <span className="font-bold text-amber-400">14 complex modules</span> remain undocumented.
            </p>
            <div className="mt-auto grid grid-cols-1 gap-3">
              <button onClick={() => navigate('/business-logic')} className="btn-glow w-full">
                Start Rule Extraction <ChevronRight size={14} />
              </button>
              <button onClick={() => navigate('/mission-control')} className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-xs font-black text-white transition-all hover:bg-slate-700">
                Resume Processing
              </button>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div>
          <SectionLabel>Modernization Blueprint</SectionLabel>
          <h2 className="text-page-title">Execution roadmap</h2>
          <p className="text-body-sm mt-2 max-w-2xl">Real-time pipeline state from environment setup through production hardening.</p>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          {BLUEPRINT_STAGES.map((stage, i) => {
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
                    const value = typeof act === 'object' ? `${act.progress}%` : 'Done';
                    return (
                      <div key={`${label}-${index}`} className="flex items-center justify-between gap-3 text-[11px] font-bold text-slate-400">
                        <span className="truncate">{label}</span>
                        <span className="font-mono text-slate-500">{value}</span>
                      </div>
                    );
                  })}
                </div>
                <div className="pipeline-card-progress">
                  <span style={{ width: `${progressValue}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="space-y-6">
        <SectionLabel>What's Next</SectionLabel>
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          <div className="glass-card space-y-4 border border-indigo-500/30 bg-indigo-500/5 p-6">
            <div className="flex items-center gap-2 text-xs font-black uppercase text-indigo-400"><Zap size={14} /> Immediate Action</div>
            <h4 className="text-card-title">Review HITL Validations</h4>
            <p className="text-body-sm">Approving remaining validations will unlock code generation.</p>
            <button onClick={() => navigate('/business-logic')} className="btn-glow w-full">Review HITL</button>
          </div>
          <div className="glass-card space-y-4 border border-slate-800 bg-slate-900/50 p-6">
            <div className="flex items-center gap-2 text-xs font-black uppercase text-slate-500"><Clock size={14} /> Upcoming</div>
            <h4 className="text-card-title">Generate Java Domain Models</h4>
            <p className="text-body-sm">Transform extracted DDD entities into Spring Boot artifacts.</p>
            <button onClick={() => navigate('/code-generation')} className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-xs font-black text-white transition-all hover:bg-slate-700 w-full">Prepare Generation</button>
          </div>
          <div className="glass-card space-y-4 border border-slate-800 bg-slate-900/50 p-6">
            <div className="flex items-center gap-2 text-xs font-black uppercase text-slate-500"><ShieldCheck size={14} /> Final Stage</div>
            <h4 className="text-card-title">Run Agentic Refinement</h4>
            <p className="text-body-sm">Perform automated compile-test-fix loops for production readiness.</p>
            <button onClick={() => navigate('/mission-control')} className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-xs font-black text-white transition-all hover:bg-slate-700 w-full">Start Refinement</button>
          </div>
        </div>
      </section>

      <div className="fixed bottom-8 left-1/2 z-50 -translate-x-1/2">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/mission-control')}
          className="btn-glow rounded-full px-10 py-4 font-black shadow-2xl"
        >
          <Play size={20} fill="currentColor" /> Launch Migration Pipeline
        </motion.button>
      </div>
    </div>
  );
};

export default Dashboard;


