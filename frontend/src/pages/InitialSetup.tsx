import React, { useState, useEffect } from 'react';
import { PlusCircle, Trash2, ChevronDown, Loader2, Languages, Database, KeyRound, Link as LinkIcon, UserRound } from 'lucide-react';
import toast from 'react-hot-toast';
import ConfigPanel from '../components/ConfigPanel';
import SourceFiles from './SourceFiles';
import { ProjectAPI } from '../services/api';
import type { ProjectConfig, ProjectSummary } from '../services/api';
import SectionLabel from '../components/SectionLabel';

const defaultAIConfig: ProjectConfig = {
  mode: 'openrouter',
  provider: 'openrouter',
  key: '',
  url: 'https://openrouter.ai/api/v1',
  model: 'openai/gpt-oss-20b:free',
};

const defaultNeo4jConfig: ProjectConfig = {
  neo4j_uri: '',
  neo4j_user: 'neo4j',
  neo4j_password: '',
};

const loadLastAIConfig = (): ProjectConfig => {
  try {
    const saved = JSON.parse(localStorage.getItem('ai_config') || '{}');
    delete saved.key;
    delete saved.has_api_key;
    delete saved.key_preview;
    return { ...defaultAIConfig, ...saved };
  } catch {
    return defaultAIConfig;
  }
};

const loadLastNeo4jConfig = (): ProjectConfig => {
  try {
    const saved = JSON.parse(localStorage.getItem('neo4j_config') || '{}');
    delete saved.neo4j_password;
    delete saved.has_neo4j_password;
    delete saved.neo4j_password_preview;
    return { ...defaultNeo4jConfig, ...saved };
  } catch {
    return defaultNeo4jConfig;
  }
};

interface Neo4jConfigPanelProps {
  runId: string | null;
  onSave?: (config: ProjectConfig) => void;
}

const Neo4jConfigPanel = ({ runId, onSave }: Neo4jConfigPanelProps) => {
  const [config, setConfig] = useState<ProjectConfig>(defaultNeo4jConfig);
  const [savedPasswordPreview, setSavedPasswordPreview] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const loadConfig = async () => {
      if (runId) {
        try {
          const serverConfig = await ProjectAPI.getConfig(runId);
          if (cancelled) return;
          setConfig({
            neo4j_uri: serverConfig.neo4j_uri || '',
            neo4j_user: serverConfig.neo4j_user || 'neo4j',
            neo4j_password: '',
          });
          setSavedPasswordPreview(serverConfig.has_neo4j_password ? serverConfig.neo4j_password_preview || 'saved' : null);
          localStorage.setItem('neo4j_config', JSON.stringify({
            neo4j_uri: serverConfig.neo4j_uri || '',
            neo4j_user: serverConfig.neo4j_user || 'neo4j',
            has_neo4j_password: Boolean(serverConfig.has_neo4j_password),
            neo4j_password_preview: serverConfig.neo4j_password_preview || null,
          }));
          return;
        } catch (e) {
          console.error('Neo4j config load error', e);
        }
      }

      const saved = loadLastNeo4jConfig();
      setConfig(saved);
      setSavedPasswordPreview(null);
    };

    void loadConfig();
    return () => { cancelled = true; };
  }, [runId]);

  const handleSave = async () => {
    const uri = (config.neo4j_uri || '').trim();
    const user = (config.neo4j_user || '').trim() || 'neo4j';
    const password = (config.neo4j_password || '').trim();

    if (!uri) {
      toast.error('Enter your Neo4j connection URI');
      return;
    }
    if (!password && !savedPasswordPreview) {
      toast.error('Enter your Neo4j password');
      return;
    }

    const updatePayload: ProjectConfig = {
      neo4j_uri: uri,
      neo4j_user: user,
    };
    if (password) {
      updatePayload.neo4j_password = password;
    }

    setSaving(true);
    try {
      if (runId) {
        await ProjectAPI.updateConfig(runId, updatePayload);
      }

      const safeConfig = {
        neo4j_uri: uri,
        neo4j_user: user,
        has_neo4j_password: Boolean(password || savedPasswordPreview),
        neo4j_password_preview: password ? `****${password.slice(-4)}` : savedPasswordPreview,
      };
      localStorage.setItem('neo4j_config', JSON.stringify(safeConfig));
      setConfig({ neo4j_uri: uri, neo4j_user: user, neo4j_password: '' });
      setSavedPasswordPreview(safeConfig.neo4j_password_preview);
      onSave?.(updatePayload);
      toast.success('Neo4j configuration saved');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Failed to save Neo4j configuration');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="rounded-xl bg-cyan-500/15 p-3 text-cyan-300">
          <Database size={20} />
        </div>
        <div>
          <h3 className="text-sm font-bold text-white">Neo4j Graph Configuration</h3>
          <p className="text-xs text-slate-400">Used by System Discovery maps and dashboard graph health.</p>
        </div>
      </div>

      <div className="space-y-3">
        <div className="relative">
          <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" size={14} />
          <input
            type="text"
            value={config.neo4j_uri || ''}
            onChange={(event) => setConfig({ ...config, neo4j_uri: event.target.value })}
            placeholder="neo4j+s://xxxxxxxx.databases.neo4j.io"
            className="w-full rounded-xl border border-slate-800 bg-slate-950 py-3 pl-10 pr-4 text-sm text-white outline-none focus:ring-2 focus:ring-cyan-500"
          />
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="relative">
            <UserRound className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" size={14} />
            <input
              type="text"
              value={config.neo4j_user || ''}
              onChange={(event) => setConfig({ ...config, neo4j_user: event.target.value })}
              placeholder="neo4j"
              className="w-full rounded-xl border border-slate-800 bg-slate-950 py-3 pl-10 pr-4 text-sm text-white outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </div>

          <div className="relative">
            <KeyRound className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" size={14} />
            <input
              type="password"
              value={config.neo4j_password || ''}
              onChange={(event) => setConfig({ ...config, neo4j_password: event.target.value })}
              placeholder={savedPasswordPreview ? `Saved password: ${savedPasswordPreview}` : 'Neo4j password'}
              className="w-full rounded-xl border border-slate-800 bg-slate-950 py-3 pl-10 pr-4 text-sm text-white outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-600 px-4 py-3 text-xs font-black text-white transition-all hover:bg-cyan-500 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? <Loader2 className="animate-spin" size={16} /> : <Database size={16} />}
          Save Neo4j Configuration
        </button>
      </div>
    </div>
  );
};

