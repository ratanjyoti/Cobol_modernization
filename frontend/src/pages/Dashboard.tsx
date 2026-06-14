import { FileText, CheckCircle2, Activity, Layers, ArrowUpRight, type LucideIcon } from 'lucide-react';

type KPICardProps = {
  label: string;
  value: string;
  icon: LucideIcon;
  subtext: string;
};
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Play, Loader2 } from 'lucide-react';

// Inside Dashboard component...
const [isLaunching, setIsLaunching] = useState(false);
const navigate = useNavigate();

const handleStartMigration = async () => {
  setIsLaunching(true);
  
  // Simulate the "Initializing" sequence
  const sequences = ["Creating Migration Job...", "Connecting to LLM...", "Initializing WebSocket..."];
  for (const seq of sequences) {
    // We could use a toast here to show these messages
    await new Promise(res => setTimeout(res, 800));
  }
  
  // Navigate to Mission Control
  navigate('/mission-control');
};

// In the JSX:
<motion.button 
  whileHover={{ scale: 1.02 }}
  whileTap={{ scale: 0.98 }}
  onClick={handleStartMigration}
  className="bg-indigo-600 text-white px-8 py-4 rounded-2xl font-bold flex items-center gap-3 shadow-xl shadow-indigo-500/30 transition-all"
>
  {isLaunching ? (
    <>
      <Loader2 className="animate-spin" size={20} /> 
      Initializing System...
    </>
  ) : (
    <>
      <Play size={20} fill="currentColor" /> 
      Start Migration
    </>
  )}
</motion.button>

const KPICard = ({ label, value, icon: Icon, subtext }: KPICardProps) => (
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
  return (
    <div className="space-y-10">
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <h1 className="text-4xl font-extrabold text-white tracking-tight">Migration Dashboard</h1>
          <p className="text-slate-400 text-lg max-w-2xl">AI-powered COBOL analysis and automated Java modernization workflow.</p>
        </div>
        <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-400 px-4 py-2 rounded-full text-sm font-bold border border-emerald-500/20">
          <CheckCircle2 size={18} /> 422 files validated
        </div>
      </div>

      <div className="bg-gradient-to-br from-indigo-600 to-violet-700 p-8 rounded-3xl text-white shadow-xl shadow-indigo-500/20">
        <h2 className="text-2xl font-bold mb-2">System Ready for Analysis</h2>
        <p className="opacity-80 text-sm max-w-xl">Your AI models are connected. Upload COBOL source files to begin the reverse engineering process.</p>
      </div>

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
