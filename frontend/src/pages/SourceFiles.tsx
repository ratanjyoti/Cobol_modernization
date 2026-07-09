import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ProjectAPI, WS_BASE_URL } from '../services/api';
import { clearAnalysisWarmCache, warmAnalysisTabs } from '../services/analysisPrefetch';

import {
  Upload, FileText, CheckCircle2, Clock,
  Layers, Loader2, Zap, Play, GitBranch,
  Activity, RotateCcw, Trash2, Languages, Target, XCircle, FolderOpen, AlertCircle
} from 'lucide-react';
import toast from 'react-hot-toast';
import PageHeader from '../components/PageHeader';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';

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

type DetectionAlert = {
  file: string;
  lang: string;
  id?: string;
  filepath?: string;
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
  { id: 'mapping', title: 'Dependency Mapping', tokens: '10k – 25k', cost: 'Low', color: 'text-emerald-400', bg: 'bg-emerald-500/10', desc: 'Visualize architecture & connections only.' },
  { id: 'reverse', title: 'Reverse Engineering', tokens: '50k – 120k', cost: 'Medium', color: 'text-amber-400', bg: 'bg-amber-500/10', desc: 'Extract logic, complexity & rules.' },
  { id: 'plain', title: 'Business Rules (Plain)', tokens: '80k – 150k', cost: 'Medium', color: 'text-blue-400', bg: 'bg-blue-500/10', desc: 'Simple functional rule extraction.' },
  { id: 'ddd', title: 'Business Rules (DDD)', tokens: '150k – 300k', cost: 'High', color: 'text-purple-400', bg: 'bg-purple-500/10', desc: 'Domain-driven microservice decomposition.' },
  { id: 'full', title: 'Full Migration', tokens: '250k – 600k', cost: 'Very High', color: 'text-red-400', bg: 'bg-red-500/10', desc: 'End-to-end agentic pipeline.' },
];

