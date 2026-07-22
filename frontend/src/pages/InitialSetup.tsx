import React, { useState, useEffect } from 'react';
import { PlusCircle, Trash2, ChevronDown, Loader2, Languages } from 'lucide-react';
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

const loadLastAIConfig = (): ProjectConfig => {
  try {
    const saved = JSON.parse(localStorage.getItem('ai_config') || '{}');
    delete saved.key;
    return { ...defaultAIConfig, ...saved };
  } catch {
    return defaultAIConfig;
  }
};

const InitialSetup = () => {
  const [runId, setRunId] = useState<string | null>(localStorage.getItem('active_run_id'));
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [isDeletingRuns, setIsDeletingRuns] = useState(false);
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [sourceMetaLang, setSourceMetaLang] = useState('en');

  useEffect(() => {
    void fetchProjectHistory();
    const savedLang = localStorage.getItem('modernizer_source_lang');
    if (savedLang) setSourceMetaLang(savedLang);
  }, []);

  const fetchProjectHistory = async () => {
    try {
      const data = await ProjectAPI.list();
      setProjects(data);
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
    const aiConfig = loadLastAIConfig();

    try {
      const response = await ProjectAPI.create({
        project_name: runName,
        ...aiConfig,
        lang: sourceMetaLang,
        speed_profile: 'Balanced',
        workers: 4,
      });
      const newRunId = response.run_id;
      localStorage.setItem('active_run_id', newRunId);
      localStorage.setItem(`ai_config_${newRunId}`, JSON.stringify({ ...aiConfig, key: '' }));
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
        </div>

        <div className="lg:col-span-7 space-y-6">
          <SectionLabel>AI Engine Configuration</SectionLabel>
          <div className="glass-card p-6 border border-slate-800 bg-slate-900/50">
            <ConfigPanel runId={runId} />
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
