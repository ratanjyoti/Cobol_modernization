import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, CheckCircle2, Clock, Calendar, ArrowRight,
  Database, AlertCircle, Play, Trash2, Download, Loader2, FileText,
  Settings, Languages
} from 'lucide-react';
import toast from 'react-hot-toast';
import { ProjectAPI } from '../services/api';
import type { FileRecord, ProjectSummary } from '../services/api';
import PageHeader from '../components/PageHeader';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';

const STATUS_CONFIG: Record<string, { label: string; color: string; text: string; border: string; animation: string }> = {
  CONFIGURING: { label: 'Configuring', color: 'bg-slate-500', text: 'text-slate-300', border: 'border-slate-500', animation: '' },
  INGESTING: { label: 'Ingesting', color: 'bg-blue-500', text: 'text-blue-300', border: 'border-blue-500', animation: '' },
  ANALYZING: { label: 'Analyzing', color: 'bg-amber-500', text: 'text-amber-300', border: 'border-amber-500', animation: 'animate-pulse' },
  CONVERTING: { label: 'Converting', color: 'bg-purple-500', text: 'text-purple-300', border: 'border-purple-500', animation: 'animate-pulse' },
  DEPLOYED: { label: 'Deployed', color: 'bg-emerald-500', text: 'text-emerald-300', border: 'border-emerald-500', animation: '' },
  FAILED: { label: 'Failed', color: 'bg-red-500', text: 'text-red-300', border: 'border-red-500', animation: '' },
};

const formatDate = (value?: string | null) => {
  if (!value) return 'Not recorded';
  return new Intl.DateTimeFormat(undefined, { year: 'numeric', month: 'short', day: '2-digit' }).format(new Date(value));
};

const getProgress = (project: ProjectSummary) => {
  const counts = project.file_status_counts || {};
  const total = project.files_count || 0;
  if (project.status === 'FAILED') return 30;
  if (project.status === 'DEPLOYED') return 100;
  if (total === 0) return 10;
  const confirmed = counts.CONFIRMED || 0;
  return Math.max(25, Math.round((confirmed / total) * 70) + 20);
};

