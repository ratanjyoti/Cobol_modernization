import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileText, Zap, CheckCircle2, Activity, Layers, 
  Database, ArrowUpRight, Play, Loader2, 
  Upload, GitBranch, Languages, Code, 
  ChevronRight, HelpCircle, AlertCircle, PlusCircle,
  BookOpen, BrainCircuit, Rocket, ShieldCheck
} from 'lucide-react';
import toast from 'react-hot-toast';

// --- Types & Data ---
type MigrationScope = 'mapping' | 'reverse' | 'full';
type RulePrecision = 'plain' | 'ddd';

const SCOPE_CONFIG = {
  mapping: { label: 'Dependency Mapping', cost: 'Low', color: 'text-emerald-400', bg: 'bg-emerald-500/10', desc: 'Visualize architecture & connections only.' },
  reverse: { label: 'Reverse Engineering', cost: 'Medium', color: 'text-amber-400', bg: 'bg-amber-500/10', desc: 'Extract logic, complexity & rules.' },
  full: { label: 'Full Migration', cost: 'High', color: 'text-red-400', bg: 'bg-red-500/10', desc: 'End-to-end conversion with Agentic Refinement.' },
};

const ROADMAP_STEPS = [
  { 
    title: "Ingestion & Planning", 
    layer: "Layers 1-2", 
    desc: "File size check, adaptive chunking (300-line overlap), and initial COBOL parsing.", 
    icon: Upload 
  },
  { 
    title: "Intel Extraction", 
    layer: "Layers 3-5", 
    desc: "Complexity scoring, TPM throttling, and self-healing API loops to ensure zero data loss.", 
    icon: BrainCircuit 
  },
  { 
    title: "Modern Transformation", 
    layer: "Layers 6-8", 
    desc: "Java/C# conversion, reconciliation of chunks, and unified application structuring.", 
    icon: Code 
  },
  { 
    title: "Agentic Refinement", 
    layer: "Layer 9", 
    desc: "Iterative Compile-Test-Fix loop to produce production-ready, optimized code.", 
    icon: ShieldCheck 
  },
];

