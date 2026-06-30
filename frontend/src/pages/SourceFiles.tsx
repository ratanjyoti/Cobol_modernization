import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ProjectAPI, WS_BASE_URL } from '../services/api';

import {
  Upload, FileText, CheckCircle2, Clock,
  AlertCircle, Layers, Loader2, Zap, Play, GitBranch,
  Activity, RotateCcw, Trash2, Languages, Target, XCircle
} from 'lucide-react';
import toast from 'react-hot-toast';

type SourceFileRecord = {
  id: string;
  name: string;
  size: number;
  status: 'Pending' | 'Processing' | 'Analyzed';
  chunks: number;
  detectedLang?: string;
};

type DetectionAlert = {
  file: string;
  lang: string;
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
  { id: 'telon-batch', name: 'Telon Batch (T2B)' },
  { id: 'telon-screen', name: 'Telon Screen (T2C)' },
  { id: 'pli', name: 'PL/I' },
  { id: 'fortran', name: 'Fortran' },
];

const TARGET_LANGUAGES = [
  { id: 'java', name: 'Java 21 (Spring Boot)' },
  { id: 'csharp', name: 'C# 12 (.NET 8)' },
  { id: 'python', name: 'Python 3.12 (FastAPI)' },
];

const SourceFiles = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queuedDetectionKeys = useRef<Set<string>>(new Set());

  const [inputMethod, setInputMethod] = useState<'file' | 'github'>('file');
  const [githubUrl, setGithubUrl] = useState('');
  const [files, setFiles] = useState<SourceFileRecord[]>([]);
  const [selectedScope, setSelectedScope] = useState(localStorage.getItem(STORAGE_KEYS.selectedScope) || '');
  const [sourceLang, setSourceLang] = useState(localStorage.getItem(STORAGE_KEYS.sourceLang) || 'auto');
  const [targetLang, setTargetLang] = useState(localStorage.getItem(STORAGE_KEYS.targetLang) || 'java');
  const [isLaunching, setIsLaunching] = useState(false);
  const [isFetchingRepo, setIsFetchingRepo] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [pipelineActive, setPipelineActive] = useState(() => localStorage.getItem(STORAGE_KEYS.pipelineStatus) === 'active');
  const [detectionAlert, setDetectionAlert] = useState<DetectionAlert | null>(null);
  const [pendingDetections, setPendingDetections] = useState<DetectionAlert[]>([]);
  
  const runId = localStorage.getItem('active_run_id');
  const enqueueLanguageDetections = (mappedFiles: any[]) => {
    if (sourceLang !== 'auto') return;

    const detections = mappedFiles
      .map((file) => ({ file: file.filename || file.name, lang: file.lang || file.detected_lang || 'UNKNOWN' }))
      .filter((item) => {
        if (!item.file || !item.lang || item.lang === 'UNKNOWN') return false;
        const key = `${item.file}:${item.lang}`;
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
      if (data.event === 'LANGUAGE_DETECTED') {
        enqueueLanguageDetections([{ filename: data.file, lang: data.suggested_lang }]);
      }
    };
    return () => socket.close();
  }, [runId, sourceLang]);

  const [isCorrecting, setIsCorrecting] = useState(false);
  const [selectedManualLang, setSelectedManualLang] = useState('');

  const confirmLanguage = async (confirmed: boolean, manualLang?: string) => {
    if (!runId || !detectionAlert) return;

    const finalLang = confirmed ? detectionAlert.lang : (manualLang || 'UNKNOWN');

    try {
      await ProjectAPI.confirmLanguage({
        run_id: runId,
        filename: detectionAlert.file,
        lang: finalLang,
      });
      toast.success(`Updated ${detectionAlert.file} to ${finalLang}`);
      setFiles(prev => prev.map(file => file.name === detectionAlert.file ? { ...file, status: 'Analyzed', detectedLang: finalLang } : file));
      setIsCorrecting(false);
      setSelectedManualLang('');
      showNextDetection();
    } catch (e) {
      toast.error("Failed to save language preference");
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
      const mapped = response.files.map((f: any) => ({
        id: f.id,
        name: f.filename,
        size: f.size || 0,
        status: f.status === 'PENDING_CONFIRMATION' ? 'Pending' : 'Analyzed',
        chunks: 1,
        detectedLang: f.detected_lang || f.lang,
      }));
      setFiles(mapped);
    } catch (e) { console.error("Failed to fetch files", e); }
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
        if (file.name.endsWith('.zip')) {
          const zipFormData = new FormData();
          zipFormData.append('run_id', runId);
          zipFormData.append('zip_file', file);
          const zipData = await ProjectAPI.uploadZip(zipFormData);
          if (zipData && zipData.mapped_files) {
            const backendFiles = zipData.mapped_files.map((f: any) => ({
              id: f.id, name: f.filename, size: f.size || 0, status: 'Pending' as const, chunks: 1, detectedLang: f.lang || f.detected_lang,
            }));
            setFiles(prev => [...prev, ...backendFiles]);
            enqueueLanguageDetections(zipData.mapped_files);
            toast.success(`Extracted ${backendFiles.length} files`);
          }
        } else if (file.name.endsWith('.cbl') || file.name.endsWith('.cob') || file.name.endsWith('.txt')) {
          const fileFormData = new FormData();
          fileFormData.append('run_id', runId);
          fileFormData.append('files', file);
          const fileResponse = await ProjectAPI.uploadFiles(fileFormData);
          const uploadedRecords = fileResponse.mapped_files || [];
          const backendFiles = uploadedRecords.map((f: any) => ({
            id: f.id, name: f.filename, size: f.size || file.size, status: 'Pending' as const, chunks: 1, detectedLang: f.lang || f.detected_lang,
          }));
          setFiles(prev => [...prev, ...backendFiles]);
          enqueueLanguageDetections(uploadedRecords);
          toast.success(`Uploaded ${file.name}`);
        } else {
          toast.error(`Unsupported file type: ${file.name}`);
        }
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "File upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  const handleGithubIngest = async () => {
    if (!githubUrl.trim() || !runId) {
      toast.error("Invalid GitHub URL or no project found");
      return;
    }
    setIsFetchingRepo(true);
    try {
      const response = await ProjectAPI.ingestGithub(runId!, githubUrl);
      const backendFiles = response.mapped_files.map((f: any) => ({
        id: f.id, name: f.filename, size: f.size || 0, status: 'Pending' as const, chunks: 1, detectedLang: f.lang || f.detected_lang,
      }));
      setFiles(prev => [...prev, ...backendFiles]);
      enqueueLanguageDetections(response.mapped_files || []);
      toast.success("Repository ingested successfully!");
    } catch (error) {
      toast.error("Failed to ingest GitHub repository");
    } finally {
      setIsFetchingRepo(false);
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
      {/* HEADER */}
      <div className="flex justify-between items-center">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold text-white">Source Files</h1>
          <p className="text-slate-400">Configure your migration mapping and ingest source code.</p>
        </div>
        <div className="flex gap-3">
          {pipelineActive && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-500 text-xs font-bold animate-pulse">
              <Loader2 size={14} className="animate-spin" /> Pipeline Processing Active
            </div>
          )}
          <button onClick={resetPipeline} className="p-2 text-slate-500 hover:text-white transition-colors" title="Reset Pipeline">
            <RotateCcw size={18} />
          </button>
        </div>
      </div>

      {/* SECTION 1: CONFIGURATION (NOW FIRST) */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
        <div className="flex items-center gap-2 text-indigo-400 text-sm font-bold uppercase tracking-widest">
          <Layers size={16} /> Step 1: Project Configuration
        </div>
        
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

      {/* SECTION 2: INGESTION (NOW SECOND) */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-indigo-400 text-sm font-bold uppercase tracking-widest">
          <Upload size={16} /> Step 2: Source Code Ingestion
        </div>

        <div className="flex justify-center">
          <div className="flex p-1 bg-slate-950 rounded-xl border border-slate-800 w-full max-w-md">
            <button onClick={() => setInputMethod('file')} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${inputMethod === 'file' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}><Upload size={14}/> Local Upload</button>
            <button onClick={() => setInputMethod('github')} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${inputMethod === 'github' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}><GitBranch size={14}/> GitHub Repository</button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6">
          {inputMethod === 'file' ? (
            <div 
              onClick={() => fileInputRef.current?.click()}
              className="relative group border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-3xl p-12 transition-all text-center bg-slate-900/30 cursor-pointer"
            >
              <input type="file" ref={fileInputRef} multiple style={{ display: 'none' }} onChange={handleFileUpload} accept=".cbl,.cob,.txt,.zip" />
              <div className="flex flex-col items-center gap-4 pointer-events-none"> 
                <div className={`p-4 rounded-full transition-colors ${isUploading ? 'bg-indigo-500 text-white' : 'bg-slate-800 text-slate-400 group-hover:text-indigo-400'}`}>
                  {isUploading ? <Loader2 className="animate-spin" size={32} /> : <Upload size={32} />}
                </div>
                <div className="space-y-1">
                  <p className="text-lg font-medium text-slate-300">{isUploading ? 'Uploading files...' : 'Click or drag COBOL files or a ZIP archive'}</p>
                  <p className="text-sm text-slate-500">Supports .cbl, .cob, .txt, .zip</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-card p-8 rounded-3xl border-slate-800 bg-slate-900/50 flex flex-col md:flex-row gap-4 items-end">
              <div className="flex-1 space-y-3 w-full">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">GitHub Repository URL</label>
                <div className="relative">
                  <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                  <input type="text" placeholder="https://github.com/username/repository" className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 transition-all" value={githubUrl} onChange={(e) => setGithubUrl(e.target.value)} />
                </div>
              </div>
              <button onClick={handleGithubIngest} disabled={isFetchingRepo} className="w-full md:w-auto px-8 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50">
                {isFetchingRepo ? <><Loader2 className="animate-spin" size={18}/> Fetching...</> : <><Zap size={18}/> Ingest Repo</>}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* SECTION 3: FILE REVIEW & LAUNCH (NOW LAST) */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-indigo-400 text-sm font-bold uppercase tracking-widest">
          <FileText size={16} /> Step 3: Review & Launch
        </div>
        
        <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-800/50 text-slate-300 text-xs uppercase tracking-wider">
              <tr className="border-b border-slate-700">
                <th className="p-4 font-semibold">File Name</th>
                <th className="p-4 font-semibold">Size</th>
                <th className="p-4 font-semibold">Status</th>
                <th className="p-4 font-semibold">Language</th>
                <th className="p-4 font-semibold">Chunks</th>
                <th className="p-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="text-slate-300">
              {files.map(file => (
                <tr key={file.id} className="border-t border-slate-700 hover:bg-slate-800/30 transition-colors">
                  <td className="p-4 flex items-center gap-3"><FileText size={16} className="text-slate-500" /><span className="font-medium">{file.name}</span></td>
                  <td className="p-4 text-sm">{file.size} LLOC</td>
                  <td className="p-4 text-sm">
                    {file.status === 'Processing' ? <div className="flex items-center gap-2 text-amber-400 font-medium"><Loader2 size={14} className="animate-spin" /> Processing...</div> : 
                     file.status === 'Analyzed' ? <div className="flex items-center gap-2 text-emerald-400"><CheckCircle2 size={14} /> Analyzed</div> : 
                     <div className="flex items-center gap-2 text-slate-500"><Clock size={14} /> Pending</div>}
                  </td>
                  <td className="p-4 text-sm"><span className="text-indigo-300 font-mono text-xs">{file.detectedLang || "-"}</span></td>
                  <td className="p-4 text-sm">
                    {file.chunks > 1 ? <span className="bg-blue-500/20 text-blue-400 px-2 py-1 rounded text-xs border border-blue-500/30">{file.chunks} Chunks</span> : <span className="text-slate-500 text-xs">Single File</span>}
                  </td>
                  <td className="p-4 text-right">
                    <button onClick={() => removeFile(file.id)} className={`p-2 rounded-lg transition-colors ${pipelineActive ? 'text-slate-700 cursor-not-allowed' : 'text-slate-500 hover:text-red-400 hover:bg-red-500/10'}`}><Trash2 size={16} /></button>
                  </td>
                </tr>
              ))}
              {files.length === 0 && (<tr className="border-t border-slate-700"><td colSpan={6} className="p-12 text-center text-slate-500 italic">No source code ingested. Upload files above to begin.</td></tr>)}
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
                <div className="p-4 bg-indigo-500/20 rounded-full text-indigo-400"><Languages size={40} /></div>
              </div>

              {!isCorrecting ? (
                <div className="space-y-5">
                  <div className="space-y-2">
                    <h3 className="text-xl font-bold text-white">Language Detected</h3>
                    <p className="text-slate-400">
                      <span className="text-white font-mono">{detectionAlert.file}</span> was detected as <span className="text-indigo-400 font-bold">{detectionAlert.lang}</span>.
                    </p>
                    <p className="text-sm text-slate-500 italic">Please confirm before continuing.</p>
                  </div>
                  <div className="flex gap-4">
                    <button onClick={() => setIsCorrecting(true)} className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2"><XCircle size={18} /> No</button>
                    <button onClick={() => confirmLanguage(true)} className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2"><CheckCircle2 size={18} /> Yes</button>
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
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="" disabled>Select language</option>
                    {SOURCE_LANGUAGES.filter(lang => lang.id !== 'auto').map(lang => (
                      <option key={lang.id} value={lang.id}>{lang.name}</option>
                    ))}
                  </select>
                  <div className="flex gap-3">
                    <button onClick={() => setIsCorrecting(false)} className="flex-1 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-bold transition-all">Back</button>
                    <button disabled={!selectedManualLang} onClick={() => confirmLanguage(false, selectedManualLang)} className="flex-1 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl font-bold transition-all flex items-center justify-center gap-2"><CheckCircle2 size={18} /> Confirm</button>
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













