import { useEffect, useState } from 'react';
import {
  Activity, Zap, ShieldAlert, Cpu, MessageSquare, Share2, FileText, GitBranch,
  Settings, Pause, Play, X, Send, SlidersHorizontal
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import PageHeader from '../components/PageHeader';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';
import { API_BASE_URL } from '../services/api';

const explorerTabs = [
  { id: 'dependencies', icon: Share2, label: 'Deps', message: 'Mapping call hierarchy and file relationships...' },
  { id: 'logic', icon: FileText, label: 'Logic', message: 'Extracting business rules from active chunks...' },
  { id: 'ddd', icon: GitBranch, label: 'DDD', message: 'Defining domain boundaries and ownership...' },
];

type MissionEvent = {
  timestamp: string;
  message: string;
  level: string;
  project_id?: string | null;
};

type MissionStatus = {
  is_running: boolean;
  progress: number;
  active_project: string | null;
  project_count: number;
  file_count: number;
  active_chunk: string;
  self_healing_events: number;
  tokens_used: string;
  latest_event: MissionEvent | null;
  events: MissionEvent[];
};

const initialStatus: MissionStatus = {
  is_running: true,
  progress: 0,
  active_project: null,
  project_count: 0,
  file_count: 0,
  active_chunk: 'Idle',
  self_healing_events: 0,
  tokens_used: 'n/a',
  latest_event: null,
  events: [],
};

const MissionControl = () => {
  const [isRunning, setIsRunning] = useState(true);
  const [status, setStatus] = useState<MissionStatus>(initialStatus);
  const [activeExplorerTab, setActiveExplorerTab] = useState('dependencies');
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [logs, setLogs] = useState<string[]>(['Connecting to backend...', 'Listening for pipeline events...']);
  const [chatInput, setChatInput] = useState('');

  useEffect(() => {
    let active = true;

    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/mission-control/status`);
        if (!response.ok) {
          throw new Error(`Request failed (${response.status})`);
        }

        const payload = await response.json();
        if (!active) {
          return;
        }

        const nextStatus = {
          ...payload,
          progress: Number(payload.progress || 0),
          project_count: Number(payload.project_count || 0),
          file_count: Number(payload.file_count || 0),
          self_healing_events: Number(payload.self_healing_events || 0),
        } as MissionStatus;

        setStatus(nextStatus);
        const nextLogs = (payload.events || []).map((event: MissionEvent) => {
          const stamp = event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : 'now';
          return `[${stamp}] ${event.message}`;
        });
        setLogs(nextLogs.length ? nextLogs.slice(-20) : ['Awaiting backend events...']);
      } catch (error) {
        if (!active) {
          return;
        }
        setLogs((prev) => [
          ...(prev.length > 0 ? prev : ['Connecting to backend...']),
          `Backend unavailable: ${error instanceof Error ? error.message : 'unknown error'}`,
        ].slice(-20));
      }
    };

    fetchStatus();
    const interval = window.setInterval(fetchStatus, 3000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  const activeTab = explorerTabs.find((tab) => tab.id === activeExplorerTab) || explorerTabs[0];
  const effectiveIsRunning = isRunning && status.is_running;
  const progressValue = Math.max(0, Math.min(100, status.progress || 0));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Mission Control"
        description="Monitor pipeline execution, agent activity, validation loops, and live modernization events from one command view."
        action={(
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setIsRunning(!isRunning)} className="btn-glow">
              {effectiveIsRunning ? <Pause size={18} /> : <Play size={18} />}
              {effectiveIsRunning ? 'Pause Run' : 'Resume Run'}
            </button>
            <button onClick={() => setIsConfigOpen(true)} className="btn-secondary flex items-center gap-2 px-4 py-3">
              <Settings size={18} />
              Config
            </button>
          </div>
        )}
        meta={<StatusBadge status={effectiveIsRunning ? 'Running' : 'Pending'} />}
      />

      <div className="kpi-bento">
        <div className="glass-card kpi-featured p-5 flex flex-col justify-between">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="label">Overall Progress</p>
              <p className="text-display mt-2">{progressValue.toFixed(1)}%</p>
              <p className="text-body-sm mt-2">
                {status.active_project ? `Active project: ${status.active_project}` : 'Waiting for a project to start.'}
              </p>
            </div>
            <Activity className="text-[var(--corporate-accent)]" size={28} />
          </div>
          <div className="pipeline-card-progress mt-8">
            <span style={{ width: `${progressValue}%` }} />
          </div>
        </div>
        <div className="glass-card p-5">
          <Zap className="text-[var(--corporate-warning)]" size={22} />
          <p className="label mt-4">Tokens Used</p>
          <p className="text-heading mt-2">{status.tokens_used}</p>
        </div>
        <div className="glass-card p-5">
          <ShieldAlert className="text-[var(--corporate-success)]" size={22} />
          <p className="label mt-4">Self-Healing</p>
          <p className="text-heading mt-2">{status.self_healing_events} Events</p>
        </div>
        <div className="glass-card p-5">
          <Cpu className="text-[var(--corporate-accent)]" size={22} />
          <p className="label mt-4">Active Chunk</p>
          <p className="text-heading mt-2">{status.active_chunk}</p>
        </div>
        <div className="glass-card p-5">
          <MessageSquare className="text-[var(--corporate-success)]" size={22} />
          <p className="label mt-4">AI Analyst</p>
          <p className="text-heading mt-2">{status.latest_event?.message ? 'Online' : 'Idle'}</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[300px_minmax(0,1fr)_320px]">
        <aside className="glass-card min-h-[520px] overflow-hidden">
          <div className="border-b border-[var(--corporate-border)] p-4">
            <SectionLabel>Explorer</SectionLabel>
          </div>
          <div className="premium-tabs m-4 w-auto">
            {explorerTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveExplorerTab(tab.id)}
                className={`premium-tab flex-1 ${activeExplorerTab === tab.id ? 'premium-tab-active' : 'premium-tab-idle'}`}
              >
                <tab.icon size={15} />
                {tab.label}
              </button>
            ))}
          </div>
          <div className="p-4 text-body-sm">{activeTab.message}</div>
        </aside>

        <section className="min-w-0 space-y-6">
          <div className="glass-card p-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <SectionLabel className="flex-1">Active Project</SectionLabel>
              <StatusBadge status={status.active_project ? 'Running' : 'Pending'} />
            </div>
            <div className="rounded-lg border border-[var(--corporate-border-strong)] bg-[var(--terminal-bg)] p-4 font-mono text-sm text-[var(--terminal-text)]">
              <div><span className="opacity-60">Project Count:</span> {status.project_count}</div>
              <div><span className="opacity-60">Files:</span> {status.file_count}</div>
              <div><span className="opacity-60">Latest Event:</span> {status.latest_event?.message || 'No events yet'}</div>
            </div>
          </div>

          <div className="overflow-hidden rounded-lg border border-[var(--corporate-border-strong)] bg-[var(--terminal-bg)] shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/10 bg-black/20 px-4 py-3">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-red-500/60" />
                <div className="h-3 w-3 rounded-full bg-amber-500/60" />
                <div className="h-3 w-3 rounded-full bg-emerald-500/60" />
              </div>
              <span className="font-mono text-xs uppercase tracking-widest text-[var(--terminal-text)] opacity-70">system_log_stream</span>
            </div>
            <div className="h-[360px] space-y-2 overflow-y-auto p-4 font-mono text-sm">
              {logs.map((log, index) => (
                <div key={`${log}-${index}`} className="flex gap-3 text-[var(--terminal-text)]">
                  <span className="shrink-0 opacity-45">[{new Date().toLocaleTimeString()}]</span>
                  <span className={log.includes('Healing') ? 'text-[var(--corporate-warning)]' : 'text-[var(--corporate-success)]'}>{log}</span>
                </div>
              ))}
              {effectiveIsRunning && <div className="animate-pulse text-[var(--corporate-accent)]">_ awaiting_next_chunk...</div>}
            </div>
          </div>
        </section>

        <aside className="glass-card flex min-h-[520px] flex-col overflow-hidden">
          <div className="border-b border-[var(--corporate-border)] p-4">
            <SectionLabel>AI Analyst</SectionLabel>
          </div>
          <div className="flex-1 space-y-4 p-4">
            <div className="rounded-lg border border-[var(--corporate-border)] bg-[var(--corporate-bg-soft)] p-4 text-body-sm">
              I am monitoring this migration. Ask me about any chunk, dependency, or extracted rule.
            </div>
          </div>
          <div className="flex gap-2 border-t border-[var(--corporate-border)] p-4">
            <input
              value={chatInput}
              onChange={(event) => setChatInput(event.target.value)}
              className="min-w-0 flex-1 rounded-lg border border-[var(--corporate-border)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--corporate-accent)]"
              placeholder="Ask about a rule..."
            />
            <button onClick={() => setChatInput('')} className="btn-glow px-3 py-2">
              <Send size={15} />
            </button>
          </div>
        </aside>
      </div>

      <AnimatePresence>
        {isConfigOpen && (
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            className="fixed right-0 top-0 z-[100] h-full w-96 max-w-[92vw] border-l border-[var(--corporate-border-strong)] bg-[var(--corporate-panel-strong)] p-6 shadow-2xl"
          >
            <div className="mb-8 flex items-center justify-between gap-4">
              <div>
                <SectionLabel>Configuration</SectionLabel>
                <h3 className="text-heading mt-2">System Config</h3>
              </div>
              <button onClick={() => setIsConfigOpen(false)} className="btn-secondary p-2"><X size={20} /></button>
            </div>
            <div className="space-y-6">
              <label className="block space-y-2">
                <span className="label">Target Language</span>
                <select className="w-full rounded-lg border border-[var(--corporate-border)] p-3 text-sm">
                  <option>Java 21 (Spring Boot)</option>
                  <option>C# 12 (.NET 8)</option>
                </select>
              </label>
              <label className="block space-y-2">
                <span className="label">Token Budget</span>
                <input type="number" className="w-full rounded-lg border border-[var(--corporate-border)] p-3 text-sm" defaultValue={5000000} />
              </label>
              <div className="glass-card flex items-center justify-between p-4">
                <span className="text-card-title">Self-Healing Loop</span>
                <div className="relative h-6 w-11 rounded-full bg-[var(--corporate-accent)]">
                  <div className="absolute right-1 top-1 h-4 w-4 rounded-full bg-white" />
                </div>
              </div>
              <button className="btn-glow w-full">
                <SlidersHorizontal size={18} />
                Apply Settings
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default MissionControl;
