import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FileText, Activity, Layers, Database, GitBranch, Play, ChevronRight, PlusCircle,
  BrainCircuit, Rocket, ShieldCheck, Lightbulb, CheckCircle2, Loader2, Clock, Zap,
  Languages, Target, Code2, AlertCircle, ChevronDown, Trash2, Workflow, ServerCog,
  Braces, Network, ArrowRight, Sparkles
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
  { id: 1, name: 'Environment Setup', status: 'Complete', desc: 'AI provider, token budget, and run configuration are prepared.', activities: ['AI Model Config', 'Token Budget', 'Source Lang Config'] },
  { id: 2, name: 'Discovery & Analysis', status: 'Complete', desc: 'Legacy structure, dependencies, and complexity are mapped.', activities: ['Adaptive Chunking', 'Dependency Mapping', 'Complexity Analysis'] },
  { id: 3, name: 'Knowledge Extraction', status: 'In Progress', desc: 'Business meaning is extracted from procedural code paths.', activities: [{ name: 'Rule Extraction', progress: 80 }, { name: 'DDD Discovery', progress: 45 }, { name: 'HITL Validation', progress: 20 }] },
  { id: 4, name: 'Modern Code Generation', status: 'Pending', desc: 'Generate service, domain, and API artifacts.', activities: ['DTO Generation', 'Domain Models', 'Service Layer'] },
  { id: 5, name: 'Agentic Refinement', status: 'Pending', desc: 'Compile-test-fix loops harden generated outputs.', activities: ['Compile-Test-Fix', 'Unit Tests', 'Optimization'] },
];

const JOURNEY_STEPS = [
  { name: 'Upload COBOL', path: '/source-files', icon: FileText, desc: 'Ingest COBOL, JCL, copybooks, SQL, and archive folders.' },
  { name: 'Discover Graph', path: '/discovery', icon: Network, desc: 'Find CALLs, COPY statements, tables, and missing dependencies.' },
  { name: 'Extract Rules', path: '/business-logic', icon: BrainCircuit, desc: 'Translate legacy behavior into business-readable rules.' },
  { name: 'Generate APIs', path: '/code-generation', icon: Braces, desc: 'Create modernization-ready service and API outputs.' },
  { name: 'Refine', path: '/mission-control', icon: ShieldCheck, desc: 'Run validation and repair loops before export.' },
];

const TRUST_BADGES = ['COBOL', 'JCL', 'Copybooks', 'SQL', 'Business Rules', 'Dependency Graph'];

const PREVIEW_STEPS = [
  { label: 'Reading COBOL files', icon: FileText, state: 'Complete' },
  { label: 'Discovering copybooks', icon: GitBranch, state: 'Complete' },
  { label: 'Extracting business logic', icon: BrainCircuit, state: 'Running' },
  { label: 'Building dependency graph', icon: Network, state: 'Queued' },
];

const START_OPTIONS = [
  { title: 'Start from ZIP', desc: 'Upload an application archive and let ModernizerAI inventory the legacy estate.', icon: FileText, path: '/source-files' },
  { title: 'Start from Git', desc: 'Connect a local repository or GitHub source and preserve folder paths.', icon: GitBranch, path: '/source-files' },
  { title: 'Start from COBOL', desc: 'Drop individual COBOL, JCL, copybook, SQL, and text files.', icon: Code2, path: '/source-files' },
  { title: 'Start from Review', desc: 'Open business logic extraction and confirm modernization rules.', icon: Lightbulb, path: '/business-logic' },
];

