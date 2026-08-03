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
  Pencil,
  Save,
  X,
  Download,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { getApiErrorDetail, ProjectAPI } from '../services/api';
import type { ProceduralFlowDetail, ProceduralFlowSummary } from '../services/api';

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
  detected_language?: string;
  agent_name?: string;
  agent_key?: string;
  fallback_used?: boolean;
  fallback_reason?: string;
  business_rules_count?: number;
}

const cleanMarkdownText = (value?: string | null, fallback = 'Not available.') => {
  const text = (value || '').trim();
  return text || fallback;
};

const yesNo = (value?: boolean) => (value ? 'Yes' : 'No');

const markdownList = (items?: string[]) => {
  if (!items || items.length === 0) return '* None detected.';
  return items.map((item) => `* ${item}`).join('\n');
};

const buildBusinessRulesMarkdown = (allRules: BusinessRule[], activeRunId: string | null) => {
  const generated = new Date().toLocaleString();
  const groups = allRules.reduce<Record<string, BusinessRule[]>>((acc, rule) => {
    const filename = rule.filename || 'Uploaded source file';
    if (!acc[filename]) acc[filename] = [];
    acc[filename].push(rule);
    return acc;
  }, {});

  const filenames = Object.keys(groups).sort((a, b) => a.localeCompare(b));
  const verified = allRules.filter((rule) => rule.status === 'VERIFIED').length;
  const rejected = allRules.filter((rule) => rule.status === 'REJECTED').length;
  const pending = allRules.filter((rule) => rule.status === 'PENDING').length;

  const lines: string[] = [
    '# Business Rules Details',
    '',
    `**Generated**: ${generated}`,
    `**Project Run ID**: ${activeRunId || 'Not selected'}`,
    `**Total Files Analyzed**: ${filenames.length}`,
    `**Total Business Rules**: ${allRules.length}`,
    `**Verified Rules**: ${verified}`,
    `**Pending Rules**: ${pending}`,
    `**Rejected Rules**: ${rejected}`,
    '',
    '---',
    '',
    '## Business Logic',
    '',
  ];

  filenames.forEach((filename) => {
    const fileRules = groups[filename];
    const metadata = fileRules[0];
    lines.push(
      `## ${filename}`,
      '',
      '### Business Purpose',
      cleanMarkdownText(metadata.business_purpose),
      '',
      '### Detailed Functional Logic',
      cleanMarkdownText(metadata.functional_logic),
      '',
      '---',
      ''
    );
  });

  lines.push('---', '', '## Business Rules', '');

  filenames.forEach((filename) => {
    const fileRules = groups[filename];
    lines.push(`### ${filename}`, '');
    fileRules.forEach((rule, index) => {
      const ruleLabel = rule.rule_id || `RULE-${index + 1}`;
      lines.push(
        `#### ${ruleLabel}`,
        '',
        `**Status:** ${rule.status}`,
        '',
        '**Rule Text:**',
        cleanMarkdownText(rule.rule_text),
        '',
        `**Technical Reference:** ${cleanMarkdownText(rule.technical_ref, 'Derived from source analysis.')}`,
        '',
        '---',
        ''
      );
    });
  });

  lines.push('## Technical Evidence', '');

  filenames.forEach((filename) => {
    const metadata = groups[filename][0];
    lines.push(
      `### ${filename}`,
      '',
      '**Program Description:** Extracted from AI analysis',
      '',
      '**Dependencies:**',
      markdownList(metadata.dependencies),
      '',
      '**Technical YAML / Evidence:**',
      '',
      '```yaml',
      cleanMarkdownText(metadata.technical_yaml, 'Structure analysis not available.'),
      '```',
      '',
      '---',
      ''
    );
  });

  return lines.join('\n');
};

const isGenericFallbackRule = (rule: BusinessRule) => {
  const text = `${rule.rule_text || ''} ${rule.technical_ref || ''}`.toLowerCase();
  return (
    text.includes('must preserve its') ||
    text.includes('preserve behavior') ||
    text.includes('during modernization') ||
    text.includes('derived from uploaded source file | confidence: low') ||
    text.includes('matching business outcome must be applied') ||
    text.includes('corresponding business outcome')
  );
};

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

