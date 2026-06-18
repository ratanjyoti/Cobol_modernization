import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, Zap, CheckCircle2, Activity, Layers, 
  Database, ArrowUpRight, Play, Loader2, 
  Upload, GitBranch, Languages, Code, 
  ChevronRight, HelpCircle, AlertCircle, PlusCircle,
  BookOpen, BrainCircuit, Rocket, ShieldCheck,
  X, Target, Info, Lightbulb
} from 'lucide-react';
import toast from 'react-hot-toast';

// --- Constants for Token Budgeting & Scope ---
const MIGRATION_SCOPES = [
  {
    id: 'mapping',
    title: 'Dependency Mapping',
    tokens: '10k – 25k',
    cost: 'Low',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
    purpose: 'Visualize architecture and relationships without deep semantic analysis.',
    includes: ['Program-to-program dependencies', 'Copybook relationships', 'File/DB interactions', 'Entry-point identification'],
    bestFor: 'Architecture understanding and impact analysis.'
  },
  {
    id: 'reverse',
    title: 'Reverse Engineering',
    tokens: '50k – 120k',
    cost: 'Medium',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    purpose: 'Understand how the legacy application behaves.',
    includes: ['Program summaries', 'Complexity scoring', 'Functional decomposition', 'Technical documentation'],
    bestFor: 'System understanding before migration.'
  },
  {
    id: 'plain_rules',
    title: 'Business Rule Extraction (Plain)',
    tokens: '80k – 150k',
    cost: 'Medium',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    purpose: 'Extract understandable business logic from legacy code.',
    includes: ['Rule identification', 'Conditions and actions', 'Validation rules', 'Source traceability'],
    bestFor: 'Documentation and SME validation.'
  },
  {
    id: 'ddd_rules',
    title: 'Business Rule Extraction (DDD)',
    tokens: '150k – 300k',
    cost: 'High',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
    purpose: 'Discover the business domain behind the codebase.',
    includes: ['Bounded Contexts', 'Entities & Aggregates', 'Domain Services', 'Ubiquitous Language'],
    bestFor: 'Microservice decomposition.'
  },
  {
    id: 'full',
    title: 'Full Migration',
    tokens: '250k – 600k',
    cost: 'Very High',
    color: 'text-red-400',
    bg: 'bg-red-500/10',
    purpose: 'Execute complete modernization using the full Agentic AI pipeline.',
    includes: ['All Discovery Phases', 'Java/C# Conversion', 'Chunk Reconciliation', 'Agentic Refinement'],
    bestFor: 'Production modernization initiatives.'
  },
];

const JOURNEY_STEPS = [
  { name: 'Select Project', desc: 'Define the legacy system boundaries.' },
  { name: 'Upload Source', desc: 'Ingest COBOL files and validate syntax.' },
  { name: 'Discovery', desc: 'Map dependencies and architecture.' },
  { name: 'Knowledge Extraction', desc: 'Translate code into business rules.' },
  { name: 'Plan Migration', desc: 'Define target Java/C# architecture.' },
  { name: 'Generate Code', desc: 'Transform logic into modern artifacts.' },
  { name: 'Refinement', desc: 'Iterative compile-test-fix loop.' },
  { name: 'Deploy', desc: 'Export production-ready application.' },
];

const PIPELINE_LAYERS = [
  { range: 'Layer 1–2', title: 'Ingestion & Planning', tasks: ['File validation', 'Adaptive chunking', 'COBOL parsing'] },
  { range: 'Layer 3–5', title: 'Intel Extraction', tasks: ['Complexity scoring', 'Dependency analysis', 'Self-healing API', 'TPM throttling'] },
  { range: 'Layer 6–8', title: 'Modern Transformation', tasks: ['Java/C# conversion', 'Chunk reconciliation', 'Application assembly'] },
  { range: 'Layer 9', title: 'Agentic Refinement', tasks: ['Compile', 'Test', 'Fix', 'Optimize'] },
];

