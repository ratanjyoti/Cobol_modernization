import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ProjectAPI, WS_BASE_URL } from '../services/api';
import { clearAnalysisWarmCache, warmAnalysisTabsWithRetry } from '../services/analysisPrefetch';

import {
  Upload, FileText, CheckCircle2, Clock,
  Layers, Loader2, Zap, Play, GitBranch,
  Activity, RotateCcw, Trash2, Languages, Target, FolderOpen
} from 'lucide-react';
import toast from 'react-hot-toast';
import PageHeader from '../components/PageHeader';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';
import { EmptyInspector } from '../components/AppPageShell';

type SourceFileRecord = {
  id: string;
  name: string;
  size: number;
  status: 'Pending' | 'Processing' | 'Analyzed';
  chunks: number;
  detectedLang?: string;
  relPath?: string;
  isValid?: boolean;
};

// Helper to determine File Type based on extension
const getFileType = (filename: string) => {
  const ext = filename.toLowerCase();
  if (ext.endsWith('.cpy')) return { label: 'Copybook', color: 'text-purple-400 bg-purple-500/10 border-purple-500/30' };
  if (ext.endsWith('.jcl')) return { label: 'JCL Script', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' };
  if (ext.endsWith('.cbl') || ext.endsWith('.cob')) return { label: 'Program', color: 'text-blue-400 bg-blue-500/10 border-blue-500/30' };
  if (ext.endsWith('.vb') || ext.endsWith('.bas') || ext.endsWith('.frm') || ext.endsWith('.cls')) return { label: 'VB.NET', color: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/30' };
  if (ext.endsWith('.cs')) return { label: 'C#', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' };
  if (ext.endsWith('.sln') || ext.endsWith('.csproj') || ext.endsWith('.vbproj')) return { label: '.NET Project', color: 'text-pink-400 bg-pink-500/10 border-pink-500/30' };
  if (ext.endsWith('.xml') || ext.endsWith('.config')) return { label: 'Config', color: 'text-slate-300 bg-slate-500/10 border-slate-500/30' };
  return { label: 'Other', color: 'text-slate-400 bg-slate-500/10 border-slate-500/30' };
};

const SUPPORTED_SOURCE_EXTENSIONS = [
  '.cbl', '.cob', '.cpy',
  '.jcl', '.sql',
  '.tln', '.tel',
  '.vb', '.bas', '.frm', '.cls',
  '.cs', '.sln', '.csproj', '.vbproj',
  '.xml', '.config',
  '.txt',
];

const IGNORED_UPLOAD_FOLDERS = new Set([
  '.git',
  'node_modules',
  'bin',
  'obj',
  '.vs',
  '.vscode',
  'dist',
  'build',
  '__pycache__',
]);

const isSupportedSourceFile = (fileName: string) => {
  const normalized = fileName.toLowerCase();
  return SUPPORTED_SOURCE_EXTENSIONS.some((ext) => normalized.endsWith(ext));
};

const shouldUploadFolderFile = (file: File) => {
  const relativePath = ((file as any).webkitRelativePath || file.name) as string;
  const parts = relativePath.replace(/\\/g, '/').split('/');

  if (parts.some((part) => IGNORED_UPLOAD_FOLDERS.has(part.toLowerCase()))) {
    return false;
  }

  return isSupportedSourceFile(file.name);
};

const STORAGE_KEYS = {
  files: 'modernizer_files',
  pipelineStatus: 'modernizer_pipeline_status',
  selectedScope: 'modernizer_selected_scope',
  sourceLang: 'modernizer_source_lang',
  targetLang: 'modernizer_target_lang',
} as const;

const MIGRATION_SCOPES = [
  { id: 'mapping', title: 'Dependency Mapping', tokens: '10k Ã¢â‚¬â€œ 25k', cost: 'Low', color: 'text-emerald-400', bg: 'bg-emerald-500/10', desc: 'Visualize architecture & connections only.' },
  { id: 'reverse', title: 'Reverse Engineering', tokens: '50k Ã¢â‚¬â€œ 120k', cost: 'Medium', color: 'text-amber-400', bg: 'bg-amber-500/10', desc: 'Extract logic, complexity & rules.' },
  { id: 'plain', title: 'Business Rules (Plain)', tokens: '80k Ã¢â‚¬â€œ 150k', cost: 'Medium', color: 'text-blue-400', bg: 'bg-blue-500/10', desc: 'Simple functional rule extraction.' },
  { id: 'ddd', title: 'Business Rules (DDD)', tokens: '150k Ã¢â‚¬â€œ 300k', cost: 'High', color: 'text-purple-400', bg: 'bg-purple-500/10', desc: 'Domain-driven microservice decomposition.' },
  { id: 'full', title: 'Full Migration', tokens: '250k Ã¢â‚¬â€œ 600k', cost: 'Very High', color: 'text-red-400', bg: 'bg-red-500/10', desc: 'End-to-end agentic pipeline.' },
];

const DISPLAY_MIGRATION_SCOPES = [
  { id: 'dependency_mapping', legacyId: 'mapping', title: 'Dependency Mapping', tokens: '10k - 25k', cost: 'Low', color: 'text-emerald-400', bg: 'bg-emerald-500/10', desc: 'Visualize architecture & connections only.' },
  { id: 'reverse_engineering', legacyId: 'reverse', title: 'Reverse Engineering', tokens: '50k - 120k', cost: 'Medium', color: 'text-amber-400', bg: 'bg-amber-500/10', desc: 'Extract logic, complexity & rules.' },
  { id: 'business_rules', legacyId: 'plain', title: 'Business Rules (Plain)', tokens: '80k - 150k', cost: 'Medium', color: 'text-blue-400', bg: 'bg-blue-500/10', desc: 'Simple functional rule extraction.' },
  { id: 'business_rules_ddd', legacyId: 'ddd', title: 'Business Rules (DDD)', tokens: '150k - 300k', cost: 'High', color: 'text-purple-400', bg: 'bg-purple-500/10', desc: 'Domain-driven microservice decomposition.' },
  { id: 'full_migration_ddd', legacyId: 'full', title: 'Full Migration', tokens: '250k - 600k', cost: 'Very High', color: 'text-red-400', bg: 'bg-red-500/10', desc: 'End-to-end agentic pipeline.' },
];

const normalizeScopeId = (scopeId: string | null) => {
  const displayMatch = DISPLAY_MIGRATION_SCOPES.find((scope) => scope.id === scopeId || scope.legacyId === scopeId);
  const legacyMatch = MIGRATION_SCOPES.find((scope) => scope.id === scopeId);
  return displayMatch?.id || legacyMatch?.id || '';
};

const SOURCE_LANGUAGES = [
  { id: 'auto', name: 'Auto-Detect Language' },
  { id: 'cobol', name: 'COBOL (Pure)' },
  { id: 'cobol-sql', name: 'COBOL + SQL' },
  { id: 'cobol-cics', name: 'COBOL + CICS' },
  { id: 'jcl', name: 'JCL' },
  { id: 'telon-batch', name: 'Telon Batch (T2B)' },
  { id: 'telon-screen', name: 'Telon Screen (T2C)' },
  { id: 'pli', name: 'PL/I' },
  { id: 'fortran', name: 'Fortran' },
  { id: 'sql', name: 'SQL' },
  { id: 'vbnet', name: 'VB.NET' },
  { id: 'csharp', name: 'C#' },
  { id: 'xml', name: 'XML' },
  { id: 'text', name: 'Text' },
  { id: 'unknown', name: 'Unknown' },
];

const TARGET_LANGUAGES = [
  { id: 'java', name: 'Java 21 (Spring Boot)' },
  { id: 'csharp', name: 'C# 12 (.NET 8)' },
  { id: 'python', name: 'Python 3.12 (FastAPI)' },
];

const LANGUAGE_LABELS: Record<string, string> = {
  cobol: 'COBOL',
  'cobol-sql': 'COBOL + SQL',
  'cobol-cics': 'COBOL + CICS',
  'cobol-sql-cics': 'COBOL + SQL + CICS',
  jcl: 'JCL',
  'telon-batch': 'Telon Batch',
  'telon-screen': 'Telon Screen',
  pli: 'PL/I',
  fortran: 'Fortran',
  sql: 'SQL',
  vbnet: 'VB.NET',
  csharp: 'C#',
  solution: 'Visual Studio Solution',
  xml: 'XML',
  text: 'Text',
  unknown: 'Unknown',
};

const normalizeLanguageId = (lang?: string) => {
  const normalized = (lang || '').trim().toLowerCase();
  if (!normalized) return 'unknown';
  if (SOURCE_LANGUAGES.some((item) => item.id === normalized)) return normalized;
  const labelMatch = Object.entries(LANGUAGE_LABELS).find(([, label]) => label.toLowerCase() === normalized);
  return labelMatch?.[0] || normalized;
};

const formatLanguageName = (lang?: string) => LANGUAGE_LABELS[normalizeLanguageId(lang)] || lang || 'Unknown';

interface SourceFilesProps {
  embedded?: boolean;
}

const SourceFiles = ({ embedded = false }: SourceFilesProps) => {
  const navigate = useNavigate();
  
  // Input Refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const localRepoInputRef = useRef<HTMLInputElement>(null);
  const queuedDetectionKeys = useRef<Set<string>>(new Set());

  const [inputMethod, setInputMethod] = useState<'file' | 'local' | 'github'>('file');
  const [githubUrl, setGithubUrl] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [files, setFiles] = useState<SourceFileRecord[]>([]);
  const [selectedScope, setSelectedScope] = useState(() => normalizeScopeId(localStorage.getItem(STORAGE_KEYS.selectedScope)));
  const [sourceLang, setSourceLang] = useState(localStorage.getItem(STORAGE_KEYS.sourceLang) || 'auto');
  const [targetLang, setTargetLang] = useState(localStorage.getItem(STORAGE_KEYS.targetLang) || 'java');
  const [isLaunching, setIsLaunching] = useState(false);
  const [isReadingRepo, setIsReadingRepo] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isClearingFiles, setIsClearingFiles] = useState(false);
  const [pipelineActive, setPipelineActive] = useState(() => localStorage.getItem(STORAGE_KEYS.pipelineStatus) === 'active');
  const [savingLanguageIds, setSavingLanguageIds] = useState<Set<string>>(new Set());
  const [languageCorrectionIds, setLanguageCorrectionIds] = useState<Set<string>>(new Set());
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);
  const uploadBusyRef = useRef(false);
  
  const runId = localStorage.getItem('active_run_id');
  const selectedFile = useMemo(() => files.find((file) => file.id === selectedFileId) || null, [files, selectedFileId]);

  const refreshAnalysisTabs = () => {
    if (!runId) return;
    clearAnalysisWarmCache(runId);
    warmAnalysisTabsWithRetry(runId);
  };

  // HELPER: Ensures mapping backend data to frontend state correctly across all handlers
  const mapBackendFiles = (backendFiles: any[]) => {
    return backendFiles.map((f) => ({
      id: f.id,
      name: f.filename || f.name,
      size: f.size || 0,
      status: f.status === 'PENDING_CONFIRMATION' ? 'Pending' : 'Analyzed',
      chunks: f.chunks || 1,
      detectedLang: f.lang || f.detected_lang,
      relPath: f.filepath || f.rel_path,
      isValid: f.is_valid ?? (f.status === 'CONFIRMED' || f.status === 'Analyzed'),
    }));
  };

  useEffect(() => {
    let active = true;

    const loadExistingFiles = async () => {
      if (!runId) {
        setFiles([]);
        queuedDetectionKeys.current.clear();
        return;
      }

      try {
        const response = await ProjectAPI.listFiles(runId);
        if (!active) return;
        const mapped = mapBackendFiles(response.files || []);
        setFiles(mapped);
        setSelectedFileId((current) => current && mapped.some((file) => file.id === current) ? current : mapped[0]?.id || null);
      } catch (error: any) {
        if (active) {
          toast.error(error.response?.data?.detail || 'Unable to load uploaded files for this project');
        }
      }
    };

    loadExistingFiles();

    return () => {
      active = false;
    };
  }, [runId]);

  const enqueueLanguageDetections = (mappedFiles: any[]) => {
    if (sourceLang !== 'auto') return;

    setFiles((prev) => prev.map((file) => {
      const detected = mappedFiles.find((item) => {
        const itemName = item.filename || item.name || item.file;
        const itemPath = item.filepath || item.rel_path;
        return (item.id && item.id === file.id) || itemName === file.name || (itemPath && itemPath === file.relPath);
      });

      if (!detected) return file;
      const lang = detected.lang || detected.detected_lang || detected.suggested_lang || file.detectedLang || 'UNKNOWN';
      const key = `${file.id || file.name}:${file.relPath || ''}:${lang}`;
      if (queuedDetectionKeys.current.has(key)) return file;
      queuedDetectionKeys.current.add(key);

      return {
        ...file,
        detectedLang: lang,
        isValid: detected.is_valid ?? detected.isValid ?? file.isValid,
      };
    }));
  };

  const clearAllFiles = async () => {
    if (!runId) {
      toast.error("No active project found");
      return;
    }
    if (pipelineActive) {
      toast.error("Cannot clear files while the pipeline is active.");
      return;
    }
    if (files.length === 0) {
      toast.error("No uploaded files to clear.");
      return;
    }
    if (!window.confirm("Clear all uploaded files for this run?")) return;

    setIsClearingFiles(true);
    try {
      await ProjectAPI.clearAllFiles(runId);
      setFiles([]);
      setSelectedFileId(null);
      queuedDetectionKeys.current.clear();
      localStorage.removeItem(STORAGE_KEYS.files);
      clearAnalysisWarmCache(runId);
      toast.success("All uploaded files cleared");
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Failed to clear uploaded files");
    } finally {
      setIsClearingFiles(false);
    }
  };

  useEffect(() => {
    uploadBusyRef.current = isUploading || isReadingRepo;
  }, [isUploading, isReadingRepo]);

  const saveFileLanguage = async (file: SourceFileRecord, lang: string) => {
    if (!runId) {
      toast.error('No active project found');
      return;
    }
    const normalizedLang = normalizeLanguageId(lang);
    if (!normalizedLang || normalizedLang === 'auto') {
      toast.error('Select a valid language');
      return;
    }

    setSavingLanguageIds((prev) => new Set(prev).add(file.id));
    try {
      const numericFileId = /^\d+$/.test(String(file.id || '')) ? String(file.id) : undefined;
      const response = await ProjectAPI.confirmLanguage({
        run_id: runId,
        filename: file.name,
        lang: normalizedLang,
        ...(numericFileId ? { file_id: numericFileId } : {}),
        ...(file.relPath ? { filepath: file.relPath } : {}),
      });

      const savedFile = response?.file;
      setFiles((prev) => prev.map((item) => item.id === file.id
        ? {
            ...item,
            status: 'Analyzed',
            detectedLang: savedFile?.detected_lang || normalizedLang,
            relPath: savedFile?.filepath || item.relPath,
            isValid: savedFile?.is_valid ?? true,
          }
        : item
      ));
      setLanguageCorrectionIds((prev) => {
        const next = new Set(prev);
        next.delete(file.id);
        return next;
      });
      refreshAnalysisTabs();
      toast.success(`Language saved for ${file.name}`);
    } catch (e: any) {
      const detail = e.response?.data?.detail || e.message || 'Failed to save language preference';
      toast.error(detail);
    } finally {
      setSavingLanguageIds((prev) => {
        const next = new Set(prev);
        next.delete(file.id);
        return next;
      });
    }
  };

  const markLanguageIncorrect = (fileId: string) => {
    setLanguageCorrectionIds((prev) => new Set(prev).add(fileId));
    setFiles((prev) => prev.map((file) => file.id === fileId ? { ...file, isValid: false } : file));
  };

  const removeFile = async (id: string) => {
    if (pipelineActive) {
      toast.error("Cannot delete files while the pipeline is active.");
      return;
    }
    setFiles(prev => {
      const next = prev.filter(f => f.id !== id);
      setSelectedFileId((current) => current === id ? next[0]?.id || null : current);
      return next;
    });
    toast.success("File removed from queue");
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = e.target.files;
    if (!uploadedFiles || !runId) {
      toast.error("Please start a project first!");
      return;
    }
    setIsUploading(true);
    try {
      for (const file of Array.from(uploadedFiles)) {
        const fileName = file.name.toLowerCase();
        if (fileName.endsWith('.zip')) {
          const zipFormData = new FormData();
          zipFormData.append('run_id', runId);
          zipFormData.append('zip_file', file);
          const zipData = await ProjectAPI.uploadZip(zipFormData);
          if (zipData && zipData.mapped_files) {
            const backendFiles = mapBackendFiles(zipData.mapped_files);
            setFiles(prev => [...prev, ...backendFiles]);
            setSelectedFileId((current) => current || backendFiles[0]?.id || null);
            enqueueLanguageDetections(zipData.mapped_files);
            refreshAnalysisTabs();
            toast.success(`Extracted ${backendFiles.length} files`);
          }
        } else if (isSupportedSourceFile(fileName)) {
          const fileFormData = new FormData();
          fileFormData.append('run_id', runId);
          fileFormData.append('files', file);
          const fileResponse = await ProjectAPI.uploadFiles(fileFormData);
          const uploadedRecords = fileResponse.mapped_files || [];
          const backendFiles = mapBackendFiles(uploadedRecords);
          setFiles(prev => [...prev, ...backendFiles]);
            setSelectedFileId((current) => current || backendFiles[0]?.id || null);
          enqueueLanguageDetections(uploadedRecords);
          refreshAnalysisTabs();
          toast.success(`Uploaded ${file.name}`);
        } else {
          toast.error(`Unsupported file type: ${file.name}`);
        }
      }
    } catch (error: any) {
      console.error("Detailed Error:", error);
      const serverMessage = error.response?.data?.detail || "Connection timed out or file too large";
      toast.error(`Upload failed: ${serverMessage}`);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleFolderUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = e.target.files;
    if (!uploadedFiles || !runId) return;

    const sourceFiles = Array.from(uploadedFiles).filter(shouldUploadFolderFile);
    if (sourceFiles.length === 0) {
      toast.error("No supported source files found in that folder");
      if (folderInputRef.current) folderInputRef.current.value = '';
      if (localRepoInputRef.current) localRepoInputRef.current.value = '';
      return;
    }

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('run_id', runId);

      sourceFiles.forEach((file) => {
        formData.append('files', file);
        formData.append('paths', ((file as any).webkitRelativePath || file.name) as string);
      });

      const response = await ProjectAPI.uploadFolder(formData);
      const backendFiles = mapBackendFiles(response.mapped_files || []);
      
      setFiles(prev => [...prev, ...backendFiles]);
            setSelectedFileId((current) => current || backendFiles[0]?.id || null);
      enqueueLanguageDetections(response.mapped_files || []);
      refreshAnalysisTabs();
      toast.success(`Local repository ingested: ${backendFiles.length} files`);
    } catch (error: any) {
      console.error(error);
      toast.error(error.response?.data?.detail || "Folder upload failed. Try a smaller folder or ZIP.");
    } finally {
      setIsUploading(false);
      if (folderInputRef.current) folderInputRef.current.value = '';
      if (localRepoInputRef.current) localRepoInputRef.current.value = '';
    }
  };

  const handleGithubIngest = async () => {
    if (!githubUrl.trim() || !runId) {
      toast.error("Please enter a GitHub repository URL");
      return;
    }

    setIsReadingRepo(true);
    try {
      const formData = new FormData();
      formData.append('run_id', runId);
      formData.append('repo_url', githubUrl.trim());
      if (githubToken) {
        formData.append('github_token', githubToken.trim());
      }

      const response = await ProjectAPI.ingestGithub(formData);
      const backendFiles = mapBackendFiles(response.mapped_files || []);

      setFiles(prev => [...prev, ...backendFiles]);
            setSelectedFileId((current) => current || backendFiles[0]?.id || null);
      enqueueLanguageDetections(response.mapped_files || []);
      refreshAnalysisTabs();
      toast.success(`Successfully ingested ${backendFiles.length} files from GitHub`);
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || "GitHub ingestion failed";
      toast.error(errorMsg);
    } finally {
      setIsReadingRepo(false);
    }
  };

  const launchPipeline = async () => {
    if (!selectedScope) {
      toast.error("Please select a migration scope first!");
      return;
    }
    if (!runId) {
      toast.error("No active project found!");
      return;
    }
    setIsLaunching(true);
    const formData = new FormData();
    formData.append('run_id', runId);
    formData.append('source_lang', sourceLang);
    formData.append('target_lang', targetLang);
    formData.append('scope', selectedScope);
    try {
      await ProjectAPI.launchPipeline(formData);
      setPipelineActive(true);
      localStorage.setItem(STORAGE_KEYS.pipelineStatus, 'active');
      toast.success("Pipeline initialized!");
      navigate('/mission-control');
    } catch (error) {
      toast.error("Pipeline launch failed");
    } finally {
      setIsLaunching(false);
    }
  };

  const resetPipeline = () => {
    localStorage.removeItem(STORAGE_KEYS.pipelineStatus);
    localStorage.removeItem(STORAGE_KEYS.selectedScope);
    setPipelineActive(false);
    setFiles(prev => prev.map(f => ({ ...f, status: 'Pending' })));
    setSelectedScope('');
    toast.success("Pipeline reset");
  };

  return (
    <div className={embedded ? 'enterprise-page pt-0' : 'enterprise-page'}>
      {!embedded && (
      <div className="enterprise-page-header">
        <PageHeader
        title="Source Files"
        description="Configure migration mapping, ingest source code, confirm language detection, and launch the analysis pipeline."
        meta={pipelineActive ? <StatusBadge status="Running" /> : <StatusBadge status="Pending" pulse={false} />}
        action={(
          <button onClick={resetPipeline} className="btn-secondary flex items-center gap-2 px-4 py-3" title="Reset Pipeline">
            <RotateCcw size={18} /> Reset Pipeline
          </button>
        )}
      />
      </div>
      )}

      <div className="enterprise-split-pane source-files-split">
        <section className="enterprise-explorer-panel">
          <div className="space-y-8 pr-1">
      {/* SECTION 1: CONFIGURATION */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
        <SectionLabel>Project Configuration</SectionLabel>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="glass-card p-6 rounded-3xl border-slate-800 bg-slate-900/50 space-y-4">
            <div className="flex items-center gap-2 text-indigo-400 text-sm font-bold uppercase tracking-widest">
              <Languages size={16} /> Source Language
            </div>
            <select 
              value={sourceLang} 
              onChange={(e) => setSourceLang(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 appearance-none"
            >
              {SOURCE_LANGUAGES.map(lang => <option key={lang.id} value={lang.id}>{lang.name}</option>)}
            </select>
            <p className="text-[10px] text-slate-500 italic leading-relaxed">
              Auto-Detect will prompt you during upload if a specific dialect is found.
            </p>
          </div>

          <div className="glass-card p-6 rounded-3xl border-slate-800 bg-slate-900/50 space-y-4">
            <div className="flex items-center gap-2 text-emerald-400 text-sm font-bold uppercase tracking-widest">
              <Target size={16} /> Target Platform
            </div>
            <select 
              value={targetLang} 
              onChange={(e) => setTargetLang(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-emerald-500 appearance-none"
            >
              {TARGET_LANGUAGES.map(lang => <option key={lang.id} value={lang.id}>{lang.name}</option>)}
            </select>
            <p className="text-[10px] text-slate-500 italic leading-relaxed">
              The architecture your legacy code will be modernized into.
            </p>
          </div>
        </div>

        {/* )} */}
      </motion.div>

      {files.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="source-guided-path rocket-card p-6"
        >
          <div className="rocket-panel-header mb-5">
            <div>
              <SectionLabel>Guided Path</SectionLabel>
              <h2>Next steps after upload</h2>
              <p>{files.length} file{files.length === 1 ? '' : 's'} uploaded. Continue through the modernization flow in order.</p>
            </div>
          </div>

          <div className="source-guided-actions">
            <button type="button" onClick={() => navigate('/discovery')} className="source-guided-action">
              <span className="rocket-flow-index">01</span>
              <span className="rocket-flow-icon"><GitBranch size={22} /></span>
              <span>
                <strong>See dependency maps</strong>
                <small>Open system discovery and review file relationships.</small>
              </span>
            </button>

            <button type="button" onClick={() => navigate('/business-logic')} className="source-guided-action">
              <span className="rocket-flow-index">02</span>
              <span className="rocket-flow-icon"><Activity size={22} /></span>
              <span>
                <strong>Business logic analysis</strong>
                <small>Extract and validate rules from uploaded source code.</small>
              </span>
            </button>

            <button
              type="button"
              onClick={pipelineActive ? () => navigate('/mission-control') : launchPipeline}
              disabled={isLaunching}
              className="source-guided-action source-guided-action-primary"
            >
              <span className="rocket-flow-index">03</span>
              <span className="rocket-flow-icon">{isLaunching ? <Loader2 className="animate-spin" size={22} /> : <Play size={22} fill="currentColor" />}</span>
              <span>
                <strong>{pipelineActive ? 'View migration progress' : 'Start migration'}</strong>
                <small>{pipelineActive ? 'Open Mission Control for the active pipeline.' : 'Launch the modernization pipeline when ready.'}</small>
              </span>
            </button>
          </div>
        </motion.div>
      )}
      {/* SECTION 2: INGESTION */}
      <div className="space-y-6">
        <SectionLabel>Source Code Ingestion</SectionLabel>

        <div className="flex justify-center">
          <div className="flex p-1 bg-slate-950 rounded-xl border border-slate-800 w-full max-w-md">
            <button onClick={() => setInputMethod('file')} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${inputMethod === 'file' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}><Upload size={14}/> Local Upload</button>
            <button onClick={() => setInputMethod('local')} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${inputMethod === 'local' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}><GitBranch size={14}/> Local Git</button>
            <button onClick={() => setInputMethod('github')} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${inputMethod === 'github' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}><GitBranch size={14}/> GitHub URL</button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6">
          {inputMethod === 'file' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div 
                onClick={() => fileInputRef.current?.click()}
                className="relative group border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-3xl p-12 transition-all text-center bg-slate-900/30 cursor-pointer"
              >
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  multiple 
                  style={{ display: 'none' }} 
                  onChange={handleFileUpload} 
                  accept=".cbl,.cob,.cpy,.jcl,.sql,.tln,.tel,.vb,.bas,.frm,.cls,.cs,.sln,.csproj,.vbproj,.xml,.config,.txt,.zip" 
                />
                <div className="flex flex-col items-center gap-4 pointer-events-none"> 
                  <div className={`p-4 rounded-full transition-colors ${isUploading ? 'bg-indigo-500 text-white' : 'bg-slate-800 text-slate-400 group-hover:text-indigo-400'}`}>
                    {isUploading ? <Loader2 className="animate-spin" size={32} /> : <Upload size={32} />}
                  </div>
                  <div className="space-y-1">
                    <p className="text-lg font-medium text-slate-300">Upload Files or ZIP</p>
                    <p className="text-sm text-slate-500">Supports COBOL, JCL, SQL, VB.NET, C#, and ZIP</p>
                  </div>
                </div>
              </div>

              <div 
                onClick={() => folderInputRef.current?.click()}
                className="relative group border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-3xl p-12 transition-all text-center bg-slate-900/30 cursor-pointer"
              >
                <input 
                  type="file" 
                  ref={folderInputRef}
                  {...({ webkitdirectory: "true" } as any)}
                  multiple 
                  style={{ display: 'none' }} 
                  onChange={handleFolderUpload} 
                />
                <div className="flex flex-col items-center gap-4 pointer-events-none"> 
                  <div className={`p-4 rounded-full transition-colors ${isUploading ? 'bg-indigo-500 text-white' : 'bg-slate-800 text-slate-400 group-hover:text-indigo-400'}`}>
                    {isUploading ? <Loader2 className="animate-spin" size={32} /> : <FolderOpen size={32} />}
                  </div>
                  <div className="space-y-1">
                    <p className="text-lg font-medium text-slate-300">Upload Local Folder</p>
                    <p className="text-sm text-slate-500">Preserves directory structure</p>
                  </div>
                </div>
              </div>
            </div>
          ) : inputMethod === 'local' ? (
            <div className="glass-card p-8 rounded-3xl border-slate-800 bg-slate-900/50 flex flex-col md:flex-row gap-6 items-center">
              <input
                type="file"
                ref={localRepoInputRef}
                {...({ webkitdirectory: "true" } as any)}
                multiple
                style={{ display: 'none' }}
                onChange={handleFolderUpload}
              />
              <div className="flex-1 space-y-2 w-full">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-widest">
                  <GitBranch size={16} /> Local Git Repository
                </div>
                <p className="text-sm text-slate-400">
                  Select a repository folder from this device. Supported source files will be uploaded while build output and Git internals are skipped.
                </p>
              </div>
              <button onClick={() => localRepoInputRef.current?.click()} disabled={isUploading} className="w-full md:w-auto px-8 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50">
                {isUploading ? <><Loader2 className="animate-spin" size={18}/> Uploading...</> : <><FolderOpen size={18}/> Select Folder</>}
              </button>
            </div>
          ) : (
            <div className="glass-card p-8 rounded-3xl border-slate-800 bg-slate-900/50 flex flex-col md:flex-row gap-4 items-end">
              <div className="flex-1 space-y-3 w-full">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">GitHub Repository URL</label>
                <div className="relative">
                  <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                  <input
                    type="text"
                    placeholder="https://github.com/username/repository"
                    className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                  />
                </div>
              </div>
              <div className="flex-1 space-y-3 w-full">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">GitHub Token (Optional)</label>
                <div className="relative">
                  <Target className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                  <input
                    type="password"
                    placeholder="ghp_xxxxxxxxxxxx"
                    className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                    value={githubToken}
                    onChange={(e) => setGithubToken(e.target.value)}
                  />
                </div>
              </div>
              <button onClick={handleGithubIngest} disabled={isReadingRepo} className="w-full md:w-auto px-8 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50">
                {isReadingRepo ? <><Loader2 className="animate-spin" size={18}/> Cloning...</> : <><Zap size={18}/> Ingest Repo</>}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* SECTION 3: FILE REVIEW & LAUNCH */}
      <div className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-indigo-400 text-sm font-bold uppercase tracking-widest">
            <FileText size={16} /> Review & Launch
          </div>
          <button
            onClick={clearAllFiles}
            disabled={pipelineActive || isClearingFiles || files.length === 0}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isClearingFiles ? <Loader2 className="animate-spin" size={14} /> : <Trash2 size={14} />}
            Clear All Files
          </button>
        </div>
        
        <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-800/50 text-slate-300 text-xs uppercase tracking-wider">
              <tr className="border-b border-slate-700">
                <th className="p-4 font-semibold">File & Path</th>
                <th className="p-4 font-semibold">Type</th>
                <th className="p-4 font-semibold">Language</th>
                <th className="p-4 font-semibold">Validity</th>
                <th className="p-4 font-semibold">Size</th>
                <th className="p-4 font-semibold">Status</th>
                <th className="p-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="text-slate-300">
              {files.map(file => {
                const type = getFileType(file.name);
                return (
                  <tr key={file.id} onClick={() => setSelectedFileId(file.id)} className={`cursor-pointer border-t border-slate-700 transition-colors ${selectedFileId === file.id ? 'source-file-row-active' : 'hover:bg-slate-800/30'}`}>
                    <td className="p-4">
                      <div className="flex flex-col whitespace-normal break-words max-w-xs">
                        <div className="flex items-center gap-2 font-medium text-white">
                          <FileText size={14} className="text-indigo-400" />
                          {file.name}
                        </div>
                        {file.relPath && (
                          <span className="text-[10px] text-slate-500 font-mono">
                            {file.relPath}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-4">
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${type.color}`}>
                        {type.label}
                      </span>
                    </td>
                    <td className="p-4 min-w-[220px]">
                      <div className="space-y-2">
                        <select
                          value={normalizeLanguageId(file.detectedLang)}
                          onChange={(event) => saveFileLanguage(file, event.target.value)}
                          disabled={pipelineActive || savingLanguageIds.has(file.id)}
                          className={`w-full rounded-lg border px-3 py-2 text-sm font-semibold outline-none transition-all ${languageCorrectionIds.has(file.id) ? 'border-amber-500 bg-amber-500/10' : 'border-slate-800 bg-slate-950'} disabled:cursor-not-allowed disabled:opacity-60`}
                        >
                          {SOURCE_LANGUAGES.filter((lang) => lang.id !== 'auto').map((lang) => (
                            <option key={lang.id} value={lang.id}>{lang.name}</option>
                          ))}

                        </select>
                        <div className="text-[10px] text-slate-500">
                          {file.isValid === true ? 'Saved language' : `Detected: ${formatLanguageName(file.detectedLang)}`}
                        </div>
                      </div>
                    </td>
                    <td className="p-4 min-w-[190px]">
                      {savingLanguageIds.has(file.id) ? (
                        <div className="flex items-center gap-2 text-amber-400 text-xs font-bold">
                          <Loader2 size={14} className="animate-spin" /> Saving
                        </div>
                      ) : file.isValid === true ? (
                        <div className="flex items-center gap-2 text-emerald-400 text-xs font-bold">
                          <CheckCircle2 size={14} /> Validated
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => saveFileLanguage(file, normalizeLanguageId(file.detectedLang))}
                            disabled={pipelineActive}
                            className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-1.5 text-xs font-bold text-emerald-500 transition-all hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            Yes
                          </button>
                          <button
                            type="button"
                            onClick={() => markLanguageIncorrect(file.id)}
                            disabled={pipelineActive}
                            className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 text-xs font-bold text-amber-500 transition-all hover:bg-amber-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            No
                          </button>
                        </div>
                      )}
                    </td>
                    <td className="p-4 text-sm font-mono text-slate-400">
                      {file.size} LLOC
                    </td>
                    <td className="p-4">
                      {file.status === 'Processing' ? (
                        <div className="flex items-center gap-2 text-amber-400 text-xs font-medium">
                          <Loader2 size={12} className="animate-spin" /> Processing
                        </div>
                      ) : file.status === 'Analyzed' ? (
                        <div className="flex items-center gap-2 text-emerald-400 text-xs font-medium">
                          <CheckCircle2 size={12} /> Confirmed
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 text-slate-500 text-xs font-medium">
                          <Clock size={12} /> Pending
                        </div>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <button onClick={() => removeFile(file.id)} className={`p-2 rounded-lg transition-colors ${pipelineActive ? 'text-slate-700 cursor-not-allowed' : 'text-slate-500 hover:text-red-400 hover:bg-red-500/10'}`}>
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                );
              })}
              {files.length === 0 && (
                <tr className="border-t border-slate-700">
                  <td colSpan={7} className="p-12 text-center text-slate-500 italic">
                    No source code ingested. Upload files above to begin.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>      </div>
          </div>
        </section>

        <aside className="enterprise-inspector-panel">
          {selectedFile ? (
            <div className="enterprise-panel-card space-y-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <SectionLabel>File Inspector</SectionLabel>
                  <h3 className="text-card-title mt-2 truncate">{selectedFile.name}</h3>
                  <p className="rocket-muted mt-1 break-all font-mono text-xs">{selectedFile.relPath || selectedFile.name}</p>
                </div>
                <StatusBadge status={selectedFile.status} />
              </div>

              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-xl border border-slate-800/40 p-3">
                  <span className="rocket-label">Type</span>
                  <p className="mt-1 font-bold text-[var(--corporate-text)]">{getFileType(selectedFile.name).label}</p>
                </div>
                <div className="rounded-xl border border-slate-800/40 p-3">
                  <span className="rocket-label">Size</span>
                  <p className="mt-1 font-mono font-bold text-[var(--corporate-text)]">{selectedFile.size} LLOC</p>
                </div>
                <div className="rounded-xl border border-slate-800/40 p-3">
                  <span className="rocket-label">Language</span>
                  <p className="mt-1 font-bold text-[var(--corporate-text)]">{formatLanguageName(selectedFile.detectedLang)}</p>
                </div>
                <div className="rounded-xl border border-slate-800/40 p-3">
                  <span className="rocket-label">Validity</span>
                  <p className={selectedFile.isValid ? 'mt-1 font-bold text-emerald-500' : 'mt-1 font-bold text-amber-500'}>{selectedFile.isValid ? 'Validated' : 'Needs review'}</p>
                </div>
              </div>

              <div className="space-y-3">
                <button onClick={() => navigate('/discovery')} className="rocket-secondary-btn w-full justify-center">View dependency map</button>
                <button onClick={() => navigate('/business-logic')} className="rocket-secondary-btn w-full justify-center">Analyze business logic</button>
              </div>
            </div>
          ) : (
            <EmptyInspector title="Select a source file" description="Choose a file from Step 3 to inspect language, status, validity, and next analysis actions." />
          )}
        </aside>
      </div>

      <div className="enterprise-action-bar">
        {pipelineActive ? (
          <button onClick={() => navigate('/mission-control')} className="px-10 py-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-full font-black transition-all flex items-center gap-3">
            <Activity size={20} /> View Pipeline Progress
          </button>
        ) : (
          <button
            onClick={launchPipeline}
            disabled={isLaunching || files.length === 0}
            className="px-10 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full font-black transition-all flex items-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLaunching ? <><Loader2 className="animate-spin" size={20} /> Initializing...</> : <><Play fill="currentColor" size={20} /> Launch Migration Pipeline</>}
          </button>
        )}
      </div>
    </div>
  );
};

export default SourceFiles;















