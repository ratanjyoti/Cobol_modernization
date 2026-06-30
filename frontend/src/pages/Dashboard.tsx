import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  FileText, Activity, Layers, Database, 
  ArrowUpRight, GitBranch, Play, ChevronRight, PlusCircle,
  BrainCircuit, Rocket, ShieldCheck, Info, Lightbulb, 
  CheckCircle2, Circle, Loader2, Clock, Zap,
  Languages, Settings, Globe, Cpu, Save,
  Target, Code2, AlertCircle, ChevronDown // <--- FIXED: Added ChevronDown import
} from 'lucide-react';
import toast from 'react-hot-toast';
import ConfigPanel from '../components/ConfigPanel'; 
import { ProjectAPI } from '../services/api';

// --- Types ---
type BlueprintActivity = string | { name: string; progress: number };

interface BlueprintStage {
  id: number;
  name: string;
  status: 'Complete' | 'In Progress' | 'Pending';
  indicator: 'green' | 'amber' | 'gray';
  desc: string;
  activities: BlueprintActivity[];
}

// ADDED: Type for Project History
interface ProjectHistory {
  run_id: string;
  name: string;
  status: string;
}

const BLUEPRINT_STAGES: BlueprintStage[] = [
  { id: 1, name: 'Environment Setup', status: 'Complete', indicator: 'green', desc: 'Prerequisites validated.', activities: ['AI Model Config', 'Token Budget', 'Source Lang Config'] },
  { id: 2, name: 'Discovery & Analysis', status: 'Complete', indicator: 'green', desc: 'Structure analyzed.', activities: ['Adaptive Chunking', 'Dependency Mapping', 'Complexity Analysis'] },
  { id: 3, name: 'Knowledge Extraction', status: 'In Progress', indicator: 'amber', desc: 'Business understanding construction.', activities: [{ name: 'Rule Extraction', progress: 80 }, { name: 'DDD Discovery', progress: 45 }, { name: 'HITL Validation', progress: 20 }] },
  { id: 4, name: 'Modern Code Generation', status: 'Pending', indicator: 'gray', desc: 'Components generation.', activities: ['DTO Generation', 'Domain Models', 'Service Layer'] },
  { id: 5, name: 'Agentic Refinement', status: 'Pending', indicator: 'gray', desc: 'Production hardening.', activities: ['Compile-Test-Fix', 'Unit Tests', 'Optimization'] },
];

const JOURNEY_STEPS = [
  { name: 'Select Project', path: '/projects', icon: Database },
  { name: 'Upload Source', path: '/source-files', icon: FileText },
  { name: 'Discovery', path: '/discovery', icon: BrainCircuit },
  { name: 'Knowledge Extraction', path: '/business-logic', icon: Layers },
  { name: 'Plan Migration', path: '/dashboard', icon: Target },
  { name: 'Generate Code', path: '/code-generation', icon: Code2 },
  { name: 'Refinement', path: '/mission-control', icon: ShieldCheck },
  { name: 'Deploy', path: '/code-generation', icon: Rocket },
];

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

  // --- STATE ---
  const [runId, setRunId] = useState<string | null>(localStorage.getItem('active_run_id'));
  const [projects, setProjects] = useState<ProjectHistory[]>([]); // Fixed Type
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  const [sourceMetaLang, setSourceMetaLang] = useState('en');
  const [aiMode, setAiMode] = useState<'api' | 'local'>('api');
  const [aiConfig, setAiConfig] = useState({
    key: '',
    url: 'http://localhost:11434',
    model: 'gpt-4o',
  });

  useEffect(() => {
    fetchProjectHistory();
    
    const savedLang = localStorage.getItem('modernizer_source_lang');
    const savedAiConfig = localStorage.getItem('ai_config');
    if (savedLang) setSourceMetaLang(savedLang);
    if (savedAiConfig) {
      try {
        const parsed = JSON.parse(savedAiConfig);
        setAiMode(parsed.mode || 'api');
        setAiConfig({ key: parsed.key, url: parsed.url, model: parsed.model });
      } catch (e) { console.error("Config parse error", e); }
    }
  }, []);

  const fetchProjectHistory = async () => {
    setIsLoadingProjects(true);
    try {
      const data = await ProjectAPI.list();
      setProjects(data);
    } catch (e) {
      toast.error("Failed to load project history");
    } finally {
      setIsLoadingProjects(false);
    }
  };

  const handleProjectChange = (id: string) => {
    setRunId(id);
    localStorage.setItem('active_run_id', id);
    toast.success(`Switched to project ${id}`);
  };

