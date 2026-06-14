import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, Zap, CheckCircle2, Activity, Layers, Database, ArrowUpRight, Play, Loader2 } from 'lucide-react';

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
  const [isLaunching, setIsLaunching] = useState(false);

  // THIS IS THE MIGRATION TRIGGER LOGIC
  const handleStartMigration = async () => {
    setIsLaunching(true);
    
    // 1. Simulate the "Launching Sequence" (making it feel professional)
    // In a real app, this would be calling the Backend API to create a Job
    const steps = ["Initializing System...", "Connecting to LLM...", "Loading Project State..."];
    
    for (const step of steps) {
        console.log(step); // You could also use a toast notification here
        await new Promise(res => setTimeout(res, 800));
    }

    // 2. Navigate to the Mission Control Tab
    navigate('/mission-control');
  };

  return (
    <div className="space-y-10">
      {/* TOP SECTION: Header and the BIG MIGRATION BUTTON */}
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <h1 className="text-4xl font-extrabold text-white tracking-tight">Migration Dashboard</h1>
          <p className="text-slate-400 text-lg max-w-2xl">
            Your COBOL source files are indexed. Ready to transform legacy logic into modern Java 21.
          </p>
        </div>

        {/* THE MIGRATION BUTTON */}
        <motion.button 
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleStartMigration}
          disabled={isLaunching}
          className={`px-8 py-4 rounded-2xl font-bold flex items-center gap-3 shadow-xl transition-all ${
            isLaunching 
            ? 'bg-slate-700 text-slate-400 cursor-not-allowed shadow-none' 
            : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-indigo-500/30'
          }`}
        >
          {isLaunching ? (
            <>
              <Loader2 className="animate-spin" size={20} /> 
              Launching Pipeline...
            </>
          ) : (
            <>
              <Play size={20} fill="currentColor" /> 
              Start Migration
            </>
          )}
        </motion.button>
      </div>

      {/* HERO BANNER */}
      <div className="bg-gradient-to-br from-indigo-600 to-violet-700 p-8 rounded-3xl text-white shadow-xl shadow-indigo-500/20 flex justify-between items-center">
        <div className="space-y-2">
          <h2 className="text-2xl font-bold">Project: COBOL_Migration_2024</h2>
          <p className="opacity-80 text-sm max-w-xl">
            Target Architecture: <span className="font-bold underline">Spring Boot 3.2 + PostgreSQL</span>. 
            Estimated conversion time: 4.5 hours.
          </p>
        </div>
        <div className="hidden md:block bg-white/20 p-4 rounded-2xl backdrop-blur-md border border-white/10 text-right">
          <p className="text-xs uppercase font-bold opacity-70">Current Status</p>
          <p className="text-lg font-bold">Ready to Launch</p>
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
