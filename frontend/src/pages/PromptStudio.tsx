import { useEffect, useState, useMemo } from 'react';
import {
  Save,
  FileText,
  AlertTriangle,
  RotateCcw,
  Loader2,
  CheckCircle2,
  Search,
  ChevronRight,
  Info
} from 'lucide-react';
import PageHeader from '../components/PageHeader';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';
import { API_BASE_URL } from '../services/api';

type PromptItem = {
  key: string;
  name: string;
  filename: string;
  content: string;
  default_content: string;
  has_override: boolean;
  project_id: string;
  agent: string;
  language?: string;
  type: 'System Prompt' | 'User Template';
};

const CATEGORIES = [
  { id: 'all', label: 'All Prompts' },
  { id: 'business_logic', label: 'Business Logic' },
  { id: 'conversion_planner', label: 'Planning' },
  { id: 'code_generator', label: 'Generation' },
  { id: 'compile_fix', label: 'Compile Fix' },
  { id: 'technical', label: 'Technical' },
];

const getProjectId = () => {
  return (
    localStorage.getItem('active_run_id') ||
    localStorage.getItem('current_run_id') ||
    localStorage.getItem('current_project_id') ||
    localStorage.getItem('projectId') ||
    'default'
  );
};

const PromptStudio = () => {
  const [projectId, setProjectId] = useState(getProjectId());
  const [prompts, setPrompts] = useState<Record<string, PromptItem>>({});
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const syncProjectId = () => {
      setProjectId(getProjectId());
    };

    syncProjectId();
    window.addEventListener('storage', syncProjectId);
    window.addEventListener('modernizer-project-changed', syncProjectId as EventListener);

    return () => {
      window.removeEventListener('storage', syncProjectId);
      window.removeEventListener('modernizer-project-changed', syncProjectId as EventListener);
    };
  }, []);

  const loadPrompts = async (currentProjectId: string | null = projectId) => {
    setLoading(true);
    setMessage('');

    if (!currentProjectId) {
      setPrompts({});
      setMessage('No project selected. Create or open a project first.');
      setLoading(false);
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/prompts/code-generation?project_id=${encodeURIComponent(currentProjectId)}`
      );
      if (!response.ok) throw new Error('Failed to load prompts');
      const data = await response.json();
      const promptMap: Record<string, PromptItem> = {};
      for (const item of data.prompts || []) {
        promptMap[item.key] = item;
      }
      setPrompts(promptMap);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to load prompts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPrompts(projectId);
  }, [projectId]);

  // Filtered list based on search and category
  const filteredPrompts = useMemo(() => {
    return Object.values(prompts).filter(p => {
      const matchesSearch = p.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                            p.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            (p.language || '').toLowerCase().includes(searchQuery.toLowerCase());
      
      const matchesCategory = activeCategory === 'all' || p.key.startsWith(activeCategory);
      
      return matchesSearch && matchesCategory;
    });
  }, [prompts, searchQuery, activeCategory]);

  const updatePromptValue = (key: string, value: string) => {
    setPrompts(prev => ({ ...prev, [key]: { ...prev[key], content: value } }));
  };

  const savePrompt = async (key: string) => {
    const prompt = prompts[key];
    if (!prompt) return;
    setSavingKey(key);
    try {
      const response = await fetch(
        `${API_BASE_URL}/prompts/code-generation/${encodeURIComponent(key)}?project_id=${encodeURIComponent(projectId || getProjectId())}`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: prompt.content }),
        }
      );
      if (!response.ok) throw new Error('Save failed');
      await loadPrompts(projectId || getProjectId());
      setMessage(`${prompt.name} saved successfully.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Save failed');
    } finally {
      setSavingKey(null);
    }
  };

  const resetPrompt = async (key: string) => {
    setSavingKey(key);
    try {
      const response = await fetch(
        `${API_BASE_URL}/prompts/code-generation/${encodeURIComponent(key)}/reset?project_id=${encodeURIComponent(projectId || getProjectId())}`,
        { method: 'POST' }
      );
      if (!response.ok) throw new Error('Reset failed');
      await loadPrompts(projectId || getProjectId());
      setMessage(`Reset to default.`);
    } catch (error) {
      setMessage('Reset failed');
    } finally {
      setSavingKey(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Prompt Studio"
        description="The single source of truth for all agent behaviors."
        action={
          <div className="flex items-center gap-2">
             <div className="text-xs text-gray-400 mr-2">Project: <span className="font-mono text-white">{projectId}</span></div>
             <button onClick={() => void loadPrompts(projectId || getProjectId())} className="btn-secondary px-3 py-1 text-xs">
               Refresh
             </button>
          </div>
        }
      />

      {/* Search and Category Bar */}
      <div className="glass-card p-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 bg-black/30 p-1 rounded-lg border border-white/10">
          {CATEGORIES.map(cat => (
            <button 
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`px-3 py-1.5 text-xs rounded-md transition-all ${activeCategory === cat.id ? 'bg-[var(--corporate-accent)] text-white' : 'text-gray-400 hover:text-white'}`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={14} />
          <input 
            type="text" 
            placeholder="Search prompts, languages..." 
            className="bg-black/30 border border-white/10 rounded-lg pl-9 pr-4 py-1.5 text-sm outline-none focus:ring-1 focus:ring-[var(--corporate-accent)]"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {message && (
        <div className="glass-card p-3 flex items-center gap-2 text-sm text-green-400 animate-in fade-in slide-in-from-top-1">
          <CheckCircle2 size={16} /> {message}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center p-20"><Loader2 className="animate-spin" /></div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {filteredPrompts.map((prompt) => {
            const isDirty = prompt.content !== prompt.default_content;
            return (
              <section key={prompt.key} className={`glass-card p-6 transition-all border-l-4 ${prompt.has_override ? 'border-l-green-500' : 'border-l-gray-600'}`}>
                <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-heading">{prompt.name}</h3>
                      {isDirty && <span className="text-[10px] bg-orange-500/20 text-orange-400 px-1.5 py-0.5 rounded border border-orange-500/30">● Unsaved Changes</span>}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      <span className="flex items-center gap-1"><Info size={12}/> {prompt.agent}</span>
                      {prompt.language && <span>• {prompt.language}</span>}
                      <span>• {prompt.type}</span>
                      <span className="font-mono opacity-60">({prompt.filename})</span>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => resetPrompt(prompt.key)}
                      disabled={!prompt.has_override || savingKey === prompt.key}
                      className="btn-secondary flex items-center gap-2 px-3 py-1.5 text-xs"
                    >
                      <RotateCcw size={12} /> Reset
                    </button>
                    <button
                      onClick={() => savePrompt(prompt.key)}
                      disabled={savingKey === prompt.key}
                      className="btn-glow flex items-center gap-2 px-3 py-1.5 text-xs"
                    >
                      {savingKey === prompt.key ? <Loader2 className="animate-spin" size={12} /> : <Save size={12} />} Save
                    </button>
                  </div>
                </div>

                <div className="relative group">
                  <textarea
                    value={prompt.content}
                    onChange={(e) => updatePromptValue(prompt.key, e.target.value)}
                    className="h-64 w-full resize-y rounded-lg border border-white/10 bg-black/50 p-4 font-mono text-sm text-gray-300 outline-none transition-all focus:border-[var(--corporate-accent)]"
                  />
                  <div className="absolute bottom-3 right-3 text-[10px] text-gray-500 bg-black/60 px-2 py-1 rounded border border-white/5">
                    {prompt.content.length} / 15,000 chars
                  </div>
                </div>

                <div className="mt-4 flex items-center gap-2 text-xs text-gray-500">
                   <StatusBadge status={prompt.has_override ? "Project Override" : "System Default"} pulse={false} />
                   <span className="ml-auto opacity-50">Key: {prompt.key}</span>
                </div>
              </section>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default PromptStudio;
