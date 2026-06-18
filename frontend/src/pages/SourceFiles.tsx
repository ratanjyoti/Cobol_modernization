import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Upload, FileText, CheckCircle2, Clock,
  AlertCircle, Layers, Loader2, Zap, Play, GitBranch,
  Activity, RotateCcw, Trash2 
} from 'lucide-react';
import toast from 'react-hot-toast';

type SourceFileRecord = {
  id: string;
  name: string;
  size: number;
  status: 'Pending' | 'Processing' | 'Analyzed';
  chunks: number;
};

const STORAGE_KEYS = {
  files: 'modernizer_files',
  pipelineStatus: 'modernizer_pipeline_status',
  selectedScope: 'modernizer_selected_scope',
} as const;

const MIGRATION_SCOPES = [
  { id: 'mapping', title: 'Dependency Mapping', tokens: '10k – 25k', cost: 'Low', color: 'text-emerald-400', bg: 'bg-emerald-500/10', desc: 'Visualize architecture & connections only.' },
  { id: 'reverse', title: 'Reverse Engineering', tokens: '50k – 120k', cost: 'Medium', color: 'text-amber-400', bg: 'bg-amber-500/10', desc: 'Extract logic, complexity & rules.' },
  { id: 'plain', title: 'Business Rules (Plain)', tokens: '80k – 150k', cost: 'Medium', color: 'text-blue-400', bg: 'bg-blue-500/10', desc: 'Simple functional rule extraction.' },
  { id: 'ddd', title: 'Business Rules (DDD)', tokens: '150k – 300k', cost: 'High', color: 'text-purple-400', bg: 'bg-purple-500/10', desc: 'Domain-driven microservice decomposition.' },
  { id: 'full', title: 'Full Migration', tokens: '250k – 600k', cost: 'Very High', color: 'text-red-400', bg: 'bg-red-500/10', desc: 'End-to-end agentic pipeline.' },
];

const isSourceFileRecord = (value: unknown): value is SourceFileRecord => {
  if (!value || typeof value !== 'object') return false;
  const file = value as Partial<SourceFileRecord>;
  return (
    typeof file.id === 'string' &&
    typeof file.name === 'string' &&
    typeof file.size === 'number' &&
    ['Pending', 'Processing', 'Analyzed'].includes(file.status ?? '') &&
    typeof file.chunks === 'number'
  );
};

const readStoredFiles = (): SourceFileRecord[] => {
  const savedFiles = localStorage.getItem(STORAGE_KEYS.files);
  if (!savedFiles) return [];
  try {
    const parsed = JSON.parse(savedFiles);
    if (Array.isArray(parsed) && parsed.every(isSourceFileRecord)) return parsed;
  } catch (error) {
    console.warn('Failed to parse stored source files', error);
  }
  return [];
};