const InitialSetup = () => {
  const [runId, setRunId] = useState<string | null>(localStorage.getItem('active_run_id'));
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isDeletingRuns, setIsDeletingRuns] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [sourceMetaLang, setSourceMetaLang] = useState('en');
  const [pendingAIConfig, setPendingAIConfig] = useState<ProjectConfig | null>(null);
  const [pendingNeo4jConfig, setPendingNeo4jConfig] = useState<ProjectConfig | null>(null);

  useEffect(() => {
    void fetchProjectHistory();
    const savedLang = localStorage.getItem('modernizer_source_lang');
    if (savedLang) setSourceMetaLang(savedLang);
  }, []);

  const fetchProjectHistory = async () => {
    try {
      const data = await ProjectAPI.list();
      setProjects(data);
      if ((!runId || !data.some((project) => project.run_id === runId)) && data[0]?.run_id) {
        setRunId(data[0].run_id);
        localStorage.setItem('active_run_id', data[0].run_id);
      }
    } catch (e) {
      toast.error('Failed to load project history');
    }
  };

  const handleProjectChange = (id: string) => {
    setRunId(id);
    localStorage.setItem('active_run_id', id);
    toast.success(`Active project switched to ${id}`);
  };

  const handleDeleteAllRuns = async () => {
    if (projects.length === 0) return;
    if (!window.confirm('Delete all runs?')) return;
    setIsDeletingRuns(true);
    try {
      await ProjectAPI.deleteAllRuns();
      setProjects([]);
      setRunId(null);
      localStorage.removeItem('active_run_id');
      toast.success('All runs deleted');
    } catch (e) {
      toast.error('Failed to delete runs');
    } finally {
      setIsDeletingRuns(false);
    }
  };

  const handleStartNewProject = async () => {
    if (isCreatingProject) return;
    setIsCreatingProject(true);

    const runName = `Run_${projects.length + 1}`;
    const aiConfig = { ...loadLastAIConfig(), ...(pendingAIConfig || {}) };
    const neo4jConfig = { ...loadLastNeo4jConfig(), ...(pendingNeo4jConfig || {}) };

    try {
      const response = await ProjectAPI.create({
        project_name: runName,
        ...aiConfig,
        ...neo4jConfig,
        lang: sourceMetaLang,
        speed_profile: 'Balanced',
        workers: 4,
      });
      const newRunId = response.run_id;
      localStorage.setItem('active_run_id', newRunId);
      localStorage.setItem(`ai_config_${newRunId}`, JSON.stringify({ ...aiConfig, key: '' }));
      localStorage.setItem('neo4j_config', JSON.stringify({ ...neo4jConfig, neo4j_password: '' }));
      setRunId(newRunId);
      setProjects([{ run_id: newRunId, name: response.name, status: response.status, files_count: 0 }, ...projects]);
      toast.success(`Project ${runName} created. Upload source files below.`);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error creating project');
    } finally {
      setIsCreatingProject(false);
    }
  };

  const saveLang = async (lang: string) => {
    setSourceMetaLang(lang);
    localStorage.setItem('modernizer_source_lang', lang);
    if (runId) {
      try { await ProjectAPI.updateConfig(runId, { lang }); } catch (e) {}
    }
  };

  return (
    <div className="space-y-12 pb-32 animate-in fade-in duration-700">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-extrabold text-white tracking-tight">Initial Setup</h1>
        <p className="text-slate-400">Configure your AI engine, project environment, and regional settings.</p>
      </header>

      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 space-y-6">
          <SectionLabel>Project Control</SectionLabel>
          <div className="glass-card p-6 border border-slate-800 bg-slate-900/50 space-y-6">
            <div className="space-y-3">
              <p className="label">Active Project</p>
              <div className="relative">
                <select
                  value={runId || ''}
                  onChange={(e) => handleProjectChange(e.target.value)}
                  className="w-full appearance-none rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 pr-10 text-sm font-bold text-white outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="" disabled>Select a Project</option>
                  {projects.map((proj) => (
                    <option key={proj.run_id} value={proj.run_id}>{proj.name} ({proj.status})</option>
                  ))}
                </select>
                <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
                  <ChevronDown size={14} className="text-slate-500" />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button onClick={handleStartNewProject} disabled={isCreatingProject} className="btn-glow flex items-center justify-center gap-2 py-3">
                {isCreatingProject ? <Loader2 className="animate-spin" size={16} /> : <PlusCircle size={16} />}
                New Project
              </button>
              <button onClick={handleDeleteAllRuns} disabled={isDeletingRuns} className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-xs font-black text-white hover:bg-red-900/20 hover:border-red-500/50 transition-all">
                <Trash2 size={16} className="inline mr-2" /> Delete All
              </button>
            </div>
          </div>

          <SectionLabel>Graph Database</SectionLabel>
          <div className="glass-card p-6 border border-slate-800 bg-slate-900/50">
            <Neo4jConfigPanel runId={runId} onSave={(config) => setPendingNeo4jConfig(config)} />
          </div>
        </div>

        <div className="lg:col-span-7 space-y-6">
          <SectionLabel>AI Engine Configuration</SectionLabel>
          <div className="glass-card p-6 border border-slate-800 bg-slate-900/50">
            <ConfigPanel runId={runId} onSave={(config) => setPendingAIConfig(config)} />
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <SectionLabel>Regional Settings</SectionLabel>
        <div className="glass-card p-6 border border-slate-800 bg-slate-900/50 max-w-md">  
          <div className="flex items-center gap-3 mb-4">
            <Languages size={20} className="text-indigo-400" />
            <h3 className="text-sm font-bold text-white">Source Code Language</h3>
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
      </section>

      <section className="space-y-6 border-t border-slate-800 pt-10">
        <div>
          <SectionLabel>Source Files</SectionLabel>
          <h2 className="text-2xl font-extrabold text-white tracking-tight">Upload and review source code</h2>
          <p className="mt-2 text-sm text-slate-400">Upload files for the active run, confirm detected languages, then launch the pipeline from the fixed action bar.</p>
        </div>
        <SourceFiles embedded />
      </section>
    </div>
  );
};

export default InitialSetup;