const BusinessLogic = () => {
  const navigate = useNavigate();
  const runId = localStorage.getItem('active_run_id');

  const [rules, setRules] = useState<BusinessRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [autoExtracting, setAutoExtracting] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
  const [ruleDrafts, setRuleDrafts] = useState<Record<number, string>>({});
  const [progress, setProgress] = useState(0);
  const [activeSubTab, setActiveSubTab] = useState<'business' | 'programFlow'>('business');
  const [proceduralFlows, setProceduralFlows] = useState<ProceduralFlowSummary[]>([]);
  const [selectedFlow, setSelectedFlow] = useState<ProceduralFlowDetail | null>(null);
  const [flowLoading, setFlowLoading] = useState(false);

  const applyRules = (nextRules: BusinessRule[]) => {
    const normalizedRules = nextRules.map((rule) => {
      const technicalRef = rule.technical_ref || rule.technical_yaml || 'Stored technical evidence';
      return {
        ...rule,
        business_purpose: rule.business_purpose || `Stored business rules were extracted from ${rule.filename || 'the uploaded source file'}.`,
        functional_logic: rule.functional_logic || rule.rule_text || `Review the stored rule text and technical evidence. ${technicalRef}`,
      };
    });
    setProgress(nextRules.length > 0 ? 100 : 0);
    setRules(normalizedRules);
    setSelectedFile((current) => {
      if (current && normalizedRules.some((rule) => rule.filename === current)) return current;
      return normalizedRules[0]?.filename || null;
    });
  };

  useEffect(() => {
    let cancelled = false;

    const loadOrExtractRules = async () => {
      if (!runId) {
        setLoading(false);
        return;
      }

      setProgress(15);
      setLoading(true);
      try {
        const existingRules = await ProjectAPI.getBusinessRules(runId);
        if (cancelled) return;

        const hasOnlyUsableStoredRules = existingRules.length > 0 && !existingRules.some(isGenericFallbackRule);
        if (hasOnlyUsableStoredRules) {
          applyRules(existingRules);
          return;
        }

        const fileData = await ProjectAPI.listFiles(runId);
        if (cancelled) return;

        if ((fileData.files || []).length === 0) {
          applyRules([]);
          return;
        }

        setProgress(45);
        setAutoExtracting(true);
        setProgress(55);
        const extractedRules = await ProjectAPI.extractBusinessRules(runId);
        if (cancelled) return;

        setProgress(85);
        applyRules(extractedRules);
        if (extractedRules.length > 0) toast.success('Business logic loaded from uploaded files');
      } catch (e) {
        if (!cancelled) toast.error(getApiErrorDetail(e, 'Failed to load business logic'));
      } finally {
        if (!cancelled) {
          setAutoExtracting(false);
          setLoading(false);
        }
      }
    };

    void loadOrExtractRules();
    return () => { cancelled = true; };
  }, [runId]);

  useEffect(() => {
    if (!loading && !autoExtracting) return;
    const timer = window.setInterval(() => {
      setProgress((current) => Math.min(92, current + 3));
    }, 900);
    return () => window.clearInterval(timer);
  }, [loading, autoExtracting]);

  const handleExtract = async () => {
    if (!runId) return;

    setProgress(10);
    setLoading(true);
    setAutoExtracting(true);
    try {
      setProgress(55);
      const extractedRules = await ProjectAPI.extractBusinessRules(runId);
      setProgress(85);
      applyRules(extractedRules);
      toast.success('Deep analysis complete. Baseline approval is now available.');
    } catch (e) {
      toast.error(getApiErrorDetail(e, 'Extraction failed'));
    } finally {
      setAutoExtracting(false);
      setLoading(false);
    }
  };

  const loadProceduralFlows = async () => {
    if (!runId) return;

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
    }
  };

  const extractProceduralFlow = async () => {
    if (!runId) return;

    setFlowLoading(true);
    try {
      await ProjectAPI.extractProceduralFlow(runId);
      await loadProceduralFlows();
      toast.success('Program flow extracted');
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

  const updateRule = async (id: number, status: BusinessRule['status'], text?: string) => {
    try {
      await ProjectAPI.verifyRule(id, { status, ...(text !== undefined ? { text } : {}) });
      setRules((prev) => prev.map((rule) => rule.id === id ? { ...rule, status, ...(text !== undefined ? { rule_text: text } : {}) } : rule));
      toast.success(text !== undefined ? 'Rule saved' : 'Rule updated');
    } catch (e) {
      toast.error(text !== undefined ? 'Failed to save rule' : 'Failed to update rule');
    }
  };

  const startEditingRule = (rule: BusinessRule) => {
    setEditingRuleId(rule.id);
    setRuleDrafts((prev) => ({ ...prev, [rule.id]: rule.rule_text }));
  };

  const cancelEditingRule = (id: number) => {
    setEditingRuleId(null);
    setRuleDrafts((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const saveRuleText = async (rule: BusinessRule) => {
    const nextText = (ruleDrafts[rule.id] || '').trim();
    if (!nextText) {
      toast.error('Rule text cannot be empty');
      return;
    }
    await updateRule(rule.id, rule.status, nextText);
    cancelEditingRule(rule.id);
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
  const canApproveBaseline = rules.length > 0 && !loading && !autoExtracting;

  const handleDownloadBusinessRules = () => {
    if (rules.length === 0) {
      toast.error('No business rules available to download');
      return;
    }

    const markdown = buildBusinessRulesMarkdown(rules, runId);
    const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const stamp = new Date().toISOString().slice(0, 10);
    link.href = url;
    link.download = `business-rules-${runId || stamp}.md`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    toast.success('Business rules markdown downloaded');
  };

  return (
    <div className="space-y-6 min-h-screen pb-24">
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
          <div className="flex flex-wrap items-center justify-end gap-3">
          <button
            type="button"
            onClick={handleDownloadBusinessRules}
            disabled={rules.length === 0}
            className={`flex items-center gap-2 rounded-xl border px-4 py-2 text-xs font-extrabold shadow-sm transition-all ${
              rules.length > 0
                ? 'border-neutral-900 bg-neutral-950 text-white hover:-translate-y-0.5 hover:bg-neutral-800'
                : 'cursor-not-allowed border-slate-300 bg-slate-100 text-slate-400 shadow-none opacity-70'
            }`}
          >
            <Download
              size={14}
              className={rules.length > 0 ? 'text-white' : 'text-slate-400'}
            />
            <span className={rules.length > 0 ? 'text-white' : 'text-slate-400'}>
              Download MD
            </span>
          </button>
            <div className="text-right">
              <p className="text-xs font-bold text-slate-500 uppercase">Verification Progress</p>
              <p className={`text-xl font-black ${verificationPercentage >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>{verificationPercentage}%</p>
            </div>
            <button onClick={handleExtract} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold transition-all flex items-center gap-2 border border-slate-700">
              <Zap size={14} /> Re-Analyze All
            </button>
          </div>
          <button
            onClick={() => navigate('/code-generation')}
            disabled={!canApproveBaseline}
            className={`btn-glow flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all ${canApproveBaseline ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-500 cursor-not-allowed'}`}
          >
            Approve Baseline & Proceed <ArrowRight size={18} />
          </button>
        </div>
      </header>

      {(loading || autoExtracting || progress > 0) && (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
          <div className="mb-2 flex items-center justify-between text-xs font-bold uppercase text-slate-500">
            <span>{autoExtracting ? 'Extracting business logic' : loading ? 'Loading saved rules' : 'Business logic ready'}</span>
            <span className="font-mono text-indigo-300">{progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-800">
            <div className="h-full rounded-full bg-indigo-500 transition-all duration-500" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      <div className="flex gap-2 border-b border-slate-800">
        <button
          type="button"
          onClick={() => setActiveSubTab('business')}
          className={`px-4 py-3 text-sm font-bold transition-colors ${
            activeSubTab === 'business'
              ? 'border-b-2 border-indigo-400 text-indigo-300'
              : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          Business Rules
        </button>
        <button
          type="button"
          onClick={() => {
            setActiveSubTab('programFlow');
            void loadProceduralFlows();
          }}
          className={`px-4 py-3 text-sm font-bold transition-colors ${
            activeSubTab === 'programFlow'
              ? 'border-b-2 border-indigo-400 text-indigo-300'
              : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          Program Flow
        </button>
      </div>

      {activeSubTab === 'business' && (
        <>
      <div className="grid grid-cols-12 gap-6 min-h-[calc(100vh-320px)] items-start">
        <div className="col-span-4 h-[calc(100vh-320px)] overflow-hidden">
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
            <input
              type="text"
              placeholder="Search files or business logic..."
              className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </div>

          <div className="space-y-3 overflow-y-auto max-h-[calc(100vh-360px)] pr-2 custom-scrollbar">            
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
                <div className="mb-2 grid grid-cols-2 gap-2 text-[10px] uppercase tracking-wide text-slate-500">
                  <span>Lang: {files[filename][0]?.detected_language || 'Unknown'}</span>
                  <span>Fallback: {yesNo(files[filename][0]?.fallback_used)}</span>
                </div>
                <p className="mb-1 truncate text-[10px] text-slate-500">
                  Agent: {files[filename][0]?.agent_name || files[filename][0]?.agent_key || 'Unknown'}
                </p>
                <p className="text-xs text-slate-400 line-clamp-2 italic">{files[filename][0].business_purpose || 'Analysis pending...'}</p>
              </button>
            )) : (
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-6 text-center text-sm text-slate-500">No business logic extracted yet.</div>
            )} 
          </div>
        </div>

        <div className="col-span-8 min-h-0 overflow-hidden">
          <div className="glass-card h-[calc(100vh-260px)] overflow-hidden rounded-3xl border border-indigo-500/30 bg-slate-900/50">
            {selectedFile && fileMetadata ? (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex h-full flex-col"
              >
                {/* Fixed header */}
                <div className="shrink-0 border-b border-slate-800 bg-slate-900/90 p-8">
                  <div className="border-l-4 border-indigo-500 pl-4">
                    <h2 className="break-all text-3xl font-black uppercase tracking-tight text-white">
                      {selectedFile}
                    </h2>
                    <p className="mt-1 font-mono text-xs text-slate-500">
                      Source: {fileMetadata.detected_language || 'Unknown'}
                    </p>
                  </div>
                  <div className="mt-5 grid grid-cols-2 gap-3 text-xs text-slate-300 xl:grid-cols-4">
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">Agent</p>
                      <p className="mt-1 truncate font-mono text-indigo-300">{fileMetadata.agent_name || fileMetadata.agent_key || 'Unknown'}</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">Fallback</p>
                      <p className="mt-1 font-mono text-slate-200">{yesNo(fileMetadata.fallback_used)}</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">Rules Extracted</p>
                      <p className="mt-1 font-mono text-slate-200">{fileMetadata.business_rules_count || currentFileRules.length}</p>
                    </div>
                    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                      <p className="text-[10px] uppercase tracking-wide text-slate-500">Fallback Reason</p>
                      <p className="mt-1 truncate font-mono text-slate-200">{fileMetadata.fallback_reason || 'None'}</p>
                    </div>
                  </div>
                </div>

                {/* Scrollable content */}
                <div className="min-h-0 flex-1 overflow-y-auto p-8 pr-5 custom-scrollbar">
                  <div className="space-y-10">
                    <section className="space-y-3">
                      <div className="flex items-center gap-2 text-indigo-400">
                        <FileText size={18} />
                        <h3 className="text-sm font-bold uppercase tracking-widest">
                          Business Purpose
                        </h3>
                      </div>

                      <div className="rounded-2xl border border-slate-700 bg-slate-800/40 p-5 text-base leading-relaxed text-slate-200">
                        {fileMetadata.business_purpose || 'No purpose extracted. Please run re-extraction.'}
                      </div>
                    </section>

                    <section className="space-y-6">
                      <div className="flex items-center gap-2 text-indigo-400">
                        <Activity size={18} />
                        <h3 className="text-sm font-bold uppercase tracking-widest">
                          Technical Analysis
                        </h3>
                      </div>

                      <div className="grid grid-cols-1 gap-6">
                        <div className="space-y-3 min-w-0">
                          <div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-400">
                            <Database size={14} />
                            Data Structures / Technical YAML
                          </div>

                          <div className="rounded-2xl border border-slate-800 bg-slate-950">
                            <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
                              <span className="text-xs font-bold uppercase tracking-widest text-slate-500">
                                Extracted Technical Evidence
                              </span>
                              <span className="rounded-full bg-slate-800 px-2 py-1 font-mono text-[10px] text-slate-400">
                                Scrollable
                              </span>
                            </div>

                            <pre className="max-h-[560px] min-h-[360px] overflow-auto whitespace-pre-wrap break-words p-4 font-mono text-xs leading-6 text-indigo-200 custom-scrollbar">
                              {fileMetadata.technical_yaml || 'Structure analysis not available.'}
                            </pre>
                          </div>
                        </div>

                        <div className="space-y-3 min-w-0">
                          <div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-400">
                            <GitBranch size={14} />
                            Dependencies
                          </div>

                          <div className="max-h-[220px] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950 p-4 text-xs text-slate-300 custom-scrollbar">
                            {fileMetadata.dependencies && fileMetadata.dependencies.length > 0 ? (
                              <div className="space-y-2">
                                {fileMetadata.dependencies.map((dep, index) => (
                                  <div key={`${dep}-${index}`} className="flex items-center gap-2">
                                    <div className="h-1.5 w-1.5 rounded-full bg-indigo-500" />
                                    <span className="break-words">{dep}</span>
                                  </div>
                                ))}
                              </div>
                            ) : (
                              <p className="text-slate-500">No external dependencies detected.</p>
                            )}
                          </div>
                        </div>
                      </div>
                    </section>

                    <section className="space-y-3">
                      <div className="flex items-center gap-2 text-indigo-400">
                        <Activity size={18} />
                        <h3 className="text-sm font-bold uppercase tracking-widest">
                          Detailed Functional Logic
                        </h3>
                      </div>

                      <div className="max-h-[260px] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/50 p-5 text-sm leading-relaxed text-slate-300 custom-scrollbar">
                        {fileMetadata.functional_logic || 'Detailed logic analysis is pending.'}
                      </div>
                    </section>

                  </div>
                </div>
              </motion.div>
            ) : (
              <div className="flex h-full flex-col items-center justify-center space-y-4 text-center opacity-50">
                <Info size={40} className="text-slate-600" />
                <p className="text-sm text-slate-500">
                  Select a file from the left to view its <br />
                  Full Functional Dossier.
                </p>
              </div>
            )}
          </div>
        </div>

      </div>

      {selectedFile && fileMetadata && (
        <section className="glass-card rounded-3xl border border-indigo-500/30 bg-slate-900/50 p-6">
          <div className="mb-4 flex flex-col gap-3 border-b border-slate-800 pb-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-center gap-2 text-indigo-400">
              <ShieldCheck size={18} />
              <h3 className="text-sm font-bold uppercase tracking-widest">Business Rules</h3>
            </div>
            <span className="font-mono text-xs text-slate-500">{selectedFile} - {currentFileRules.length} rules</span>
          </div>

          <div className="mb-5 grid grid-cols-2 gap-3 text-xs lg:grid-cols-4">
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
              <p className="text-[10px] uppercase tracking-wide text-slate-500">Detected Language</p>
              <p className="mt-1 font-mono text-slate-200">{fileMetadata.detected_language || 'Unknown'}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
              <p className="text-[10px] uppercase tracking-wide text-slate-500">Selected Agent</p>
              <p className="mt-1 truncate font-mono text-indigo-300">{fileMetadata.agent_name || fileMetadata.agent_key || 'Unknown'}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
              <p className="text-[10px] uppercase tracking-wide text-slate-500">Fallback Used</p>
              <p className="mt-1 font-mono text-slate-200">{yesNo(fileMetadata.fallback_used)}</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3">
              <p className="text-[10px] uppercase tracking-wide text-slate-500">Rules Count</p>
              <p className="mt-1 font-mono text-slate-200">{fileMetadata.business_rules_count || currentFileRules.length}</p>
            </div>
          </div>

          <div className="max-h-[420px] overflow-y-auto pr-2 custom-scrollbar">
            <div className="grid gap-3">
              {currentFileRules.map((rule) => {
                const isEditing = editingRuleId === rule.id;

                return (
                  <div
                    key={rule.id}
                    className={`flex items-start justify-between gap-4 rounded-xl border p-4 transition-all ${
                      rule.status === 'VERIFIED'
                        ? 'border-emerald-500/30 bg-emerald-500/5'
                        : 'border-slate-700 bg-slate-800/40'
                    }`}
                  >
                    <div className="min-w-0 flex-1 space-y-2">
                      <span className="font-mono text-[10px] font-bold text-slate-500">{rule.rule_id}</span>

                      {isEditing ? (
                        <textarea
                          value={ruleDrafts[rule.id] ?? rule.rule_text}
                          onChange={(event) =>
                            setRuleDrafts((prev) => ({
                              ...prev,
                              [rule.id]: event.target.value,
                            }))
                          }
                          className="min-h-28 w-full rounded-xl border border-indigo-500 bg-slate-950 p-3 text-sm text-slate-100 outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                      ) : (
                        <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-200">{rule.rule_text}</p>
                      )}

                      <div className="border-t border-slate-700/50 pt-2 font-mono text-[10px] text-slate-500">
                        Ref: {rule.technical_ref || 'Derived from source'}
                      </div>
                    </div>

                    <div className="flex shrink-0 gap-2">
                      {isEditing ? (
                        <>
                          <button
                            type="button"
                            onClick={() => saveRuleText(rule)}
                            className="rounded-lg bg-indigo-600 p-2 text-white hover:bg-indigo-500"
                            aria-label="Save rule"
                          >
                            <Save size={18} />
                          </button>

                          <button
                            type="button"
                            onClick={() => cancelEditingRule(rule.id)}
                            className="rounded-lg bg-slate-700 p-2 text-slate-300 hover:bg-slate-600"
                            aria-label="Cancel edit"
                          >
                            <X size={18} />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => startEditingRule(rule)}
                            className="rounded-lg bg-slate-700 p-2 text-slate-300 hover:text-indigo-300"
                            aria-label="Edit rule"
                          >
                            <Pencil size={18} />
                          </button>

                          <button
                            type="button"
                            onClick={() => updateRule(rule.id, 'VERIFIED')}
                            className={`rounded-lg p-2 transition-all ${
                              rule.status === 'VERIFIED'
                                ? 'bg-emerald-600 text-white'
                                : 'bg-slate-700 text-slate-400 hover:text-emerald-400'
                            }`}
                            aria-label="Verify rule"
                          >
                            <CheckCircle2 size={18} />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </section>
      )}
        </>
      )}

      {activeSubTab === 'programFlow' && (
        <div className="grid grid-cols-12 gap-6 min-h-[calc(100vh-320px)] items-start">
          <div className="col-span-4 h-[calc(100vh-320px)] overflow-hidden">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-black text-white">Program Flow</h2>
                <p className="text-xs text-slate-500">Entry, branches, loops, data movement, calls, and exits.</p>
              </div>
              <button
                type="button"
                onClick={extractProceduralFlow}
                disabled={flowLoading}
                className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2 text-xs font-bold text-white transition-all hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {flowLoading ? <Loader2 size={14} className="animate-spin" /> : <Activity size={14} />}
                {flowLoading ? 'Extracting' : 'Extract'}
              </button>
            </div>

            <div className="space-y-3 overflow-y-auto max-h-[calc(100vh-360px)] pr-2 custom-scrollbar">
              {proceduralFlows.length > 0 ? proceduralFlows.map((flow) => (
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
                  {flow.external_calls?.length ? (
                    <p className="mt-1 truncate text-[10px] text-slate-500">Calls: {flow.external_calls.join(', ')}</p>
                  ) : null}
                  {flow.external_operations?.length ? (
                    <p className="mt-1 truncate text-[10px] text-slate-500">Ops: {flow.external_operations.join(', ')}</p>
                  ) : null}
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
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex h-full flex-col"
                >
                  <div className="shrink-0 border-b border-slate-800 bg-slate-900/90 p-8">
                    <div className="border-l-4 border-indigo-500 pl-4">
                      <h2 className="break-all text-3xl font-black uppercase tracking-tight text-white">
                        {selectedFlow.file_name}
                      </h2>
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
      )}

      <div className={`glass-card flex items-center gap-3 border p-4 rounded-2xl ${canApproveBaseline ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' : 'border-amber-500/30 bg-amber-500/10 text-amber-400'}`}>
        <AlertCircle size={20} />
        <p className="text-body-sm">
          <strong className="text-white">Human-in-the-Loop Gate:</strong> {canApproveBaseline ? 'Business logic has been extracted. You can approve the baseline now, and individual rules can still be edited or verified.' : 'Run extraction or upload source files to unlock baseline approval.'}
        </p>
      </div>
    </div>
  );
};

export default BusinessLogic;