const KPICard = ({ label, value, icon: Icon, status, featured = false, description }: KPICardProps) => (
  <div className={`rocket-card ${featured ? 'kpi-featured p-7' : 'p-5'} flex flex-col`}>
    <div className="flex items-start justify-between gap-4">
      <span className="rocket-label">{label}</span>
      <span className="rocket-icon"><Icon size={featured ? 24 : 18} /></span>
    </div>
    <div className={featured ? 'rocket-stat mt-8' : 'mt-5 text-3xl font-black tracking-tight text-[var(--corporate-text)]'}>{value}</div>
    <p className="rocket-muted mt-2">{description || 'Modernization signal tracked by the pipeline.'}</p>
    <div className="mt-auto pt-5"><StatusBadge status={status} /></div>
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

  const activeProject = useMemo(() => projects.find((p) => p.run_id === runId), [projects, runId]);

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
    if (searchParams.get('new') !== 'true') void fetchProjectHistory();
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
    } catch {
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
      } catch {
        toast.error('Failed to sync language to server');
      }
    }
  };

  const getNextRunName = (projectList: ProjectSummary[] = projects) => {
    const runRegex = /^Run_(\d+)$/;
    const usedNumbers = projectList
      .map((project) => project.name.match(runRegex)?.[1] || null)
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
    <div className="rocket-home pb-24">
      <section className="rocket-hero-section bg-grid">
        <div className="rocket-hero-copy">
          <div className="rocket-eyebrow"><Sparkles size={15} /> ModernizerAI for legacy modernization</div>
          <h1>Convert COBOL systems into business logic, APIs, and modern code.</h1>
          <p>
            ModernizerAI reverse-engineers COBOL, JCL, copybooks, and legacy files to discover dependencies, extract business rules, and generate modernization-ready outputs.
          </p>
          <div className="rocket-actions">
            <button onClick={handleStartNewProject} disabled={isCreatingProject} className="rocket-primary-btn">
              {isCreatingProject ? <Loader2 className="animate-spin" size={18} /> : <Rocket size={18} />}
              Start migration
            </button>
            <button onClick={() => navigate('/discovery')} className="rocket-secondary-btn">
              View demo <ArrowRight size={17} />
            </button>
          </div>
          <div className="rocket-trust-row">
            {TRUST_BADGES.map((badge) => <span key={badge}>{badge}</span>)}
          </div>
        </div>

        <motion.div
          className="rocket-preview-wrap"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55 }}
        >
          <div className="rocket-preview-card">
            <div className="rocket-preview-top">
              <span>Migration run</span>
              <StatusBadge status="Running" />
            </div>
            <div className="rocket-preview-title">Legacy discovery pipeline</div>
            <div className="rocket-preview-list">
              {PREVIEW_STEPS.map((step, index) => (
                <motion.div
                  key={step.label}
                  className="rocket-preview-step"
                  animate={{ y: [0, -3, 0] }}
                  transition={{ duration: 2.4, repeat: Infinity, delay: index * 0.18 }}
                >
                  <span className="rocket-preview-icon"><step.icon size={16} /></span>
                  <span>{step.label}</span>
                  <small>{step.state}</small>
                </motion.div>
              ))}
            </div>
            <div className="rocket-preview-footer">
              <div><strong>{activeProject?.files_count || 0}</strong><span>files loaded</span></div>
              <div><strong>{progress}%</strong><span>validated</span></div>
              <div><strong>{aiConfig.model}</strong><span>model</span></div>
            </div>
          </div>
        </motion.div>
      </section>

      <section className="rocket-logo-strip" aria-label="Supported legacy inputs">
        {['COBOL', 'JCL', 'COPYBOOK', 'VSAM', 'SQL', 'CICS', 'TELON', 'PL/I'].map((item) => <span key={item}>{item}</span>)}
      </section>

      <section className="rocket-split-section">
        <div className="rocket-start-list">
          {START_OPTIONS.map((item) => (
            <button key={item.title} onClick={() => navigate(item.path)} className="rocket-start-item">
              <span className="rocket-start-icon"><item.icon size={20} /></span>
              <span><strong>{item.title}</strong><small>{item.desc}</small></span>
            </button>
          ))}
        </div>
        <div className="rocket-grid-message bg-grid">
          <h2>Not every migration starts with a clean inventory.</h2>
          <p>ModernizerAI turns what you already have into a dependency map, rule catalog, and production-ready modernization plan.</p>
        </div>
      </section>

      <section className="rocket-control-panel" id="workspace">
        <div className="rocket-panel-header">
          <div>
            <SectionLabel>Workspace</SectionLabel>
            <h2>Project setup and run control</h2>
          </div>
          <div className="rocket-project-actions">
            <button onClick={() => navigate('/projects')} className="rocket-secondary-btn">Open projects</button>
            <button onClick={handleDeleteAllRuns} disabled={isDeletingRuns || projects.length === 0} className="rocket-danger-btn">
              {isDeletingRuns ? <Loader2 className="animate-spin" size={16} /> : <Trash2 size={16} />}
              Delete runs
            </button>
          </div>
        </div>

        <div className="rocket-workspace-grid">
          <div className="rocket-card p-6">
            <div className="flex items-center gap-3 mb-5">
              <Database size={20} className="text-[var(--corporate-accent)]" />
              <div>
                <h3 className="text-heading">Active project</h3>
                <p className="rocket-muted">Resume an existing run or create a new migration.</p>
              </div>
            </div>
            <select value={runId || ''} onChange={(e) => handleProjectChange(e.target.value)} className="rocket-input">
              <option value="" disabled>Select a Project</option>
              {projects.map((proj) => <option key={proj.run_id} value={proj.run_id}>{proj.name || proj.run_id} ({proj.status})</option>)}
            </select>
            <div className="mt-5 flex items-center justify-between gap-4">
              {activeProject ? <StatusBadge status={activeProject.status} /> : <span className="rocket-muted">No active run</span>}
              <div className="flex min-w-[160px] items-center gap-3">
                <span className="font-black text-[var(--corporate-text)]">{progress}%</span>
                <div className="rocket-progress"><span style={{ width: `${progress}%` }} /></div>
              </div>
            </div>
            <button onClick={handleStartNewProject} disabled={isCreatingProject} className="rocket-primary-btn mt-6 w-full">
              {isCreatingProject ? <Loader2 className="animate-spin" size={18} /> : <PlusCircle size={18} />}
              Start new project
            </button>
          </div>

          <div className="rocket-card p-6">
            <div className="flex items-center gap-3 mb-5">
              <Languages size={20} className="text-[var(--corporate-accent)]" />
              <div>
                <h3 className="text-heading">Regional language</h3>
                <p className="rocket-muted">Sets prompts, comments, and review language.</p>
              </div>
            </div>
            <select value={sourceMetaLang} onChange={(e) => saveLang(e.target.value)} className="rocket-input">
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="jp">Japanese</option>
              <option value="de">German</option>
              <option value="fr">French</option>
              <option value="es">Spanish</option>
            </select>
          </div>

          <div className="rocket-card p-6 lg:col-span-2">
            <div className="flex items-center gap-3 mb-5">
              <ServerCog size={20} className="text-[var(--corporate-accent)]" />
              <div>
                <h3 className="text-heading">AI configuration</h3>
                <p className="rocket-muted">Shared model settings for dashboard and sidebar configuration.</p>
              </div>
            </div>
            <ConfigPanel runId={runId} onSave={(saved) => applySavedAIConfig(JSON.stringify(saved))} />
          </div>
        </div>
      </section>

      <section className="rocket-scroll-section">
        <div className="rocket-panel-header">
          <div>
            <SectionLabel>Modernization Flow</SectionLabel>
            <h2>From legacy files to generated output</h2>
          </div>
          <p>Scroll horizontally to move through the core modernization stages.</p>
        </div>
        <div className="rocket-horizontal-scroll">
          {JOURNEY_STEPS.map((step, index) => (
            <Tooltip key={step.name} text={step.desc} position="top">
              <button onClick={() => navigate(step.path)} className="rocket-flow-card">
                <span className="rocket-flow-index">{String(index + 1).padStart(2, '0')}</span>
                <span className="rocket-flow-icon"><step.icon size={23} /></span>
                <strong>{step.name}</strong>
                <small>{step.desc}</small>
              </button>
            </Tooltip>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-8 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-8">
          <SectionLabel>Project Health Snapshot</SectionLabel>
          <div className="kpi-bento">
            <KPICard featured label="Total legacy files" value={activeProject?.files_count || 0} icon={FileText} status="Healthy" description="Files loaded into the active modernization pipeline." />
            <KPICard label="Complex modules" value="14" icon={AlertCircle} status="Review" />
            <KPICard label="Pending chunks" value="35" icon={Layers} status="Review" />
            <KPICard label="Verified rules" value="16" icon={CheckCircle2} status="Healthy" />
            <KPICard label="Critical paths" value="8" icon={Workflow} status="Action" />
          </div>
        </div>
        <div className="lg:col-span-4">
          <SectionLabel>AI Recommendations</SectionLabel>
          <div className="rocket-card flex h-full flex-col gap-5 p-6">
            <div className="flex items-center gap-3 text-[var(--corporate-accent)]">
              <Lightbulb size={20} />
              <h3 className="text-heading">Recommended next move</h3>
            </div>
            <p className="rocket-body">Extract business rules before migration because <strong>14 complex modules</strong> remain undocumented.</p>
            <div className="mt-auto grid grid-cols-1 gap-3">
              <button onClick={() => navigate('/business-logic')} className="rocket-primary-btn w-full">Start rule extraction <ChevronRight size={14} /></button>
              <button onClick={() => navigate('/mission-control')} className="rocket-secondary-btn w-full">Resume processing</button>
            </div>
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div>
          <SectionLabel>Modernization Blueprint</SectionLabel>
          <h2 className="rocket-section-title">Execution roadmap</h2>
          <p className="rocket-muted mt-2 max-w-2xl">Real-time pipeline state from environment setup through production hardening.</p>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
          {BLUEPRINT_STAGES.map((stage, i) => {
            const progressValue = stageProgress(stage);
            const isActive = stage.status === 'In Progress';
            return (
              <div key={stage.id} className={`rocket-card flex min-h-[230px] flex-col gap-4 p-5 ${isActive ? 'rocket-card-active' : ''}`}>
                <div className="flex items-start justify-between gap-3">
                  <span className="rocket-label">Stage {String(i + 1).padStart(2, '0')}</span>
                  <StatusBadge status={stage.status} />
                </div>
                <div>
                  <h3 className="text-card-title">{stage.name}</h3>
                  <p className="rocket-muted mt-2">{stage.desc}</p>
                </div>
                <div className="space-y-2">
                  {stage.activities.slice(0, 3).map((act, index) => {
                    const label = typeof act === 'object' ? act.name : act;
                    const value = typeof act === 'object' ? `${act.progress}%` : 'Done';
                    return <div key={`${label}-${index}`} className="flex items-center justify-between gap-3 text-[11px] font-bold text-[var(--corporate-muted)]"><span className="truncate">{label}</span><span className="font-mono">{value}</span></div>;
                  })}
                </div>
                <div className="rocket-progress mt-auto"><span style={{ width: `${progressValue}%` }} /></div>
              </div>
            );
          })}
        </div>
      </section>

      <div className="sticky bottom-6 z-40 mx-auto flex w-fit justify-center">
        <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} onClick={() => navigate('/mission-control')} className="rocket-primary-btn rounded-full px-10 py-4 shadow-2xl">
          <Play size={20} fill="currentColor" /> Launch Migration Pipeline
        </motion.button>
      </div>
    </div>
  );
};

export default Dashboard;
