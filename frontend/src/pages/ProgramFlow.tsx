import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Activity, AlertCircle, Info, Loader2, RefreshCcw } from 'lucide-react';
import toast from 'react-hot-toast';
import { getApiErrorDetail, ProjectAPI } from '../services/api';
import type { ProceduralFlowDetail, ProceduralFlowSummary } from '../services/api';

const yesNo = (value?: boolean) => (value ? 'Yes' : 'No');

const FlowList = ({
  title,
  items,
  primaryKey,
  secondaryKey,
}: {
  title: string;
  items?: any[];
  primaryKey: string;
  secondaryKey: string;
}) => (
  <section className="space-y-3">
    {title && <h3 className="text-sm font-bold uppercase tracking-widest text-indigo-400">{title}</h3>}
    <div className="space-y-2">
      {(items || []).length > 0 ? (items || []).map((item, index) => (
        <div key={`${title}-${index}`} className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
          <p className="break-words text-sm font-bold text-slate-100">
            {item?.[primaryKey] || item?.name || `Item ${index + 1}`}
          </p>
          <p className="mt-1 break-words font-mono text-xs leading-5 text-slate-500">
            {item?.[secondaryKey] || item?.description || 'No technical reference provided.'}
          </p>
        </div>
      )) : (
        <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4 text-sm text-slate-500">
          None detected.
        </div>
      )}
    </div>
  </section>
);