const getStatusStyle = (status: string | undefined) => {
  switch (status?.toLowerCase()) {
    case 'completed': 
      return 'text-emerald-400 bg-emerald-500/10';
    case 'running': 
      return 'text-amber-400 bg-amber-500/10';
    case 'incomplete': 
      return 'text-red-400 bg-red-500/10'; // Red for incomplete
    default: 
      return 'text-slate-400 bg-slate-500/10';
  }
};


  const saveLang = async (lang: string) => {
    setSourceMetaLang(lang);
    localStorage.setItem('modernizer_source_lang', lang);
    if (runId) {
      try {
        await ProjectAPI.updateConfig(runId, { lang });
        toast.success("Language updated in project");
      } catch (e) {
        toast.error("Failed to sync language to server");
      }
    }
  };

  const handleStartNewProject = async () => {
    try {
      const config = {
        project_name: "New Migration Project",
        provider: aiMode,
        model: aiConfig.model,
        lang: sourceMetaLang,
        speed_profile: 'Balanced', 
        workers: 4
      };
      
      // 1. Call the API
      const response = await ProjectAPI.create(config);
      
      // 2. CORRECTED: Access run_id directly from response
      // Because ProjectAPI.create already returns response.data
      const newRunId = response.run_id; 
      
      if (!newRunId) {
        throw new Error("Backend did not return a run_id");
      }
      
      localStorage.setItem('active_run_id', newRunId);
      setRunId(newRunId);
      
      // Refresh the dropdown list
      await fetchProjectHistory();
      
      toast.success(`Project created: ${newRunId}`);
      navigate('/source-files'); 
    } catch (e: any) {
      console.error("Full Project Creation Error:", e); // THIS HELPS US DEBUG
      toast.error(e.message || "Error creating project");
    }
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
            
            <div className="flex flex-wrap gap-8 pt-4">
              <div className="space-y-2">
                <p className="text-slate-500 text-xs uppercase font-bold">Active Project</p>
                <div className="relative group">
                  <select 
                    value={runId || ''} 
                    onChange={(e) => handleProjectChange(e.target.value)}
                    className="appearance-none pl-4 pr-10 py-2 bg-slate-950 border border-slate-700 text-white rounded-xl text-sm font-bold focus:ring-2 focus:ring-indigo-500 outline-none cursor-pointer hover:border-indigo-500 transition-all min-w-[200px]"
                  >
                    <option value="" disabled>Select a Project</option>
                    {projects.map((proj) => (
                      <option key={proj.run_id} value={proj.run_id}>
                        {/* CHANGED THIS LINE BELOW */}
                        {proj.run_id} ({proj.status})
                      </option>
                    ))}
                  </select>
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                    <ChevronDown size={14} className="text-slate-500" />
                  </div>
                </div>
                {runId && projects.find(p => p.run_id === runId) && (
                  <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase ${getStatusStyle(projects.find(p => p.run_id === runId)?.status)}`}>
                    <div className={`w-1.5 h-1.5 rounded-full bg-current`} /> 
                    {projects.find(p => p.run_id === runId)?.status}
                  </div>
                )}
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
            <button onClick={() => navigate('/projects')} className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold transition-all shadow-lg shadow-indigo-500/30 flex items-center justify-center gap-2">
              Continue Current Project <ChevronRight size={18} />
            </button>
            <button onClick={handleStartNewProject} className="px-6 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-bold transition-all border border-slate-700 flex items-center justify-center gap-2">
              <PlusCircle size={18} /> Start New Project
            </button>
          </div>
        </div>
      </div>

      {/* SECTION 2: SYSTEM CONFIGURATION */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-slate-400 text-sm font-bold uppercase tracking-widest">
          <Settings size={16} /> System & AI Configuration
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="glass-card p-6 rounded-3xl border-slate-800 bg-slate-900/50 space-y-4">
            <div className="flex items-center gap-2 text-white font-bold">
              <Languages size={18} className="text-indigo-400" /> Regional Language
            </div>
            <select 
              value={sourceMetaLang} 
              onChange={(e) => saveLang(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="jp">Japanese</option>
              <option value="de">German</option>
              <option value="fr">French</option>
              <option value="es">Spanish</option>
            </select>
            <p className="text-[10px] text-slate-500 italic leading-relaxed">
              Sets the language for prompts and source comments.
            </p>
          </div>

          <div className="lg:col-span-2 glass-card p-6 rounded-3xl border-slate-800 bg-slate-900/50">
            <ConfigPanel runId={runId} />
          </div>
        </div>
      </div>

      {/* SECTION 3: MODERNIZATION JOURNEY */}
      <div className="space-y-6">
        <div className="flex items-center gap-2 text-slate-400 text-sm font-bold uppercase tracking-widest">
          <Info size={16} /> Modernization Journey
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
          {JOURNEY_STEPS.map((step, i) => (
            <motion.div whileHover={{ y: -5 }} key={i} onClick={() => navigate(step.path)} className="group relative p-4 bg-slate-900/50 border border-slate-800 rounded-2xl hover:border-indigo-500/50 transition-all cursor-pointer">
              <div className="flex justify-between items-start mb-2">
                <div className="text-xs font-black text-slate-600">0{i + 1}</div>
                <step.icon size={14} className="text-slate-500 group-hover:text-indigo-400" />
              </div>
              <div className="text-sm font-bold text-slate-200 group-hover:text-white transition-colors">{step.name}</div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* SECTION 4: PROJECT HEALTH SNAPSHOT */}
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
            </div>
          </div>
        </div>
      </div>

      {/* SECTION 5: MODERNIZATION BLUEPRINT */}
      <div className="space-y-8">
        <div className="space-y-2">
          <h2 className="text-3xl font-bold text-white">Modernization Blueprint</h2>
          <p className="text-slate-400">Real-time execution roadmap showing the current state of the modernization pipeline.</p>
        </div>
        <div className="glass-card p-6 rounded-3xl border-slate-800 bg-slate-900/50 flex flex-col lg:flex-row items-center gap-8">
          <div className="flex-1 flex items-center justify-between w-full lg:w-auto gap-4">
            {BLUEPRINT_STAGES.map((stage, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className={`flex items-center gap-2 ${stage.status === 'Complete' ? 'text-emerald-400' : stage.status === 'In Progress' ? 'text-amber-400' : 'text-slate-600'}`}>
                  {stage.status === 'Complete' ? <CheckCircle2 size={16} /> : stage.status === 'In Progress' ? <Loader2 size={16} className="animate-spin" /> : <Circle size={16} />}
                  <span className="text-xs font-bold uppercase">{stage.name.split(' ')[0]}</span>
                </div>
                {i < BLUEPRINT_STAGES.length - 1 && <ChevronRight size={16} className="text-slate-700" />}
              </div>
            ))}
          </div>
          <div className="flex gap-4 shrink-0">
             <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[10px] font-bold">
                <div className="w-2 h-2 rounded-full bg-emerald-500" /> Env: Healthy
             </div>
             <div className="flex items-center gap-2 px-3 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[10px] font-bold">
                <div className="w-2 h-2 rounded-full bg-amber-500" /> Knowledge: Running
             </div>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6">
          {BLUEPRINT_STAGES.map((stage) => (
            <div key={stage.id} className={`p-6 rounded-3xl border transition-all ${stage.status === 'In Progress' ? 'border-amber-500/50 bg-amber-500/5 shadow-lg shadow-amber-500/10' : 'border-slate-800 bg-slate-900/50'}`}>
              <div className="flex justify-between items-center mb-4">
                <div className={`p-1.5 rounded-lg ${stage.indicator === 'green' ? 'bg-emerald-500/20 text-emerald-400' : stage.indicator === 'amber' ? 'bg-amber-500/20 text-amber-400' : 'bg-slate-800 text-slate-500'}`}>
                  {stage.status === 'Complete' ? <CheckCircle2 size={16} /> : stage.status === 'In Progress' ? <Loader2 size={16} className="animate-spin" /> : <Circle size={16} />}
                </div>
                <span className={`text-[10px] font-bold uppercase ${stage.indicator === 'green' ? 'text-emerald-400' : stage.indicator === 'amber' ? 'text-amber-400' : 'text-slate-500'}`}>{stage.status}</span>
              </div>
              <h4 className="text-white font-bold mb-2">{stage.name}</h4>
              <p className="text-slate-500 text-xs mb-6 leading-relaxed">{stage.desc}</p>
              <div className="space-y-3">
                {stage.activities.map((act, i) => {
                  const isObj = typeof act === 'object';
                  return (
                    <div key={i} className="space-y-1">
                      <div className="flex justify-between text-[10px] mb-1">
                        <span className="text-slate-400">{isObj ? act.name : act}</span>
                        {isObj && <span className="text-white font-bold">{act.progress}%</span>}
                      </div>
                      {isObj && (
                        <div className="h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                          <div className="h-full bg-amber-500 transition-all" style={{ width: `${act.progress}%` }} />
                        </div>
                      )}
                      {!isObj && <div className="flex items-center gap-1 text-emerald-500 text-[10px]"><CheckCircle2 size={10} /> Completed</div>}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* SECTION 6: WHAT'S NEXT? */}
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-white">What's Next?</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-card p-6 rounded-3xl border-indigo-500/30 bg-indigo-500/5 border space-y-4">
            <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase"><Zap size={14} /> Immediate Action</div>
            <h4 className="text-white font-bold">Review HITL Validations</h4>
            <p className="text-slate-400 text-sm">Approving remaining validations will unlock code generation.</p>
            <button onClick={() => navigate('/business-logic')} className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold transition-all">Review HITL</button>
          </div>
          <div className="glass-card p-6 rounded-3xl border-slate-800 bg-slate-900/50 space-y-4">
            <div className="flex items-center gap-2 text-slate-500 text-xs font-bold uppercase"><Clock size={14} /> Upcoming</div>
            <h4 className="text-white font-bold">Generate Java Domain Models</h4>
            <p className="text-slate-400 text-sm">Transform extracted DDD entities into Spring Boot artifacts.</p>
            <button onClick={() => navigate('/code-generation')} className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold transition-all border border-slate-700">Prepare Generation</button>
          </div>
          <div className="glass-card p-6 rounded-3xl border-slate-800 bg-slate-900/50 space-y-4">
            <div className="flex items-center gap-2 text-slate-500 text-xs font-bold uppercase"><ShieldCheck size={14} /> Final Stage</div>
            <h4 className="text-white font-bold">Run Agentic Refinement</h4>
            <p className="text-slate-400 text-sm">Perform automated compile-test-fix loops for production readiness.</p>
            <button onClick={() => navigate('/mission-control')} className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold transition-all border border-slate-700">Start Refinement</button>
          </div>
        </div>
      </div>

      {/* GLOBAL ACTION BAR */}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
        <motion.button 
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => navigate('/mission-control')}
          className="px-10 py-4 rounded-full font-black flex items-center gap-3 shadow-2xl transition-all bg-indigo-600 text-white hover:bg-indigo-500 shadow-indigo-500/40"
        >
          <Play size={20} fill="currentColor" /> Launch Migration Pipeline
        </motion.button>
      </div>
    </div>
  );
};

export default Dashboard;