const SourceFiles = () => {
  const navigate = useNavigate();
  const [inputMethod, setInputMethod] = useState<'file' | 'github'>('file');
  const [githubUrl, setGithubUrl] = useState('');
  const [files, setFiles] = useState<SourceFileRecord[]>(readStoredFiles);
  const [selectedScope, setSelectedScope] = useState(localStorage.getItem(STORAGE_KEYS.selectedScope) || '');
  const [isLaunching, setIsLaunching] = useState(false);
  const [isFetchingRepo, setIsFetchingRepo] = useState(false);
  const [pipelineActive, setPipelineActive] = useState(() => localStorage.getItem(STORAGE_KEYS.pipelineStatus) === 'active');

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.files, JSON.stringify(files));
  }, [files]);

  const removeFile = (id: string) => {
    if (pipelineActive) {
      toast.error("Cannot delete files while the pipeline is active. Reset the pipeline first.");
      return;
    }
    setFiles(prev => prev.filter(f => f.id !== id));
    toast.success("File removed from queue");
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = e.target.files;
    if (!uploadedFiles) return;
    const newFiles: SourceFileRecord[] = Array.from(uploadedFiles).map((f) => ({
      id: Math.random().toString(36).substring(2, 9), // FIXED: Better ID generation
      name: f.name,
      size: Math.floor(Math.random() * 5000),
      status: 'Pending',
      chunks: 1,
    }));
    setFiles(prev => [...prev, ...newFiles]); // FIXED: Used functional update
    toast.success("Files uploaded!");
  };

  const handleGithubIngest = async () => {
    if (!githubUrl.trim()) {
      toast.error("Please provide a valid GitHub URL");
      return;
    }
    setIsFetchingRepo(true);
    await new Promise(res => setTimeout(res, 2000));
    const mockRepoFiles: SourceFileRecord[] = [ 
      { id: 'g1-' + Date.now(), name: 'MAIN-SVR.cbl', size: 4200, status: 'Pending', chunks: 14 },
      { id: 'g2-' + Date.now(), name: 'ACCT-PROC.cbl', size: 1100, status: 'Pending', chunks: 1 },
      { id: 'g3-' + Date.now(), name: 'CUST-DB.cob', size: 800, status: 'Pending', chunks: 1 },
    ];
    setFiles(prev => [...prev, ...mockRepoFiles]); // FIXED: Appends files instead of wiping current list
    setIsFetchingRepo(false);
    toast.success("Repository ingested!");
  };

  const simulateProcessing = async () => {
    setPipelineActive(true);
    localStorage.setItem(STORAGE_KEYS.pipelineStatus, 'active');
    
    // FIXED: Iterate over IDs, not index. 
    // This prevents errors if files are removed while processing is happening.
    const fileIds = files.map(f => f.id);
    
    for (const id of fileIds) {
      setFiles(prev => prev.map(f => f.id === id ? { ...f, status: 'Processing' } : f));
      await new Promise(res => setTimeout(res, 800 + Math.random() * 1000));
      setFiles(prev => prev.map(f => f.id === id ? { ...f, status: 'Analyzed' } : f));
    }
    toast.success("All files analyzed!");
  };

  const launchPipeline = async () => {
    if (!selectedScope) {
      toast.error("Please select a migration scope first!");
      return;
    }
    setIsLaunching(true);
    localStorage.setItem(STORAGE_KEYS.selectedScope, selectedScope);
    await simulateProcessing();
    setIsLaunching(false);
    toast.success("Pipeline initialized!");
    navigate('/mission-control');
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
      <div className="flex justify-between items-center">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold text-white">Source Files</h1>
          <p className="text-slate-400">Ingest your COBOL source code to begin analysis.</p>
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

      <div className="flex justify-center">
        <div className="flex p-1 bg-slate-950 rounded-xl border border-slate-800 w-full max-w-md">
          <button onClick={() => setInputMethod('file')} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${inputMethod === 'file' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}><Upload size={14}/> Local Upload</button>
          <button onClick={() => setInputMethod('github')} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${inputMethod === 'github' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}><GitBranch size={14}/> GitHub Repository</button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {inputMethod === 'file' ? (
          <div className="relative group border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-3xl p-12 transition-all text-center bg-slate-900/30">
            <input type="file" multiple className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" onChange={handleFileUpload} accept=".cbl,.cob,.txt" />
            <div className="flex flex-col items-center gap-4">
              <div className="p-4 bg-slate-800 rounded-full text-slate-400 group-hover:text-indigo-400 transition-colors"><Upload size={32} /></div>
              <div className="space-y-1">
                <p className="text-lg font-medium text-slate-300">Click or drag COBOL files to upload</p>
                <p className="text-sm text-slate-500">Supports .cbl, .cob, .txt</p>
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

      <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead className="bg-slate-800/50 text-slate-300 text-xs uppercase tracking-wider">
            <tr className="border-b border-slate-700">
              <th className="p-4 font-semibold">File Name</th>
              <th className="p-4 font-semibold">Size</th>
              <th className="p-4 font-semibold">Status</th>
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
                  {file.status === 'Processing' ? (
                    <div className="flex items-center gap-2 text-amber-400 font-medium"><Loader2 size={14} className="animate-spin" /> Processing...</div>
                  ) : file.status === 'Analyzed' ? (
                    <div className="flex items-center gap-2 text-emerald-400"><CheckCircle2 size={14} /> Analyzed</div>
                  ) : (
                    <div className="flex items-center gap-2 text-slate-500"><Clock size={14} /> Pending</div>
                  )}
                </td>
                <td className="p-4 text-sm">
                  {file.chunks > 1 ? <span className="bg-blue-500/20 text-blue-400 px-2 py-1 rounded text-xs border border-blue-500/30">{file.chunks} Chunks</span> : <span className="text-slate-500 text-xs">Single File</span>}
                </td>
                <td className="p-4 text-right">
                  <button 
                    onClick={() => removeFile(file.id)} 
                    className={`p-2 rounded-lg transition-colors ${pipelineActive ? 'text-slate-700 cursor-not-allowed' : 'text-slate-500 hover:text-red-400 hover:bg-red-500/10'}`}
                    title={pipelineActive ? "Cannot delete during processing" : "Remove file"}
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {files.length === 0 && (
              <tr className="border-t border-slate-700"><td colSpan={5} className="p-12 text-center text-slate-500 italic">No source code ingested.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {files.length > 0 && (
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
          <div className="flex items-center gap-2 text-amber-400 text-sm font-bold uppercase tracking-widest">
            <Zap size={16} /> Define Migration Scope & Budget
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {MIGRATION_SCOPES.map((scope) => (
              <div 
                key={scope.id} 
                onClick={() => {
                  if (pipelineActive) {
                    toast.error("Scope is locked while pipeline is active. Reset pipeline to change scope.");
                  } else {
                    setSelectedScope(scope.id);
                  }
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
          <div className="flex justify-center pt-6">
            {pipelineActive ? (
              <button onClick={() => navigate('/mission-control')} className="px-12 py-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-full font-black shadow-2xl transition-all flex items-center gap-3">
                <Activity size={20} /> View Pipeline Progress
              </button>
            ) : (
              <button onClick={launchPipeline} disabled={isLaunching} className="px-12 py-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-full font-black shadow-2xl transition-all flex items-center gap-3">
                {isLaunching ? <><Loader2 className="animate-spin" /> Initializing...</> : <><Play fill="currentColor" /> Launch Migration Pipeline</>}
              </button>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
};

export default SourceFiles;