const Projects = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProject, setSelectedProject] = useState<ProjectSummary | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<FileRecord[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | null>(localStorage.getItem('active_run_id'));
  const [loading, setLoading] = useState(true);
  const [detailsLoading, setDetailsLoading] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const data = await ProjectAPI.list();
      setProjects(data);
      
      const storedId = localStorage.getItem('active_run_id');
      const preferred = data.find((project) => project.run_id === storedId) || data[0] || null;
      
      if (preferred) {
        setActiveRunId(preferred.run_id); 
        await selectProject(preferred.run_id, data);
      } else {
        setSelectedProject(null);
        setSelectedFiles([]);
      }
    } catch {
      toast.error('Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const selectProject = async (runId: string, projectList = projects) => {
    setDetailsLoading(true);
    try {
      setActiveRunId(runId); 
      localStorage.setItem('active_run_id', runId);
      const projectFromList = projectList.find((project) => project.run_id === runId) || null;
      setSelectedProject(projectFromList);
      const [projectDetail, fileData] = await Promise.all([
        ProjectAPI.get(runId),
        ProjectAPI.listFiles(runId),
      ]);
      setSelectedProject(projectDetail);
      setSelectedFiles(fileData.files);
    } catch {
      toast.error('Failed to load project details');
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleActivate = (runId: string) => {
    localStorage.setItem('active_run_id', runId);
    setActiveRunId(runId); 
    toast.success(`Switched to ${projects.find((project) => project.run_id === runId)?.name || runId}`);
    navigate('/initial-setup');
  };

  const handleDelete = async (runId: string) => {
    if (!window.confirm('Delete this run and its uploaded files?')) return;

    try {
      await ProjectAPI.delete(runId);
      const remaining = projects.filter((project) => project.run_id !== runId);
      setProjects(remaining);
      if (activeRunId === runId) {
        localStorage.removeItem('active_run_id');
        setActiveRunId(null);
      }
      if (selectedProject?.run_id === runId) {
        const nextProject = remaining[0] || null;
        if (nextProject) await selectProject(nextProject.run_id, remaining);
        else {
          setSelectedProject(null);
          setSelectedFiles([]);
        }
      }
      toast.success('Run deleted');
    } catch {
      toast.error('Failed to delete run');
    }
  };

  const activeProject = projects.find((project) => project.run_id === activeRunId);
  const selectedConfig = selectedProject ? STATUS_CONFIG[selectedProject.status] || STATUS_CONFIG.CONFIGURING : STATUS_CONFIG.CONFIGURING;
  const selectedProgress = selectedProject ? getProgress(selectedProject) : 0;
  const fileStatusRows = useMemo(() => Object.entries(selectedProject?.file_status_counts || {}), [selectedProject]);
  const languageRows = useMemo(() => Object.entries(selectedProject?.language_counts || {}), [selectedProject]);

  if (loading) {
    return <div className="flex justify-center items-center h-screen text-white"><Loader2 className="animate-spin" /></div>;
  }

  return (
    <div className="space-y-10">
      <PageHeader
        title="Project Management Hub"
        description="Manage migration runs, backend status, active project context, and run history."
        meta={activeProject ? <StatusBadge status={activeProject.status} /> : undefined}
        action={(
          <button onClick={() => navigate('/initial-setup')} className="btn-glow">
            <Plus size={20} /> Select Project
          </button>
        )}
      />

      {activeProject && (
        <div className="glass-card p-8 rounded-3xl border-indigo-500/50 bg-indigo-500/5 border-2 relative overflow-hidden shadow-[0_0_20px_rgba(99,102,241,0.2)]">
          <div className="absolute top-0 right-0 p-4">
            <span className="px-3 py-1 rounded-full bg-indigo-500 text-white text-[10px] font-bold uppercase tracking-wider">Active Run</span>
          </div>
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
            <div className="flex items-center gap-6">
              <div className="p-4 bg-indigo-600 rounded-2xl text-white shadow-xl shadow-indigo-500/40">
                <Database size={32} />
              </div>
              <div className="space-y-1">
                <h2 className="text-2xl font-bold text-white">{activeProject.name} <span className="text-slate-500 text-sm font-mono ml-2">{activeProject.run_id}</span></h2>
                <p className="text-slate-400 text-sm">
                  {formatDate(activeProject.created_at)} - {activeProject.files_count} Source Files - {activeProject.llm_model || 'Target pending'}
                </p>
              </div>
            </div>
            <button
              onClick={() => handleActivate(activeProject.run_id)}
              className="px-6 py-3 bg-white text-indigo-900 rounded-xl font-bold hover:bg-indigo-50 transition-all flex items-center gap-2"
            >
              Open Initial Setup <ArrowRight size={18} />
            </button>
          </div>
          <div className="mt-6 w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div className="bg-indigo-500 h-full transition-all duration-500" style={{ width: `${getProgress(activeProject)}%` }} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <SectionLabel>Version History / All Runs</SectionLabel>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {projects.map((project) => {
              const config = STATUS_CONFIG[project.status] || STATUS_CONFIG.CONFIGURING;
              const isActive = project.run_id === activeRunId;
              const isSelected = project.run_id === selectedProject?.run_id;

              return (
                <button
                  key={project.run_id}
                  onClick={() => selectProject(project.run_id)}
                  className={`glass-card text-left p-6 rounded-2xl border-slate-800 transition-all group 
                    ${isActive 
                      ? 'ring-2 ring-indigo-500 border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/20' 
                      // : isSelected 
                        : 'border-slate-500 bg-slate-800/50' 
                        // : 'hover:border-slate-600'
                    }`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className="p-2 bg-slate-800 rounded-lg text-slate-400">
                      <Database size={20} />
                    </div>
                    <div className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold uppercase bg-opacity-20 ${config.text} ${config.animation}`}>
                      {project.status === 'FAILED' && <AlertCircle size={12} />}
                      {project.status === 'DEPLOYED' && <CheckCircle2 size={12} />}
                      {config.label}
                    </div>
                  </div>

                  <h4 className="text-white font-bold mb-1 truncate">{project.name}</h4>
                  <p className="text-slate-500 text-xs font-mono mb-4">{project.run_id}</p>

                  <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
                    <div className="flex items-center gap-1"><Calendar size={12} /> {formatDate(project.created_at)}</div>
                    <div className="flex items-center gap-1"><Database size={12} /> {project.files_count} files</div>
                  </div>

                  <div className="space-y-2 mb-6">
                    <div className="flex justify-between text-[10px] text-slate-400 uppercase font-bold">
                      <span>Progress</span>
                      <span>{getProgress(project)}%</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div className={`h-full ${config.color} transition-all`} style={{ width: `${getProgress(project)}%` }} />
                    </div>
                  </div>

                  <div className="flex justify-between items-center pt-4 border-t border-slate-800 gap-2">
                    <div className="flex gap-2">
                      <span
                        onClick={(event) => { event.stopPropagation(); handleActivate(project.run_id); }}
                        className="p-2 hover:bg-indigo-500/20 text-indigo-400 rounded-lg transition-colors cursor-pointer"
                        title="Resume Run"
                      >
                        <Play size={16} />
                      </span>
                      <span
                        onClick={(event) => { event.stopPropagation(); handleDelete(project.run_id); }}
                        className="p-2 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors cursor-pointer"
                        title="Delete Run"
                      >
                        <Trash2 size={16} />
                      </span>
                    </div>
                    {project.status === 'DEPLOYED' && (
                      <span className="flex items-center gap-1 text-xs font-bold text-emerald-400">
                        <Download size={14} /> Export
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
            {projects.length === 0 && (
              <div className="md:col-span-2 glass-card p-10 rounded-2xl border-slate-800 text-center text-slate-400">
                No runs yet. Create a run from the Dashboard to start tracking it here.
              </div>
            )}
          </div>
        </div>

        <div className="glass-card p-6 rounded-2xl border-slate-800 bg-slate-900/50 min-h-[420px]">
          {detailsLoading && <div className="text-slate-400 flex items-center gap-2"><Loader2 size={16} className="animate-spin" /> Loading project details...</div>}
          {!detailsLoading && selectedProject && (
            <div className="space-y-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-slate-500 text-xs uppercase font-bold tracking-widest">Selected Run</p>
                  <h3 className="text-2xl font-bold text-white mt-1">{selectedProject.name}</h3>
                  <p className="text-slate-500 text-xs font-mono mt-1">{selectedProject.run_id}</p>
                </div>
                <span className={`px-3 py-1 rounded-md text-[10px] font-bold uppercase ${selectedConfig.text} bg-slate-800`}>{selectedConfig.label}</span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs text-slate-400 uppercase font-bold">
                  <span>Run Progress</span>
                  <span>{selectedProgress}%</span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div className={`h-full ${selectedConfig.color}`} style={{ width: `${selectedProgress}%` }} />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-500 text-xs">Created</div>
                  <div className="text-white font-bold">{formatDate(selectedProject.created_at)}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-500 text-xs">Files</div>
                  <div className="text-white font-bold">{selectedProject.files_count}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-500 text-xs">Model</div>
                  <div className="text-white font-bold truncate">{selectedProject.llm_model || '-'}</div>
                </div>
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800">
                  <div className="text-slate-500 text-xs">Workers</div>
                  <div className="text-white font-bold">{selectedProject.parallel_workers || '-'}</div>
                </div>
              </div>

              <div className="space-y-3">
                <SectionLabel>File Status</SectionLabel>
                {fileStatusRows.length > 0 ? fileStatusRows.map(([status, count]) => (
                  <div key={status} className="flex justify-between text-sm border-b border-slate-800 pb-2">
                    <span className="text-slate-400">{status.replaceAll('_', ' ')}</span>
                    <span className="text-white font-bold">{count}</span>
                  </div>
                )) : <p className="text-slate-500 text-sm">No files uploaded yet.</p>}
              </div>

              <div className="space-y-3">
                <SectionLabel>Languages</SectionLabel>
                {languageRows.length > 0 ? languageRows.map(([language, count]) => (
                  <div key={language} className="flex justify-between text-sm border-b border-slate-800 pb-2">
                    <span className="text-slate-400">{language}</span>
                    <span className="text-white font-bold">{count}</span>
                  </div>
                )) : <p className="text-slate-500 text-sm">No language detection data yet.</p>}
              </div>

              <div className="space-y-3">
                <SectionLabel>Source Files</SectionLabel>
                <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                  {selectedFiles.length > 0 ? selectedFiles.map((file) => (
                    <div key={file.id} className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex justify-between gap-3 text-xs">
                      <span className="text-slate-300 truncate">{file.filepath || file.filename}</span>
                      <span className="text-indigo-300 shrink-0">{file.status}</span>
                    </div>
                  )) : <p className="text-slate-500 text-sm">No source files attached.</p>}
                </div>
              </div>

              <button
                onClick={() => handleActivate(selectedProject.run_id)}
                className="w-full px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2"
              >
                Open This Project <ArrowRight size={18} />
              </button>
            </div>
          )}
          {!detailsLoading && !selectedProject && <p className="text-slate-500">Select a run to see its details.</p>}
        </div>
      </div>
    </div>
  );
};

export default Projects;