const KPICard = ({ label, value, icon: Icon, subtext }: any) => (
  <div className="glass-card p-6 rounded-2xl border-slate-800 hover:border-indigo-500/50 transition-all group">
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
  
  // --- State ---
  const [isLaunching, setIsLaunching] = useState(false);
  const [selectedProject, setSelectedProject] = useState('Payroll_System_v1');
  const [sourceMetaLang, setSourceMetaLang] = useState('en');
  const [migrationScope, setMigrationScope] = useState<MigrationScope>('reverse');
  const [rulePrecision, setRulePrecision] = useState<RulePrecision>('plain');
  
  // Ingestion states from previous version
  const [inputMethod, setInputMethod] = useState<'file' | 'github'>('file');
  const [targetLang, setTargetLang] = useState('java');
  const [githubUrl, setGithubUrl] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);

  const handleStartMigration = async () => {
    setIsLaunching(true);
    
    // Simulating pipeline initialization based on selected scope
    const steps = [
      `Initializing ${SCOPE_CONFIG[migrationScope].label}...`,
      `Configuring ${sourceMetaLang} translation bridge...`,
      `Setting token budget for ${rulePrecision === 'ddd' ? 'DDD' : 'Plain'} extraction...`,
      "Connecting to Mission Control..."
    ];

    for (const step of steps) {
        toast.loading(step);
        await new Promise(res => setTimeout(res, 800));
    }

    toast.success("Pipeline Deployed Successfully!");
    navigate('/mission-control');
  };

  return (
    <div className="space-y-10 pb-20">
      {/* HEADER */}
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <h1 className="text-4xl font-extrabold text-white tracking-tight">Command Center</h1>
          <p className="text-slate-400 text-lg max-w-2xl">
            Orchestrate your legacy migration. Configure AI behavior and project scope before launch.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT COLUMN: CONFIGURATION (8 Cols) */}
        <div className="lg:col-span-8 space-y-8">
          
          {/* Section 1: Project & Language Gateway */}
          <div className="glass-card p-8 rounded-3xl border-slate-800 bg-slate-900/50 shadow-2xl">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-2 bg-indigo-600 rounded-lg text-white"><Database size={20}/></div>
              <h2 className="text-xl font-bold text-white">Project & Language Context</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Active Project</label>
                <div className="flex gap-2">
                  <select 
                    value={selectedProject}
                    onChange={(e) => setSelectedProject(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 appearance-none"
                  >
                    <option value="Payroll_System_v1">Payroll System v1</option>
                    <option value="Claims_Core_Legacy">Claims Core Legacy</option>
                    <option value="Cust_Data_Mainframe">Cust Data Mainframe</option>
                  </select>
                  <button className="p-3 bg-slate-800 hover:bg-indigo-600 text-white rounded-xl transition-colors" title="New Project">
                    <PlusCircle size={20} />
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                  <Languages size={14}/> Source Metadata Language
                </label>
                <select 
                  value={sourceMetaLang}
                  onChange={(e) => setSourceMetaLang(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 appearance-none"
                >
                  <option value="en">English</option>
                  <option value="es">Spanish (Español)</option>
                  <option value="de">German (Deutsch)</option>
                  <option value="fr">French (Français)</option>
                  <option value="jp">Japanese (日本語)</option>
                </select>
                <p className="text-[10px] text-slate-500 italic flex items-center gap-1">
                  <HelpCircle size={10}/> Translates COBOL comments to English for LLM optimization.
                </p>
              </div>
            </div>
          </div>

          {/* Section 2: Service Scope & Token Planner */}
          <div className="glass-card p-8 rounded-3xl border-slate-800 bg-slate-900/50 shadow-2xl">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-2 bg-amber-600 rounded-lg text-white"><Zap size={20}/></div>
              <h2 className="text-xl font-bold text-white">Migration Scope & Token Budget</h2>
            </div>

            <div className="space-y-8">
              {/* Migration Depth */}
              <div className="space-y-4">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Migration Depth</label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {(Object.keys(SCOPE_CONFIG) as MigrationScope[]).map((key) => (
                    <div 
                      key={key}
                      onClick={() => setMigrationScope(key)}
                      className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                        migrationScope === key 
                        ? 'border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/20' 
                        : 'border-slate-800 bg-slate-950 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${SCOPE_CONFIG[key].bg} ${SCOPE_CONFIG[key].color}`}>
                          {SCOPE_CONFIG[key].cost} Tokens
                        </span>
                        {migrationScope === key && <CheckCircle2 size={16} className="text-indigo-400" />}
                      </div>
                      <h4 className="text-white font-bold text-sm mb-1">{SCOPE_CONFIG[key].label}</h4>
                      <p className="text-xs text-slate-500">{SCOPE_CONFIG[key].desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Business Rule Precision */}
              <div className="space-y-4">
                <label className="text-xs font-bold text-slate-500 uppercase tracking-widest">Business Rule Precision</label>
                <div className="flex gap-4">
                  <button 
                    onClick={() => setRulePrecision('plain')}
                    className={`flex-1 p-4 rounded-2xl border text-left transition-all ${
                      rulePrecision === 'plain' ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-800 bg-slate-950'
                    }`}
                  >
                    <div className="font-bold text-white text-sm">Plain Extraction</div>
                    <div className="text-xs text-slate-500">Simple functional rules. (Low Cost)</div>
                  </button>
                  <button 
                    onClick={() => setRulePrecision('ddd')}
                    className={`flex-1 p-4 rounded-2xl border text-left transition-all ${
                      rulePrecision === 'ddd' ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-800 bg-slate-950'
                    }`}
                  >
                    <div className="font-bold text-white text-sm">DDD-Driven Extraction</div>
                    <div className="text-xs text-slate-500">Map to Bounded Contexts & Entities. (High Cost)</div>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: Guided Roadmap */}
          <div className="glass-card p-8 rounded-3xl border-slate-800 bg-slate-900/50 shadow-2xl">
            <div className="flex items-center gap-3 mb-8">
              <div className="p-2 bg-emerald-600 rounded-lg text-white"><BookOpen size={20}/></div>
              <h2 className="text-xl font-bold text-white">The Path to Production</h2>
            </div>
            <div className="relative space-y-8 pl-8">
              <div className="absolute left-3 top-2 bottom-2 w-0.5 bg-slate-800" />
              {ROADMAP_STEPS.map((step, i) => (
                <div key={i} className="relative flex gap-6 group">
                  <div className="absolute -left-8 top-1 w-4 h-4 rounded-full bg-slate-900 border-2 border-indigo-500 group-hover:bg-indigo-500 transition-colors" />
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-bold text-indigo-400 uppercase tracking-tighter">{step.layer}</span>
                      <h4 className="text-white font-bold">{step.title}</h4>
                    </div>
                    <p className="text-sm text-slate-500 max-w-xl">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: EXECUTION & STATS (4 Cols) */}
        <div className="lg:col-span-4 space-y-8">
          
          {/* Launch Panel */}
          <div className="glass-card p-8 rounded-3xl border-slate-800 bg-indigo-600/10 border-indigo-500/30 shadow-2xl flex flex-col items-center text-center space-y-6">
            <div className="p-4 bg-indigo-600 rounded-full text-white shadow-xl shadow-indigo-500/40">
              <Rocket size={32} />
            </div>
            <div className="space-y-2">
              <h3 className="text-xl font-bold text-white">Ready for Launch</h3>
              <p className="text-sm text-slate-400">All 9 layers of the pipeline are configured and online.</p>
            </div>
            <motion.button 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleStartMigration}
              disabled={isLaunching}
              className={`w-full py-4 rounded-2xl font-bold flex items-center justify-center gap-3 transition-all ${
                isLaunching 
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed' 
                : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-500/30'
              }`}
            >
              {isLaunching ? (
                <><Loader2 className="animate-spin" size={20} /> Initializing...</>
              ) : (
                <><Play size={20} fill="currentColor" /> Start Migration</>
              )}
            </motion.button>
            <div className="flex items-center gap-2 text-[10px] text-amber-500 uppercase font-bold">
              <AlertCircle size={12} />
              <span>Estimated Token Load: {SCOPE_CONFIG[migrationScope].cost}</span>
            </div>
          </div>

          {/* Current Health Snapshot */}
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest px-2">Project Health Snapshot</h3>
            <div className="grid grid-cols-1 gap-4">
              <KPICard label="Total COBOL Files" value="422" icon={FileText} subtext="Priority view active" />
              <KPICard label="Complex Modules" value="14" icon={Activity} subtext="Needs review" />
              <KPICard label="Pending Chunks" value="35" icon={Layers} subtext="Processing queue" />
              <KPICard label="Verified Rules" value="16" icon={CheckCircle2} subtext="Ready to convert" />
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

export default Dashboard;