const CustomLoadingToast = ({ message, toastId }: { message: string, toastId: any }) => (
  <div className="flex items-center justify-between gap-4 bg-slate-900 border border-slate-700 text-white px-4 py-3 rounded-xl shadow-2xl min-w-[300px]">
    <div className="flex items-center gap-3">
      <Loader2 size={16} className="animate-spin text-indigo-400" />
      <span className="text-sm font-medium text-slate-200">{message}</span>
    </div>
    <button onClick={(e) => { e.stopPropagation(); toast.dismiss(toastId); }} className="p-1 hover:bg-slate-800 rounded-md text-slate-500 hover:text-white transition-colors"><X size={14} /></button>
  </div>
);

const KPICard = ({ label, value, icon: Icon, status }: any) => {
  const statusColor = status === 'Healthy' ? 'text-emerald-400' : status === 'Review' ? 'text-amber-400' : 'text-red-400';
  return (
    <div className="glass-card p-5 rounded-2xl border-slate-800 hover:border-indigo-500/50 transition-all">
      <div className="flex justify-between items-start mb-3">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{label}</span>
        <Icon size={18} className="text-slate-500" />
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      <div className={`text-[10px] font-bold mt-2 flex items-center gap-1 ${statusColor}`}>
        <div className={`w-1.5 h-1.5 rounded-full bg-current`} /> {status}
      </div>
    </div>
  );
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [isLaunching, setIsLaunching] = useState(false);
  const [selectedProject, setSelectedProject] = useState('Payroll_System_v1');
  const [sourceMetaLang, setSourceMetaLang] = useState('en');
  const [targetPlatform, setTargetPlatform] = useState('java');
  const [selectedScope, setSelectedScope] = useState('reverse');

  const handleStartMigration = async () => {
    setIsLaunching(true);
    const steps = [`Initializing ${MIGRATION_SCOPES.find(s => s.id === selectedScope)?.title}...`, `Translating metadata from ${sourceMetaLang}...`, "Connecting to Mission Control..."];
    for (const step of steps) {
      toast((t) => <CustomLoadingToast message={step} toastId={t} />, { duration: 2000, position: 'top-right' });
      await new Promise(res => setTimeout(res, 1200));
    }
    toast.success("Pipeline Deployed!");
    navigate('/mission-control');
  };

  return (
    <div className="space-y-12 pb-20 animate-in fade-in duration-700">
      
      {/* SECTION 1: WELCOME COMMAND CENTER */}
      <div className="relative overflow-hidden rounded-3xl p-8 bg-gradient-to-br from-indigo-900/40 via-slate-900 to-slate-900 border border-indigo-500/20 shadow-2xl">
        <div className="relative z-10 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/20 border border-indigo-500/30 text-indigo-400 text-xs font-bold uppercase tracking-widest">
              <Rocket size={14} /> Executive Command Center
            </div>
            <h1 className="text-5xl font-black text-white tracking-tight">Welcome to <span className="text-indigo-500">ModernizerAI</span></h1>
            <p className="text-slate-400 text-lg max-w-2xl">AI-powered legacy modernization platform for reverse engineering, business discovery, and agentic transformation.</p>
            
            <div className="flex flex-wrap gap-8 pt-4">
              <div className="space-y-1">
                <p className="text-slate-500 text-xs uppercase font-bold">Active Project</p>
                <p className="text-white font-bold text-lg">{selectedProject}</p>
              </div>
              <div className="space-y-1">
                <p className="text-slate-500 text-xs uppercase font-bold">Current Phase</p>
                <p className="text-indigo-400 font-bold text-lg">Reverse Engineering</p>
              </div>
              <div className="space-y-1">
                <p className="text-slate-500 text-xs uppercase font-bold">Overall Progress</p>
                <div className="flex items-center gap-3">
                  <p className="text-white font-bold text-lg">68%</p>
                  <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-indigo-500" style={{ width: '68%' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div className="flex flex-col gap-3 w-full md:w-auto">
            <button onClick={() => navigate('/mission-control')} className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all shadow-lg shadow-indigo-500/30 flex items-center justify-center gap-2">
              Continue Current Project <ChevronRight size={18} />
            </button>
            <button onClick={() => navigate('/projects')} className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-bold transition-all border border-slate-700 flex items-center justify-center gap-2">
              <PlusCircle size={18} /> Start New Project
            </button>
          </div>
        </div>
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-600/10 blur-[100px] rounded-full -mr-20 -mt-20" />
      </div>

      {/* SECTION 2: MODERNIZATION JOURNEY */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-slate-400 text-sm font-bold uppercase tracking-widest">
          <Info size={16} /> Modernization Journey
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
          {JOURNEY_STEPS.map((step, i) => (
            <div key={i} className="group relative p-4 bg-slate-900/50 border border-slate-800 rounded-2xl hover:border-indigo-500/50 transition-all">
              <div className="text-xs font-black text-slate-600 mb-2">0{i + 1}</div>
              <div className="text-sm font-bold text-slate-200 group-hover:text-white transition-colors">{step.name}</div>
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div className="bg-slate-800 text-white text-[10px] p-2 rounded shadow-xl w-32 text-center">{step.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SECTION 3: CURRENT CONFIGURATION */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="glass-card p-6 rounded-3xl border-slate-800 bg-slate-900/50 space-y-4">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
            <Database size={14} /> Active Project
          </label>
          <select value={selectedProject} onChange={(e) => setSelectedProject(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="Payroll_System_v1">Payroll System v1</option>
            <option value="Claims_Core_Legacy">Claims Core Legacy</option>
          </select>
        </div>

        <div className="glass-card p-6 rounded-3xl border-slate-800 bg-slate-900/50 space-y-4">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
            <Languages size={14} /> Source Metadata Language
          </label>
          <select value={sourceMetaLang} onChange={(e) => setSourceMetaLang(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="jp">Japanese</option>
            <option value="de">German</option>
            <option value="fr">French</option>
            <option value="es">Spanish</option>
          </select>
          <p className="text-[10px] text-slate-500 italic">Translates legacy comments to English for LLM accuracy.</p>
        </div>

        <div className="glass-card p-6 rounded-3xl border-slate-800 bg-slate-900/50 space-y-4">
          <label className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
            <Target size={14} /> Target Platform
          </label>
          <select value={targetPlatform} onChange={(e) => setTargetPlatform(e.target.value)} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="java">Java 21 + Spring Boot</option>
            <option value="dotnet">.NET 9</option>
            <option value="custom">Custom</option>
          </select>
        </div>
      </div>

      {/* SECTION 4: MIGRATION SCOPE & TOKEN BUDGET */}
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2 text-slate-400 text-sm font-bold uppercase tracking-widest">
            <Zap size={16} /> Migration Scope & Token Budget
          </div>
          <div className="text-[10px] text-slate-500 italic">Estimates based on ~400 COBOL programs</div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {MIGRATION_SCOPES.map((scope) => (
            <div 
              key={scope.id} 
              onClick={() => setSelectedScope(scope.id)}
              className={`p-5 rounded-2xl border transition-all cursor-pointer flex flex-col ${selectedScope === scope.id ? 'border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/20' : 'border-slate-800 bg-slate-900/50 hover:border-slate-600'}`}
            >
              <div className="flex justify-between items-start mb-4">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${scope.bg} ${scope.color}`}>{scope.cost}</span>
                {selectedScope === scope.id && <CheckCircle2 size={16} className="text-indigo-400" />}
              </div>
              <h4 className="text-white font-bold text-sm mb-2">{scope.title}</h4>
              <div className="text-xs font-mono text-indigo-400 mb-3 font-bold">{scope.tokens} Tokens</div>
              <p className="text-xs text-slate-400 mb-4 line-clamp-2">{scope.purpose}</p>
              <div className="mt-auto space-y-2">
                <div className="text-[10px] font-bold text-slate-500 uppercase">Includes:</div>
                <div className="flex flex-wrap gap-1">
                  {scope.includes.slice(0, 2).map((inc, i) => (
                    <span key={i} className="text-[9px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">{inc}</span>
                  ))}
                  {scope.includes.length > 2 && <span className="text-[9px] text-slate-500">+{scope.includes.length - 2} more</span>}
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="bg-amber-500/5 border border-amber-500/20 p-3 rounded-xl flex items-center gap-3 text-amber-500/80 text-xs">
          <AlertCircle size={14} /> Actual usage depends on project size, complexity, and prompt customization.
        </div>
      </div>

      {/* SECTION 5: THE PATH TO PRODUCTION (PIPELINE) */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-slate-400 text-sm font-bold uppercase tracking-widest">
          <Layers size={16} /> 9-Layer Pipeline Visualization
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {PIPELINE_LAYERS.map((layer, i) => (
            <div key={i} className="relative p-6 bg-slate-900 border border-slate-800 rounded-2xl space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-[10px] font-bold text-indigo-500 uppercase">{layer.range}</span>
                <div className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center text-white text-xs font-bold">{i+1}</div>
              </div>
              <h4 className="text-white font-bold">{layer.title}</h4>
              <ul className="space-y-2">
                {layer.tasks.map((task, j) => (
                  <li key={j} className="text-xs text-slate-500 flex items-center gap-2">
                    <div className="w-1 h-1 bg-indigo-500 rounded-full" /> {task}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* SECTION 6 & 7: HEALTH & RECOMMENDATIONS */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-6">
          <div className="flex items-center gap-2 text-slate-400 text-sm font-bold uppercase tracking-widest">
            <Activity size={16} /> Project Health Snapshot
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <KPICard label="Total COBOL Files" value="422" icon={FileText} status="Healthy" />
            <KPICard label="Complex Modules" value="14" icon={AlertCircle} status="Review" />
            <KPICard label="Pending Chunks" value="35" icon={Layers} status="Review" />
            <KPICard label="Verified Rules" value="16" icon={CheckCircle2} status="Healthy" />
            <KPICard label="Critical Paths" value="8" icon={GitBranch} status="Action" />
            <KPICard label="Discovered Domains" value="4" icon={Database} status="Healthy" />
          </div>
        </div>

        <div className="lg:col-span-4">
          <div className="h-full glass-card p-6 rounded-3xl border-indigo-500/30 bg-indigo-500/5 space-y-6 border">
            <div className="flex items-center gap-2 text-indigo-400 text-sm font-bold uppercase tracking-widest">
              <Lightbulb size={16} /> AI Recommendations
            </div>
            <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 space-y-3">
              <p className="text-slate-300 text-sm leading-relaxed">
                "Extract business rules before migration because <span className="text-amber-400 font-bold">14 complex modules</span> remain undocumented."
              </p>
            </div>
            <div className="grid grid-cols-1 gap-3">
              <button onClick={() => navigate('/business-logic')} className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2">
                Start Rule Extraction <ChevronRight size={14} />
              </button>
              <button onClick={() => navigate('/mission-control')} className="w-full py-3 px-4 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold transition-all border border-slate-700">
                Resume Processing
              </button>
              <button onClick={() => navigate('/source-files')} className="w-full py-3 px-4 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold transition-all border border-slate-700">
                Open Source Workspace
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* FINAL ACTION BAR */}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
        <motion.button 
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleStartMigration}
          disabled={isLaunching}
          className={`px-10 py-4 rounded-full font-black flex items-center gap-3 shadow-2xl transition-all ${isLaunching ? 'bg-slate-800 text-slate-500 cursor-not-allowed' : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-indigo-500/40'}`}
        >
          {isLaunching ? <><Loader2 className="animate-spin" size={20} /> Initializing Pipeline...</> : <><Play size={20} fill="currentColor" /> Launch Migration Pipeline</>}
        </motion.button>
      </div>
    </div>
  );
};

export default Dashboard;