const ProgramFlow = () => {
  const runId = localStorage.getItem('active_run_id');
  const [proceduralFlows, setProceduralFlows] = useState<ProceduralFlowSummary[]>([]);
  const [selectedFlow, setSelectedFlow] = useState<ProceduralFlowDetail | null>(null);
  const [flowLoading, setFlowLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);

  const loadProceduralFlows = async () => {
    if (!runId) {
      setInitialLoading(false);
      return;
    }

    try {
      const data = await ProjectAPI.listProceduralFlows(runId);
      const flows = data.flows || [];
      setProceduralFlows(flows);
      setSelectedFlow((current) => {
        if (current && flows.some((flow) => String(flow.file_id) === String(current.file_id))) {
          return current;
        }
        return null;
      });
    } catch (e) {
      toast.error(getApiErrorDetail(e, 'Failed to load program flow'));
    } finally {
      setInitialLoading(false);
    }
  };

  useEffect(() => {
    void loadProceduralFlows();
  }, [runId]);

  const extractProceduralFlow = async (force = false) => {
    if (!runId || flowLoading) return;
    if (force && !window.confirm('Regenerate program flow and overwrite the saved flow JSON for this run?')) return;

    setFlowLoading(true);
    try {
      await ProjectAPI.extractProceduralFlow(runId, force);
      await loadProceduralFlows();
      toast.success(force ? 'Program flow regenerated' : 'Program flow loaded or extracted');
    } catch (e) {
      toast.error(getApiErrorDetail(e, 'Program flow extraction failed'));
    } finally {
      setFlowLoading(false);
    }
  };

  const loadProceduralFlowDetail = async (fileId: string | number) => {
    if (!runId) return;

    setFlowLoading(true);
    try {
      const data = await ProjectAPI.getProceduralFlow(runId, fileId);
      setSelectedFlow(data);
    } catch (e) {
      toast.error(getApiErrorDetail(e, 'Failed to load program flow detail'));
    } finally {
      setFlowLoading(false);
    }
  };

  return (
    <div className="space-y-6 min-h-screen pb-24">
      <header className="flex flex-col gap-5 border-b border-slate-800 pb-7 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-1">
          <div className="mb-3 flex items-center gap-2">
            <span className="label">Modernization Pipeline</span>
            <span className="text-slate-600">/</span>
            <span className="label text-indigo-400">Program Flow</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Program Flow</h1>
          <p className="text-slate-400">Entry points, branches, loops, data movement, calls, and exits.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => extractProceduralFlow(false)}
            disabled={flowLoading}
            className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white transition-all hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {flowLoading ? <Loader2 size={14} className="animate-spin" /> : <Activity size={14} />}
            {flowLoading ? 'Extracting' : 'Extract'}
          </button>
          <button
            type="button"
            onClick={() => extractProceduralFlow(true)}
            disabled={flowLoading}
            className="flex items-center gap-2 rounded-xl bg-amber-600 px-4 py-2 text-xs font-bold text-white transition-all hover:bg-amber-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {flowLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCcw size={14} />}
            Regenerate
          </button>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-6 min-h-[calc(100vh-260px)] items-start">
        <div className="col-span-4 h-[calc(100vh-260px)] overflow-hidden">
          <div className="space-y-3 overflow-y-auto max-h-[calc(100vh-280px)] pr-2 custom-scrollbar">
            {initialLoading ? (
              <div className="flex flex-col items-center justify-center gap-3 p-10 text-center text-sm text-slate-500">
                <Loader2 className="animate-spin text-indigo-500" />
                Loading saved program flow...
              </div>
            ) : proceduralFlows.length > 0 ? proceduralFlows.map((flow) => (
              <button
                key={flow.file_id}
                type="button"
                onClick={() => loadProceduralFlowDetail(flow.file_id)}
                className={`w-full rounded-xl border p-4 text-left transition-all ${
                  selectedFlow && String(selectedFlow.file_id) === String(flow.file_id)
                    ? 'border-indigo-500 bg-indigo-500/10'
                    : 'border-slate-800 bg-slate-900 hover:border-slate-600'
                }`}
              >
                <div className="mb-2 flex items-start justify-between gap-3">
                  <span className="break-all font-mono text-xs font-bold text-indigo-400">{flow.file_name}</span>
                  <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] text-slate-400">{flow.execution_steps} Steps</span>
                </div>
                <div className="grid grid-cols-3 gap-2 text-[10px] uppercase tracking-wide text-slate-500">
                  <span>{flow.decision_count} Decisions</span>
                  <span>{flow.loop_count} Loops</span>
                  <span>{flow.external_operation_count} Ops</span>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] uppercase tracking-wide text-slate-500">
                  <span>Lang: {flow.detected_language || 'Unknown'}</span>
                  <span>Fallback: {yesNo(flow.fallback_used)}</span>
                </div>
                <p className="mt-2 text-xs text-slate-400">Entry: {flow.entry_point || 'Unknown'}</p>
              </button>
            )) : (
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-center text-sm text-slate-500">
                No program flow extracted yet.
              </div>
            )}
          </div>
        </div>

        <div className="col-span-8 min-h-0 overflow-hidden">
          <div className="glass-card h-[calc(100vh-260px)] overflow-hidden rounded-3xl border border-indigo-500/30 bg-slate-900/50">
            {selectedFlow ? (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex h-full flex-col">
                <div className="shrink-0 border-b border-slate-800 bg-slate-900/90 p-8">
                  <div className="border-l-4 border-indigo-500 pl-4">
                    <h2 className="break-all text-3xl font-black uppercase tracking-tight text-white">{selectedFlow.file_name}</h2>
                    <p className="mt-1 font-mono text-xs text-slate-500">
                      Entry point: {selectedFlow.entry_point?.name || 'Unknown'}
                    </p>
                  </div>
                  <div className="mt-5 grid grid-cols-2 gap-3 text-xs xl:grid-cols-4">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">Detected Language</p>
                      <p className="mt-1 font-mono text-slate-200">{selectedFlow.detected_language || 'Unknown'}</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">Execution Steps</p>
                      <p className="mt-1 font-mono text-slate-200">{selectedFlow.execution_flow?.length || 0}</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">Decisions / Loops</p>
                      <p className="mt-1 font-mono text-slate-200">{selectedFlow.decision_branches?.length || 0} / {selectedFlow.loops?.length || 0}</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">Fallback Used</p>
                      <p className="mt-1 font-mono text-slate-200">{yesNo(selectedFlow.fallback_used)}</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">External Ops</p>
                      <p className="mt-1 font-mono text-slate-200">{selectedFlow.external_operations?.length || 0}</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">External Calls</p>
                      <p className="mt-1 font-mono text-slate-200">{selectedFlow.external_calls?.length || 0}</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 xl:col-span-2">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">Fallback Reason</p>
                      <p className="mt-1 truncate font-mono text-slate-200">{selectedFlow.fallback_reason || 'None'}</p>
                    </div>
                  </div>
                </div>

                <div className="min-h-0 flex-1 overflow-y-auto p-8 pr-5 custom-scrollbar">
                  <div className="space-y-8">
                    <section className="space-y-3">
                      <div className="flex items-center gap-2 text-indigo-400">
                        <Activity size={18} />
                        <h3 className="text-sm font-bold uppercase tracking-widest">Execution Flow</h3>
                      </div>
                      <div className="space-y-3">
                        {(selectedFlow.execution_flow || []).map((step: any, index: number) => (
                          <div key={`${step.step_no || index}-${step.name || index}`} className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4">
                            <div className="flex items-start justify-between gap-3">
                              <p className="font-mono text-xs font-bold text-indigo-300">{step.step_no || index + 1}. {step.name || 'Unnamed step'}</p>
                              <span className="rounded bg-slate-800 px-2 py-1 text-[10px] uppercase text-slate-400">{step.type || 'unknown'}</span>
                            </div>
                            <p className="mt-2 text-sm leading-relaxed text-slate-300">{step.description || 'No step description provided.'}</p>
                            {step.calls?.length > 0 && (
                              <p className="mt-2 text-xs text-slate-500">Calls: {step.calls.join(', ')}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </section>

                    <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                      <FlowList title="Decision Branches" items={selectedFlow.decision_branches} primaryKey="condition" secondaryKey="technical_reference" />
                      <FlowList title="Loops" items={selectedFlow.loops} primaryKey="loop_type" secondaryKey="condition" />
                      <FlowList title="Data Movement" items={selectedFlow.data_movement} primaryKey="variable" secondaryKey="technical_reference" />
                      <FlowList title="External Operations" items={selectedFlow.external_operations} primaryKey="operation_type" secondaryKey="technical_reference" />
                      <FlowList title="External Calls" items={selectedFlow.external_calls} primaryKey="program" secondaryKey="technical_reference" />
                      <FlowList title="Exit Paths" items={selectedFlow.exit_paths} primaryKey="type" secondaryKey="technical_reference" />
                    </section>

                    {selectedFlow.unresolved_items?.length > 0 && (
                      <section className="space-y-3">
                        <div className="flex items-center gap-2 text-amber-400">
                          <AlertCircle size={18} />
                          <h3 className="text-sm font-bold uppercase tracking-widest">Unresolved Items</h3>
                        </div>
                        <FlowList title="" items={selectedFlow.unresolved_items} primaryKey="item" secondaryKey="reason" />
                      </section>
                    )}
                  </div>
                </div>
              </motion.div>
            ) : (
              <div className="flex h-full flex-col items-center justify-center space-y-4 text-center opacity-50">
                <Info size={40} className="text-slate-600" />
                <p className="text-sm text-slate-500">
                  Select a file from the left to view its <br />
                  Procedural Program Flow.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProgramFlow;
