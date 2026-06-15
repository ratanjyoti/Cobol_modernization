import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  FileText, Zap, CheckCircle2, Activity, Layers, 
  Database, ArrowUpRight, Play, Loader2, 
  Upload, GitBranch, Languages, Code 
} from 'lucide-react';
import toast from 'react-hot-toast';

// Reusable KPI Card Component
const KPICard = ({ label, value, icon: Icon, subtext }: any) => (
  <div className="glass-card p-6 rounded-2xl border-slate-800 hover:border-indigo-500/50 transition-all cursor-pointer group">
    <div className="flex justify-between items-start mb-4">
      <span className="text-sm font-medium text-slate-400">{label}</span>
      <div className="p-2 bg-slate-900 rounded-lg group-hover:bg-indigo-500/20 transition-colors">
        <Icon size={20} className="text-slate-500 group-hover:text-indigo-400" />
      </div>
    </div>
    <div className="text-3xl font-bold text-white mb-1">{value}</div>
    <div className="flex items-center justify-between">
      <span className="text-xs text-slate-500">{subtext}</span>
      <ArrowUpRight size={14} className="text-indigo-400" />
    </div>
  </div>
);

const Dashboard = () => {
  const navigate = useNavigate();
  
  // --- STATE FOR INGESTION ---
  const [isLaunching, setIsLaunching] = useState(false);
  const [inputMethod, setInputMethod] = useState<'file' | 'github'>('file');
  const [sourceLang, setSourceLang] = useState('auto');
  const [targetLang, setTargetLang] = useState('java');
  const [githubUrl, setGithubUrl] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const handleStartMigration = async () => {
    if (inputMethod === 'github' && !githubUrl) {
      toast.error("Please provide a valid GitHub Repository URL");
      return;
    }
    if (inputMethod === 'file' && selectedFiles.length === 0) {
      toast.error("Please upload at least one source file");
      return;
    }

    setIsLaunching(true);
    
    const steps = ["Analyzing Source Language...", "Validating Repository...", "Initializing Pipeline..."];
    for (const step of steps) {
        toast.loading(step);
        await new Promise(res => setTimeout(res, 1000));
    }

    toast.success("Pipeline Started!");
    navigate('/mission-control');
  };

  return (
    <div className="space-y-10">
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <h1 className="text-4xl font-extrabold text-white tracking-tight">Migration Hub</h1>
          <p className="text-slate-400 text-lg max-w-2xl">
            Configure your source and target environments to begin the modernization process.
          </p>
        </div>
      </div>

      {/* --- INGESTION CARD --- */}
      <div className="glass-card p-8 rounded-3xl border-slate-800 bg-slate-900/50 shadow-2xl">
        <div className="flex items-center gap-3 mb-8">
          <div className="p-2 bg-indigo-600 rounded-lg text-white"><Upload size={20}/></div>
          <h2 className="text-xl font-bold text-white">Project Ingestion</h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          
          {/* Column 1: Source Input */}
          <div className="space-y-6">
            <div className="space-y-3">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Source Input</label>
              <div className="flex p-1 bg-slate-950 rounded-xl border border-slate-800">
                <button 
                  onClick={() => setInputMethod('file')}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${inputMethod === 'file' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                >
                  <Upload size={14}/> Upload
                </button>
                <button 
                  onClick={() => setInputMethod('github')}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-medium transition-all ${inputMethod === 'github' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-500 hover:text-slate-300'}`}
                >
                  <GitBranch size={14}/> GitHub
                </button>
              </div>
            </div>

            {inputMethod === 'file' ? (
              <div className="relative group border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-2xl p-8 transition-all text-center bg-slate-900/30">
                <input 
                  type="file" 
                  multiple 
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
                  onChange={(e) => setSelectedFiles(e.target.files ? Array.from(e.target.files) : [])}
                />
                <div className="flex flex-col items-center gap-3">
                  <div className="p-3 bg-slate-800 rounded-full text-slate-400 group-hover:text-indigo-400 transition-colors">
                    <Upload size={24} />
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-slate-300">Click or drag files to upload</p>
                    <p className="text-xs text-slate-500">Supports .cbl, .cob, .txt</p>
                  </div>
                </div>
                {selectedFiles.length > 0 && (
                  <div className="mt-4 p-2 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-xs text-indigo-400">
                    {selectedFiles.length} files selected
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="relative">
                  <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                  <input 
                    type="text" 
                    placeholder="https://github.com/user/repo" 
                    className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                    value={githubUrl}
                    onChange={(e) => setGithubUrl(e.target.value)}
                  />
                </div>
                <p className="text-[10px] text-slate-500 italic">Ensure the repository is public or API key has access.</p>
              </div>
            )}
          </div>

          {/* Column 2: Language Config */}
          <div className="space-y-6">
            <div className="space-y-3">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                <Languages size={14}/> Language Mapping
              </label>
              <div className="grid grid-cols-1 gap-4">
                <div className="space-y-2">
                  <span className="text-[10px] text-slate-500 ml-1">Source Language</span>
                  <select 
                    value={sourceLang}
                    onChange={(e) => setSourceLang(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 appearance-none"
                  >
                    <option value="auto">✨ Auto-Detect Language</option>
                    <optgroup label="Standard COBOL">
                      <option value="cobol">COBOL (Pure)</option>
                      <option value="cobol-sql">COBOL + SQL</option>
                      <option value="cobol-ims">COBOL + IMS</option>
                      <option value="cobol-cics">COBOL + CICS</option>
                    </optgroup>
                    <optgroup label="Telon / Others">
                      <option value="telon-batch">Telon Batch (T2B)</option>
                      <option value="telon-screen">Telon Screen (T2C)</option>
                      <option value="jcl">JCL</option>
                      <option value="pli">PL/I</option>
                      <option value="fortran">Fortran</option>
                    </optgroup>
                  </select>
                </div>
                <div className="space-y-2">
                  <span className="text-[10px] text-slate-500 ml-1">Target Language</span>
                  <select 
                    value={targetLang}
                    onChange={(e) => setTargetLang(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 appearance-none"
                  >
                    <option value="java">Java 21 (Spring Boot)</option>
                    <option value="csharp">C# 12 (.NET 8)</option>
                    <option value="python">Python 3.12 (FastAPI)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Column 3: Execution */}
          <div className="flex flex-col justify-center items-center gap-6 bg-slate-900/50 rounded-3xl p-6 border border-slate-800">
            <div className="text-center space-y-2">
              <div className="p-3 bg-indigo-600/20 text-indigo-400 rounded-full mx-auto w-fit">
                <Code size={24} />
              </div>
              <h3 className="text-lg font-bold text-white">Ready to Convert</h3>
              <p className="text-xs text-slate-500">All systems are online. Ready to launch the pipeline.</p>
            </div>
            <motion.button 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleStartMigration}
              disabled={isLaunching}
              className={`w-full py-4 rounded-2xl font-bold flex items-center justify-center gap-3 shadow-xl transition-all ${
                isLaunching 
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed shadow-none' 
                : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-indigo-500/30'
              }`}
            >
              {isLaunching ? (
                <>
                  <Loader2 className="animate-spin" size={20} /> 
                  Initializing...
                </>
              ) : (
                <>
                  <Play size={20} fill="currentColor" /> 
                  Start Migration
                </>
              )}
            </motion.button>
          </div>
        </div>
      </div>

      {/* KPI GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard label="Total COBOL Files" value="422" icon={FileText} subtext="Priority view active" />
        <KPICard label="Complex Modules" value="14" icon={Activity} subtext="Needs review" />
        <KPICard label="Pending Chunks" value="35" icon={Layers} subtext="Processing queue" />
        <KPICard label="Verified Rules" value="16" icon={CheckCircle2} subtext="Ready to convert" />
      </div>
    </div>
  );
};

export default Dashboard;