const SOURCE_LANGUAGES = [
  { id: 'auto', name: '✨ Auto-Detect Language' },
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

const formatLanguageName = (lang?: string) => LANGUAGE_LABELS[(lang || '').toLowerCase()] || lang || 'Unknown';

const SourceFiles = () => {
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
  const [selectedScope, setSelectedScope] = useState(localStorage.getItem(STORAGE_KEYS.selectedScope) || '');
  const [sourceLang, setSourceLang] = useState(localStorage.getItem(STORAGE_KEYS.sourceLang) || 'auto');
  const [targetLang, setTargetLang] = useState(localStorage.getItem(STORAGE_KEYS.targetLang) || 'java');
  const [isLaunching, setIsLaunching] = useState(false);
  const [isReadingRepo, setIsReadingRepo] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isClearingFiles, setIsClearingFiles] = useState(false);
  const [pipelineActive, setPipelineActive] = useState(() => localStorage.getItem(STORAGE_KEYS.pipelineStatus) === 'active');
  const [detectionAlert, setDetectionAlert] = useState<DetectionAlert | null>(null);
  const [pendingDetections, setPendingDetections] = useState<DetectionAlert[]>([]);
  const uploadBusyRef = useRef(false);
  
  const runId = localStorage.getItem('active_run_id');

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
      isValid: f.is_valid,
    }));
  };

  const enqueueLanguageDetections = (mappedFiles: any[]) => {
    if (sourceLang !== 'auto') return;

    const detections = mappedFiles
      .map((file) => ({
        file: file.filename || file.name,
        lang: file.lang || file.detected_lang || 'UNKNOWN',
        id: file.id,
        filepath: file.filepath || file.rel_path,
        isValid: file.is_valid ?? file.isValid,
      }))
      .filter((item) => {
        if (!item.file || !item.lang || item.lang === 'UNKNOWN' || item.isValid === false) return false;
        const key = `${item.id || item.file}:${item.filepath || ''}:${item.lang}`;
        if (queuedDetectionKeys.current.has(key)) return false;
        queuedDetectionKeys.current.add(key);
        return true;
      });

    if (detections.length === 0) return;

    setDetectionAlert((current) => {
      if (current) {
        setPendingDetections((prev) => [...prev, ...detections]);
        return current;
      }

      const [nextDetection, ...remaining] = detections;
      if (remaining.length > 0) {
        setPendingDetections((prev) => [...prev, ...remaining]);
      }
      return nextDetection;
    });
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
      setDetectionAlert(null);
      setPendingDetections([]);
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

  const showNextDetection = () => {
    setPendingDetections((prev) => {
      const [nextDetection, ...remaining] = prev;
      setDetectionAlert(nextDetection || null);
      return remaining;
    });
  };

  useEffect(() => {
    if (!runId) return;
    const socket = new WebSocket(`${WS_BASE_URL}/discovery/ws/${runId}`);
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === 'LANGUAGE_DETECTED' && !uploadBusyRef.current) {
        enqueueLanguageDetections([{ filename: data.file, lang: data.suggested_lang, is_valid: data.is_valid }]);
      }
    };
    return () => socket.close();
  }, [runId, sourceLang]);

  const [isCorrecting, setIsCorrecting] = useState(false);
  const [isConfirmingLanguage, setIsConfirmingLanguage] = useState(false);
  const [selectedManualLang, setSelectedManualLang] = useState('');

  const confirmLanguage = async (confirmed: boolean, manualLang?: string) => {
    if (!runId || !detectionAlert || isConfirmingLanguage) return;

    const finalLang = confirmed ? detectionAlert.lang : (manualLang || 'UNKNOWN');

    setIsConfirmingLanguage(true);
    try {
      await ProjectAPI.confirmLanguage({
        run_id: runId,
        filename: detectionAlert.file,
        lang: finalLang,
        file_id: detectionAlert.id,
        filepath: detectionAlert.filepath,
      });
      toast.success(`Updated ${detectionAlert.file} to ${finalLang}`);
      setFiles(prev => prev.map(file => file.name === detectionAlert.file ? { ...file, status: 'Analyzed', detectedLang: finalLang } : file));
      refreshAnalysisTabs();
      setIsCorrecting(false);
      setSelectedManualLang('');
      showNextDetection();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || "Failed to save language preference");
    } finally {
      setIsConfirmingLanguage(false);
    }
  };

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.selectedScope, selectedScope);
    localStorage.setItem(STORAGE_KEYS.sourceLang, sourceLang);
    localStorage.setItem(STORAGE_KEYS.targetLang, targetLang);
  }, [selectedScope, sourceLang, targetLang]);

  useEffect(() => {
    if (runId) { fetchProjectFiles(); }
  }, [runId, sourceLang]);

  const fetchProjectFiles = async () => {
    try {
      const response = await ProjectAPI.listFiles(runId!); 
      const mapped = mapBackendFiles(response.files);
      setFiles(mapped);
    } catch (e) { console.error("Failed to fetch files", e); }
  };

  const refreshAnalysisTabs = (force = true) => {
    if (!runId) return;
    warmAnalysisTabs(runId, force).catch((error) => {
      console.error("Failed to warm analysis tabs", error);
    });
  };

  const removeFile = async (id: string) => {
    if (pipelineActive) {
      toast.error("Cannot delete files while the pipeline is active.");
      return;
    }
    setFiles(prev => prev.filter(f => f.id !== id));
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
    <div className="space-y-10 pb-20">
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

      {/* SECTION 1: CONFIGURATION */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
        <SectionLabel>Step 1: Project Configuration</SectionLabel>
        
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

        <div className="space-y-4">
          <div className="flex items-center gap-2 text-amber-400 text-sm font-bold uppercase tracking-widest">
            <Zap size={16} /> Select Migration Scope & Budget
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {MIGRATION_SCOPES.map((scope) => (
              <div 
                key={scope.id} 
                onClick={() => {
                  if (pipelineActive) { toast.error("Scope is locked while pipeline is active."); } 
                  else { setSelectedScope(scope.id); }
                }}
                className={`p-4 rounded-2xl border transition-all cursor-pointer ${!pipelineActive ? 'hover:border-slate-600' : 'opacity-60 cursor-not-allowed'} ${selectedScope === scope.id ? 'border-indigo-500 bg-indigo-500/10 shadow-lg' : 'border-slate-800 bg-slate-900/50'}`}
              >
                <div className="flex justify-between mb-2">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${scope.bg} ${scope.color}`}>{scope.cost}</span>
                  {selectedScope === scope.id && <CheckCircle2 size={14} className="text-indigo-400" />}
                </div>
                <h4 className="text-white font-bold text-xs mb-1">{scope.title}</h4>
                <div className="text-xs font-mono text-indigo-400 mb-2">{scope.tokens} Tokens</div>
                <p className="text-[10px] text-slate-500 line-clamp-2">{scope.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </motion.div>

      {/* SECTION 2: INGESTION */}
      <div className="space-y-6">
        <SectionLabel>Step 2: Source Code Ingestion</SectionLabel>

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
            <FileText size={16} /> Step 3: Review & Launch
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
                  <tr key={file.id} className="border-t border-slate-700 hover:bg-slate-800/30 transition-colors">
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
                    <td className="p-4">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-indigo-300">{formatLanguageName(file.detectedLang)}</span>
                        {file.status === 'Analyzed' ? (
                          <CheckCircle2 size={12} className="text-emerald-500" title="Confirmed" />
                        ) : (
                          <Clock size={12} className="text-slate-500" title="Suggested" />
                        )}
                      </div>
                    </td>
                    <td className="p-4">
                      {file.isValid === true ? (
                        <div className="flex items-center gap-1 text-emerald-400 text-xs font-medium">
                          <CheckCircle2 size={14} /> Valid
                        </div>
                      ) : file.isValid === false ? (
                        <div className="flex items-center gap-1 text-amber-400 text-xs font-medium">
                          <AlertCircle size={14} /> Suspicious
                        </div>
                      ) : (
                        <span className="text-slate-600 text-xs">Unknown</span>
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
        </div>

        <div className="flex justify-center pt-6">
          {pipelineActive ? (
            <button onClick={() => navigate('/mission-control')} className="px-12 py-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-full font-black shadow-2xl transition-all flex items-center gap-3">
              <Activity size={20} /> View Pipeline Progress
            </button>
          ) : (
            <button 
              onClick={launchPipeline} 
              disabled={isLaunching || files.length === 0} 
              className="px-12 py-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full font-black shadow-2xl transition-all flex items-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLaunching ? <><Loader2 className="animate-spin" size={20} /> Initializing...</> : <><Play fill="currentColor" size={20} /> Launch Migration Pipeline</>}
            </button>
          )}
        </div>
      </div>

      {/* LANGUAGE DETECTION MODAL */}
      <AnimatePresence>
        {detectionAlert && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="glass-card p-8 rounded-3xl border-indigo-500/50 bg-slate-900 border-2 max-w-md w-full shadow-2xl text-center space-y-6"
            >
              <div className="flex justify-center">
                <div className="p-4 bg-indigo-500/20 rounded-full text-indigo-400">
                  {isConfirmingLanguage ? <Loader2 className="animate-spin" size={40} /> : <Languages size={40} />}
                </div>
              </div>

              {isConfirmingLanguage ? (
                <div className="space-y-3">
                  <h3 className="text-xl font-bold text-white">Saving Language</h3>
                  <p className="text-sm text-slate-400">Preparing the next file confirmation...</p>
                </div>
              ) : !isCorrecting ? (
                <div className="space-y-5">
                  <div className="space-y-2">
                    <h3 className="text-xl font-bold text-white">Language Detected</h3>
                    <p className="text-slate-400">
                      {detectionAlert.file.toLowerCase().endsWith('.txt') ? (
                        <>This text file <span className="text-white font-mono">{detectionAlert.file}</span> contains <span className="text-indigo-400 font-bold">{formatLanguageName(detectionAlert.lang)}</span> code.</>
                      ) : (
                        <><span className="text-white font-mono">{detectionAlert.file}</span> was detected as <span className="text-indigo-400 font-bold">{formatLanguageName(detectionAlert.lang)}</span>.</>
                      )}
                    </p>
                    <p className="text-sm text-slate-500 italic">Please confirm before continuing.</p>
                  </div>
                  <div className="flex gap-4">
                    <button disabled={isConfirmingLanguage} onClick={() => setIsCorrecting(true)} className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"><XCircle size={18} /> No</button>
                    <button disabled={isConfirmingLanguage} onClick={() => confirmLanguage(true)} className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"><CheckCircle2 size={18} /> Yes</button>
                  </div>
                </div>
              ) : (
                <div className="space-y-5">
                  <div className="space-y-2">
                    <h3 className="text-xl font-bold text-white">Choose Correct Language</h3>
                    <p className="text-slate-400 text-sm">Select the language for <span className="text-indigo-400 font-mono">{detectionAlert.file}</span>.</p>
                  </div>
                  <select
                    value={selectedManualLang}
                    onChange={(e) => setSelectedManualLang(e.target.value)}
                    disabled={isConfirmingLanguage}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="" disabled>Select language</option>
                    {SOURCE_LANGUAGES.filter(lang => lang.id !== 'auto').map(lang => (
                      <option key={lang.id} value={lang.id}>{lang.name}</option>
                    ))}
                  </select>
                  <div className="flex gap-3">
                    <button disabled={isConfirmingLanguage} onClick={() => setIsCorrecting(false)} className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed">Back</button>
                    <button disabled={!selectedManualLang || isConfirmingLanguage} onClick={() => confirmLanguage(false, selectedManualLang)} className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2"><CheckCircle2 size={18} /> Confirm</button>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default SourceFiles;


