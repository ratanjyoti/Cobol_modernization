import { useEffect, useState } from 'react';
import {
  Save,
  FileText,
  AlertTriangle,
  RotateCcw,
  Loader2,
  CheckCircle2,
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
};

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
  const [projectId] = useState(getProjectId());
  const [prompts, setPrompts] = useState<Record<string, PromptItem>>({});
  const [loading, setLoading] = useState(true);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  const promptList = Object.values(prompts);

  const loadPrompts = async () => {
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch(
        `${API_BASE_URL}/prompts/code-generation?project_id=${encodeURIComponent(projectId)}`
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to load prompts');
      }

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
    loadPrompts();
  }, []);

  const updatePromptValue = (key: string, value: string) => {
    setPrompts((previous) => ({
      ...previous,
      [key]: {
        ...previous[key],
        content: value,
      },
    }));
  };

  const savePrompt = async (key: string) => {
    const prompt = prompts[key];
    if (!prompt) return;

    setSavingKey(key);
    setMessage('');

    try {
      const response = await fetch(
        `${API_BASE_URL}/prompts/code-generation/${encodeURIComponent(key)}?project_id=${encodeURIComponent(projectId)}`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            content: prompt.content,
          }),
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to save prompt');
      }

      await loadPrompts();
      setMessage(`${prompt.name} saved successfully.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to save prompt');
    } finally {
      setSavingKey(null);
    }
  };

  const saveAllPrompts = async () => {
    for (const prompt of promptList) {
      await savePrompt(prompt.key);
    }
  };

  const resetPrompt = async (key: string) => {
    const prompt = prompts[key];
    if (!prompt) return;

    setSavingKey(key);
    setMessage('');

    try {
      const response = await fetch(
        `${API_BASE_URL}/prompts/code-generation/${encodeURIComponent(key)}/reset?project_id=${encodeURIComponent(projectId)}`,
        {
          method: 'POST',
        }
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to reset prompt');
      }

      await loadPrompts();
      setMessage(`${prompt.name} reset to default.`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Failed to reset prompt');
    } finally {
      setSavingKey(null);
    }
  };

  const modifiedCount = promptList.filter((prompt) => prompt.has_override).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Prompt Studio"
        description="Edit project-specific prompts used by planning, generation, and compile-fix agents."
        action={(
          <button onClick={saveAllPrompts} className="btn-glow" disabled={loading}>
            <Save size={18} />
            Save All Prompts
          </button>
        )}
        meta={<StatusBadge status={modifiedCount > 0 ? `${modifiedCount} Modified` : 'Default'} pulse={false} />}
      />

      <SectionLabel>Code Generation Prompt Constitution</SectionLabel>

      <section className="glass-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-heading">Project Prompt Scope</h3>
            <p className="text-body-sm">
              Editing here creates overrides for project <span className="font-mono">{projectId}</span>.
              Default prompts remain unchanged in the codebase.
            </p>
          </div>
          <StatusBadge status="File-based Overrides" pulse={false} />
        </div>
      </section>

      {message && (
        <section className="glass-card p-4">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <CheckCircle2 size={16} />
            <span>{message}</span>
          </div>
        </section>
      )}

      {loading ? (
        <section className="glass-card flex items-center gap-3 p-6">
          <Loader2 className="animate-spin" size={18} />
          <span className="text-body-sm">Loading prompts...</span>
        </section>
      ) : (
        <div className="grid grid-cols-1 gap-5">
          {promptList.map((prompt) => (
            <section key={prompt.key} className="glass-card p-6 space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="rounded-lg bg-[var(--corporate-accent-soft)] p-2 text-[var(--corporate-accent)]">
                    <FileText size={18} />
                  </div>
                  <div>
                    <h3 className="text-heading">{prompt.name}</h3>
                    <p className="text-body-sm">
                      {prompt.filename}
                      {' '}
                      ·
                      {' '}
                      {prompt.has_override ? 'Project override active' : 'Using default prompt'}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    className="btn-secondary flex items-center gap-2 px-3 py-2"
                    onClick={() => resetPrompt(prompt.key)}
                    disabled={savingKey === prompt.key || !prompt.has_override}
                  >
                    {savingKey === prompt.key ? <Loader2 className="animate-spin" size={14} /> : <RotateCcw size={14} />}
                    Reset
                  </button>

                  <button
                    className="btn-secondary flex items-center gap-2 px-3 py-2"
                    onClick={() => savePrompt(prompt.key)}
                    disabled={savingKey === prompt.key}
                  >
                    {savingKey === prompt.key ? <Loader2 className="animate-spin" size={14} /> : <Save size={14} />}
                    Save
                  </button>
                </div>
              </div>

              <textarea
                value={prompt.content}
                onChange={(event) => updatePromptValue(prompt.key, event.target.value)}
                className="h-56 w-full resize-y rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4 font-mono text-sm text-[var(--terminal-text)] outline-none transition-all focus:ring-2 focus:ring-[var(--corporate-accent)]"
              />

              <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-[var(--corporate-warning)]">
                <AlertTriangle size={14} />
                <span>
                  These prompt changes affect code planning, generation, and compile-fix behavior for this project.
                </span>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
};

export default PromptStudio;
