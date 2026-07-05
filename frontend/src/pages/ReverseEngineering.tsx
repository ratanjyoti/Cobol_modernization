import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ProjectAPI } from '../services/api';
import {
  AlertTriangle, Cpu, Database, FileCheck, FileText, GitBranch,
  Info, Layers, Loader2, Share2, X, Zap
} from 'lucide-react';

const tierStyle: Record<string, string> = {
  High: 'bg-red-500/10 text-red-300 border-red-500/30',
  Medium: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  Low: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
};

const modeStyle: Record<string, string> = {
  Thorough: 'text-red-300',
  Balanced: 'text-amber-300',
  Turbo: 'text-emerald-300',
};

const ReverseEngineering = () => {
  const runId = localStorage.getItem('active_run_id');
  const [activeTab, setActiveTab] = useState('complexity');
  const [complexityData, setComplexityData] = useState<any>(null);
  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [graphData, setGraphData] = useState<any>({ nodes: [], edges: [] });
  const [dddData, setDddData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    const loadTabData = async () => {
      if (!runId) {
        setError('No active project selected. Start or open a project first.');
        return;
      }

      setLoading(true);
      setError('');
      try {
        if (activeTab === 'complexity') {
          const res = await ProjectAPI.getComplexity(runId);
          if (!active) return;
          setComplexityData(res);
          setSelectedFile((current: any) => current ? res.files?.find((file: any) => file.id === current.id) || null : res.files?.[0] || null);
        }
        if (activeTab === 'dependencies') {
          const res = await ProjectAPI.getGraph(runId);
          if (!active) return;
          setGraphData(res || { nodes: [], edges: [] });
        }
        if (activeTab === 'ddd') {
          const res = await ProjectAPI.getDDD(runId);
          if (!active) return;
          setDddData(res || []);
        }
      } catch (e: any) {
        if (active) setError(e.response?.data?.detail || 'Unable to load analysis data for this run.');
      } finally {
        if (active) setLoading(false);
      }
    };

    loadTabData();
    return () => { active = false; };
  }, [activeTab, runId]);

  const tabs = [
    { id: 'complexity', label: 'Complexity', icon: AlertTriangle },
    { id: 'dependencies', label: 'Dependencies', icon: Share2 },
    { id: 'ddd', label: 'DDD Discovery', icon: GitBranch },
    { id: 'reports', label: 'Reports', icon: FileCheck },
  ];

  const dependencySummary = useMemo(() => {
    const nodes = graphData?.nodes || [];
    const edges = graphData?.edges || [];
    const unresolved = nodes.filter((node: any) => node.resolved === false).length;
    return { nodes: nodes.length, edges: edges.length, unresolved };
  }, [graphData]);

  return (
    <div className="space-y-6 h-full">
      <div className="flex justify-between items-end gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Reverse Engineering Explorer</h1>
          <p className="text-slate-400">Complexity scoring, dependency discovery, and domain grouping for the active run.</p>
        </div>
        <div className="text-xs font-mono text-slate-500">Run: <span className="text-slate-300">{runId || 'none'}</span></div>
      </div>

      <div className="flex flex-wrap gap-2 p-1 bg-slate-950 rounded-xl border border-slate-800 w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === tab.id ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:bg-slate-800'
            }`}
          >
            <tab.icon size={14} /> {tab.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-260px)] min-h-[560px]">
        <div className="col-span-12 xl:col-span-9 glass-card p-6 overflow-y-auto relative">
          {loading && <div className="absolute inset-0 bg-slate-900/70 flex items-center justify-center z-10"><Loader2 className="animate-spin text-indigo-500" /></div>}
          {error && <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">{error}</div>}

          <AnimatePresence mode="wait">
            {activeTab === 'complexity' && (
              <motion.div key="complexity" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                    <p className="text-xs uppercase font-bold text-slate-500">Overall Effort</p>
                    <p className="mt-1 text-xl font-bold text-white">{complexityData?.overall_effort || 'Balanced'}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                    <p className="text-xs uppercase font-bold text-slate-500">Average Score</p>
                    <p className="mt-1 text-xl font-bold text-white">{complexityData?.average_score ?? 0}</p>
                  </div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
                    <p className="text-xs uppercase font-bold text-slate-500">Files Scored</p>
                    <p className="mt-1 text-xl font-bold text-white">{complexityData?.files?.length || 0}</p>
                  </div>
                </div>

                <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4 text-sm text-slate-300">
                  <span className="font-bold text-indigo-300">How scoring works: </span>{complexityData?.method || 'Upload files to calculate complexity.'}
                </div>

                <div className="space-y-3">
                  {(complexityData?.files || []).map((file: any) => (
                    <button
                      key={file.id || file.name}
                      onClick={() => setSelectedFile(file)}
                      className={`w-full grid grid-cols-12 items-center gap-3 p-4 rounded-xl border transition-all text-left ${
                        selectedFile?.id === file.id ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-800 bg-slate-900 hover:border-slate-600'
                      }`}
                    >
                      <div className="col-span-5 min-w-0">
                        <p className="truncate text-sm font-bold text-white">{file.name}</p>
                        <p className="truncate text-[11px] font-mono text-slate-500">{file.filepath}</p>
                      </div>
                      <div className="col-span-2 text-xs text-slate-400"><Layers size={13} className="inline mr-1" />{file.chunks} chunk{file.chunks === 1 ? '' : 's'}</div>
                      <div className="col-span-2 text-xs font-mono text-slate-300">Score {file.score}</div>
                      <div className={`col-span-1 text-center rounded border px-2 py-1 text-[10px] font-bold ${tierStyle[file.tier] || tierStyle.Low}`}>{file.tier}</div>
                      <div className={`col-span-2 text-right text-xs font-bold ${modeStyle[file.mode] || 'text-indigo-300'}`}>{file.mode} mode</div>
                    </button>
                  ))}
                  {(!complexityData?.files || complexityData.files.length === 0) && (
                    <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-500">No complexity scores yet. Upload source files for this run.</div>
                  )}
                </div>
              </motion.div>
            )}

            {activeTab === 'dependencies' && (
              <motion.div key="dependencies" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4"><p className="text-xs uppercase font-bold text-slate-500">Nodes</p><p className="mt-1 text-xl font-bold text-white">{dependencySummary.nodes}</p></div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4"><p className="text-xs uppercase font-bold text-slate-500">Relations</p><p className="mt-1 text-xl font-bold text-white">{dependencySummary.edges}</p></div>
                  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4"><p className="text-xs uppercase font-bold text-slate-500">Unresolved</p><p className="mt-1 text-xl font-bold text-white">{dependencySummary.unresolved}</p></div>
                </div>
                <div className="rounded-xl border border-slate-800 overflow-hidden">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-800 text-slate-400 text-xs uppercase"><tr><th className="p-3">Source</th><th className="p-3">Relation</th><th className="p-3">Target</th></tr></thead>
                    <tbody className="divide-y divide-slate-800">
                      {(graphData?.edges || []).map((edge: any, index: number) => <tr key={`${edge.from}-${edge.to}-${index}`} className="text-slate-300"><td className="p-3 font-mono text-xs">{edge.from}</td><td className="p-3 text-indigo-300 text-xs font-bold">{edge.type}</td><td className="p-3 font-mono text-xs">{edge.to}</td></tr>)}
                    </tbody>
                  </table>
                  {(graphData?.edges || []).length === 0 && <div className="p-8 text-center text-slate-500">No dependency relations discovered yet.</div>}
                </div>
              </motion.div>
            )}

            {activeTab === 'ddd' && (
              <motion.div key="ddd" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {dddData.map((domain: any) => (
                  <div key={domain.name} className="rounded-xl border border-slate-800 bg-slate-900 p-5 space-y-4">
                    <div className="flex items-center gap-3"><div className={`w-3 h-3 rounded-full ${domain.color}`} /><h4 className="font-bold text-white">{domain.name}</h4></div>
                    <div className="flex flex-wrap gap-2">{domain.programs.map((program: string) => <span key={program} className="text-[10px] bg-slate-800 text-slate-300 px-2 py-1 rounded border border-slate-700">{program}</span>)}</div>
                    <div className="text-xs text-slate-500">{domain.rules} discovered relation{domain.rules === 1 ? '' : 's'} mapped into this boundary.</div>
                  </div>
                ))}
                {dddData.length === 0 && <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-500">No DDD boundaries discovered yet.</div>}
              </motion.div>
            )}

            {activeTab === 'reports' && (
              <motion.div key="reports" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-slate-400">
                Analysis reports will use the complexity, dependency, and DDD data shown in the other tabs.
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="col-span-12 xl:col-span-3 glass-card p-6 border-indigo-500/30 bg-indigo-500/5 overflow-y-auto">
          {selectedFile && activeTab === 'complexity' ? (
            <div className="space-y-6">
              <div className="flex justify-between items-start gap-3">
                <div className="min-w-0"><h3 className="text-lg font-bold text-white truncate">{selectedFile.name}</h3><p className="text-[11px] font-mono text-slate-500 truncate">{selectedFile.filepath}</p></div>
                <button onClick={() => setSelectedFile(null)} className="text-slate-500 hover:text-white transition-colors"><X size={18} /></button>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3">
                <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase"><Zap size={14} /> Calculation</div>
                {(selectedFile.calculation || []).map((item: any) => <div key={item.label} className="flex justify-between gap-3 text-sm"><span className="text-slate-500">{item.label}</span><span className="text-white font-mono">{item.points}</span></div>)}
                <div className="h-px bg-slate-800" />
                <div className="flex justify-between text-sm font-bold"><span className="text-slate-300">Final Score</span><span className="text-indigo-300">{selectedFile.score}</span></div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-2">
                <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold uppercase"><Cpu size={14} /> Execution Mode</div>
                <p className="text-sm text-slate-300">This file will use <span className="text-white font-bold">{selectedFile.mode}</span> processing with <span className="text-white font-bold">{selectedFile.chunks}</span> stored chunk{selectedFile.chunks === 1 ? '' : 's'}.</p>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-60">
              <Info size={40} className="text-slate-600" />
              <p className="text-sm text-slate-500">Select a scored file to see how its complexity and processing mode were calculated.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReverseEngineering;
