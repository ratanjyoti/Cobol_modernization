import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Loader2,
  Search,
  FileText,
  Zap,
  Info,
  Database,
  GitBranch,
  Activity,
  ShieldCheck,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { ProjectAPI } from '../services/api';

interface BusinessRule {
  id: number;
  rule_id: string;
  rule_text: string;
  technical_ref?: string;
  technical_yaml: string;
  status: 'PENDING' | 'VERIFIED' | 'REJECTED';
  filename: string;
  business_purpose?: string;
  functional_logic?: string;
  data_structures?: unknown[];
  dependencies?: string[];
  complexity_rating?: string;
  modernization_tips?: string[];
}

const BusinessLogic = () => {
  const navigate = useNavigate();
  const runId = localStorage.getItem('active_run_id');

  const [rules, setRules] = useState<BusinessRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoExtracting, setAutoExtracting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  const applyRules = (nextRules: BusinessRule[]) => {
    setRules(nextRules);
    setSelectedFile((current) => {
      if (current && nextRules.some((rule) => rule.filename === current)) return current;
      return nextRules[0]?.filename || null;
    });
  };

  useEffect(() => {
    let cancelled = false;

    const loadOrExtractRules = async () => {
      if (!runId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const existingRules = await ProjectAPI.getBusinessRules(runId);
        if (cancelled) return;

        const hasReportContent = existingRules.some((rule: BusinessRule) => rule.business_purpose || rule.functional_logic);
        if (existingRules.length > 0 && hasReportContent) {
          applyRules(existingRules);
          return;
        }

        const fileData = await ProjectAPI.listFiles(runId);
        if (cancelled) return;

        if ((fileData.files || []).length === 0) {
          applyRules([]);
          return;
        }

        setAutoExtracting(true);
        const extractedRules = await ProjectAPI.extractBusinessRules(runId);
        if (cancelled) return;

        applyRules(extractedRules);
        if (extractedRules.length > 0) {
          toast.success('Business logic loaded from uploaded files');
        }
      } catch (e) {
        if (!cancelled) toast.error('Failed to load business logic');
      } finally {
        if (!cancelled) {
          setAutoExtracting(false);
          setLoading(false);
        }
      }
    };

    loadOrExtractRules();

    return () => {
      cancelled = true;
    };
  }, [runId]);

  const handleExtract = async () => {
    if (!runId) return;

    setLoading(true);
    setAutoExtracting(true);
    try {
      const extractedRules = await ProjectAPI.extractBusinessRules(runId);
      applyRules(extractedRules);
      toast.success('Deep analysis complete!');
    } catch (e) {
      toast.error('Extraction failed');
    } finally {
      setAutoExtracting(false);
      setLoading(false);
    }
  };

  const updateRule = async (id: number, status: BusinessRule['status']) => {
    try {
      await ProjectAPI.verifyRule(id, { status });
      setRules((prev) => prev.map((rule) => rule.id === id ? { ...rule, status } : rule));
      toast.success('Rule updated');
    } catch (e) {
      toast.error('Failed to update rule');
    }
  };

  const files = useMemo(() => {
    const groups: Record<string, BusinessRule[]> = {};
    rules.forEach((rule) => {
      const filename = rule.filename || 'Uploaded source file';
      if (!groups[filename]) groups[filename] = [];
      groups[filename].push(rule);
    });
    return groups;
  }, [rules]);

  const verificationPercentage = useMemo(() => {
    if (rules.length === 0) return 0;
    const verified = rules.filter((rule) => rule.status === 'VERIFIED').length;
    return Math.round((verified / rules.length) * 100);
  }, [rules]);

  const filteredFiles = Object.keys(files).filter((filename) => {
    const query = searchTerm.trim().toLowerCase();
    if (!query) return true;
    const metadata = files[filename][0];
    return (
      filename.toLowerCase().includes(query) ||
      (metadata.business_purpose || '').toLowerCase().includes(query) ||
      files[filename].some((rule) => rule.rule_text.toLowerCase().includes(query))
    );
  });

  const currentFileRules = selectedFile ? files[selectedFile] || [] : [];
  const fileMetadata = currentFileRules[0] || null;

  return (
    <div className="space-y-6 h-full">
      <header className="flex flex-col gap-5 border-b border-slate-800 pb-7 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-1">
          <div className="mb-3 flex items-center gap-2">
            <span className="label">Modernization Pipeline</span>
            <span className="text-slate-600">/</span>
            <span className="label text-indigo-400">Business Logic Dossier</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Reverse Engineering Results</h1>
          <p className="text-slate-400">Complete functional decomposition of legacy source code.</p>
        </div>

        <div className="flex flex-col items-end gap-3">
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-xs font-bold text-slate-500 uppercase">Verification Progress</p>
              <p className={`text-xl font-black ${verificationPercentage >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {verificationPercentage}%
              </p>
            </div>
            <button onClick={handleExtract} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold transition-all flex items-center gap-2 border border-slate-700">
              <Zap size={14} /> Re-Analyze All
            </button>
          </div>
          <button
            onClick={() => navigate('/code-generation')}
            disabled={verificationPercentage < 80}
            className={`btn-glow flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all ${verificationPercentage >= 80 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-500 cursor-not-allowed'}`}
          >
            Approve Baseline & Proceed <ArrowRight size={18} />
          </button>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-320px)]">
        <div className="col-span-4 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
            <input
              type="text"
              placeholder="Search files or business logic..."
              className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </div>

          <div className="space-y-3 overflow-y-auto max-h-[60vh] pr-2">
            {loading ? (
              <div className="flex flex-col items-center justify-center gap-3 p-10 text-center text-sm text-slate-500">
                <Loader2 className="animate-spin text-indigo-500" />
                {autoExtracting ? 'Extracting business logic from uploaded files...' : 'Loading business logic...'}
              </div>
            ) : filteredFiles.length > 0 ? filteredFiles.map((filename) => (
              <button
                key={filename}
                type="button"
                onClick={() => setSelectedFile(filename)}
                className={`w-full p-4 text-left rounded-xl border cursor-pointer transition-all ${selectedFile === filename ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-800 bg-slate-900 hover:border-slate-600'}`}
              >
                <div className="flex justify-between items-center mb-2 gap-3">
                  <span className="font-mono text-xs text-indigo-400 font-bold break-all">{filename}</span>
                  <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-400 whitespace-nowrap">{files[filename].length} Rules</span>
                </div>
                <p className="text-xs text-slate-400 line-clamp-2 italic">
                  {files[filename][0].business_purpose || 'Analysis pending...'}
                </p>
              </button>
            )) : (
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-center text-sm text-slate-500">
                No business logic extracted yet.
              </div>
            )}
          </div>
        </div>

        <div className="col-span-8 glass-card p-8 border-indigo-500/30 bg-slate-900/50 rounded-3xl overflow-y-auto">
          {selectedFile && fileMetadata ? (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-10"
            >
              <div className="border-l-4 border-indigo-500 pl-4">
                <h2 className="text-3xl font-black text-white tracking-tight uppercase break-all">{selectedFile}</h2>
                <p className="text-slate-500 font-mono text-xs mt-1">Source: COBOL Legacy Mainframe</p>
              </div>

              <section className="space-y-3">
                <div className="flex items-center gap-2 text-indigo-400">
                  <FileText size={18} />
                  <h3 className="text-sm font-bold uppercase tracking-widest">Business Purpose</h3>
                </div>
                <div className="p-5 bg-slate-800/40 rounded-2xl border border-slate-700 text-slate-200 leading-relaxed text-base">
                  {fileMetadata.business_purpose || 'No purpose extracted. Please run re-extraction.'}
                </div>
              </section>

              <section className="space-y-6">
                <div className="flex items-center gap-2 text-indigo-400">
                  <Activity size={18} />
                  <h3 className="text-sm font-bold uppercase tracking-widest">Technical Analysis</h3>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase">
                      <Database size={14} /> Data Structures
                    </div>
                    <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs text-indigo-300 whitespace-pre-wrap max-h-80 overflow-y-auto">
                      {fileMetadata.technical_yaml || 'Structure analysis not available.'}
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase">
                      <GitBranch size={14} /> Dependencies
                    </div>
                    <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 text-xs text-slate-300 space-y-1">
                      {fileMetadata.dependencies && fileMetadata.dependencies.length > 0 ? fileMetadata.dependencies.map((dep, index) => (
                        <div key={`${dep}-${index}`} className="flex items-center gap-2">
                          <div className="w-1 h-1 bg-indigo-500 rounded-full" /> {dep}
                        </div>
                      )) : 'No external dependencies detected.'}
                    </div>
                  </div>
                </div>
              </section>

              <section className="space-y-3">
                <div className="flex items-center gap-2 text-indigo-400">
                  <Activity size={18} />
                  <h3 className="text-sm font-bold uppercase tracking-widest">Detailed Functional Logic</h3>
                </div>
                <div className="p-5 bg-slate-950/50 rounded-2xl border border-slate-800 text-slate-300 text-sm leading-relaxed">
                  {fileMetadata.functional_logic || 'Detailed logic analysis is pending.'}
                </div>
              </section>

              <section className="space-y-4">
                <div className="flex items-center gap-2 text-indigo-400">
                  <ShieldCheck size={18} />
                  <h3 className="text-sm font-bold uppercase tracking-widest">Verified Business Rules</h3>
                </div>

                <div className="grid gap-3">
                  {currentFileRules.map((rule) => (
                    <div
                      key={rule.id}
                      className={`p-4 rounded-xl border transition-all flex justify-between items-start gap-4 ${rule.status === 'VERIFIED' ? 'bg-emerald-500/5 border-emerald-500/30' : 'bg-slate-800/40 border-slate-700'}`}
                    >
                      <div className="space-y-2">
                        <span className="font-mono text-[10px] text-slate-500 font-bold">{rule.rule_id}</span>
                        <p className="text-sm text-slate-200 leading-relaxed">{rule.rule_text}</p>
                        <div className="text-[10px] text-slate-500 font-mono pt-2 border-t border-slate-700/50">
                          Ref: {rule.technical_ref || 'Derived from source'}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => updateRule(rule.id, 'VERIFIED')}
                        className={`p-2 rounded-lg transition-all ${rule.status === 'VERIFIED' ? 'bg-emerald-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-emerald-400'}`}
                        aria-label="Verify rule"
                      >
                        <CheckCircle2 size={18} />
                      </button>
                    </div>
                  ))}
                </div>
              </section>
            </motion.div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
              <Info size={40} className="text-slate-600" />
              <p className="text-sm text-slate-500">Select a file from the left to view its <br />Full Functional Dossier.</p>
            </div>
          )}
        </div>
      </div>

      <div className="glass-card flex items-center gap-3 border border-amber-500/30 bg-amber-500/10 p-4 text-amber-400 rounded-2xl">
        <AlertCircle size={20} />
        <p className="text-body-sm">
          <strong className="text-white">Human-in-the-Loop Gate:</strong> The conversion engine is locked. You must verify <span className="font-bold underline">{Math.ceil(rules.length * 0.8)}</span> rules to unlock the Java Generation phase.
        </p>
      </div>
    </div>
  );
};

export default BusinessLogic;
