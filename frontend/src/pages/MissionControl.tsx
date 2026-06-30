import React, { useState, useEffect } from 'react';
import { 
  Activity, Zap, ShieldAlert, Cpu, 
  MessageSquare, Share2, FileText, GitBranch, Settings, 
  Pause, Play, X, Send
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const MissionControl = () => {
  const [isRunning, setIsRunning] = useState(true);
  const [progress, setProgress] = useState(34);
  const [activeExplorerTab, setActiveExplorerTab] = useState('dependencies');
  const [isConfigOpen, setIsConfigOpen] = useState(false);
  const [logs, setLogs] = useState<string[]>(["Connecting to WebSocket...", "Listening for pipeline events..."]);
  const [chatInput, setChatInput] = useState("");

  // Simulation of Live Streaming Logs
  useEffect(() => {
    if (isRunning) {
      const interval = setInterval(() => {
        const events = [
          "Chunk 42: Parsing Procedure Division...",
          "Dependency Graph: Linked ACCT-SVR to CUST-DB",
          "AI: Extracting business rule 'Overdraft-Limit'",
          "Self-Healing: Retrying Chunk 45 (Rate Limit 429)",
          "Conversion: Generating AccountService.java"
        ];
        setLogs(prev => [...prev, events[Math.floor(Math.random() * events.length)]].slice(-20));
        setProgress(p => (p < 100 ? p + 0.1 : 100));
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [isRunning]);

  return (
    <div className="h-[calc(100vh-120px)] flex flex-col gap-6">
      
      {/* TOP BAR: Metrics & Global Controls */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-card p-4 flex items-center gap-4">
          <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg"><Activity size={20}/></div>
          <div className="flex-1">
            <p className="text-[10px] font-bold text-slate-500 uppercase">Overall Progress</p>
            <div className="flex items-center gap-3">
              <span className="text-xl font-bold text-white">{progress.toFixed(1)}%</span>
              <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full bg-indigo-500 transition-all" style={{width: `${progress}%`}} />
              </div>
            </div>
          </div>
        </div>
        <div className="glass-card p-4 flex items-center gap-4">
          <div className="p-2 bg-amber-500/20 text-amber-400 rounded-lg"><Zap size={20}/></div>
          <div className="flex-1">
            <p className="text-[10px] font-bold text-slate-500 uppercase">Tokens Used</p>
            <span className="text-xl font-bold text-white">1.2M / 5M</span>
          </div>
        </div>
        <div className="glass-card p-4 flex items-center gap-4">
          <div className="p-2 bg-emerald-500/20 text-emerald-400 rounded-lg"><ShieldAlert size={20}/></div>
          <div className="flex-1">
            <p className="text-[10px] font-bold text-slate-500 uppercase">Self-Healing</p>
            <span className="text-xl font-bold text-white">12 Events</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setIsRunning(!isRunning)} className="flex-1 btn-primary flex items-center justify-center gap-2">
            {isRunning ? <><Pause size={18}/> Pause</> : <><Play size={18}/> Resume</>}
          </button>
          <button onClick={() => setIsConfigOpen(true)} className="btn-secondary p-2"><Settings size={20}/></button>
        </div>
      </div>

      {/* MAIN WORKSPACE: 3 Columns */}
      <div className="flex-1 grid grid-cols-12 gap-6 overflow-hidden">
        
        {/* LEFT: Reverse Engineering Explorer */}
        <div className="col-span-3 glass-card flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-800">
            <h3 className="font-bold text-white flex items-center gap-2"><Cpu size={18} className="text-indigo-500"/> Explorer</h3>
          </div>
          <div className="flex p-2 gap-1 bg-slate-900/50">
            {[
              { id: 'dependencies', icon: Share2, label: 'Deps' },
              { id: 'logic', icon: FileText, label: 'Logic' },
              { id: 'ddd', icon: GitBranch, label: 'DDD' },
            ].map(tab => (
              <button 
                key={tab.id}
                onClick={() => setActiveExplorerTab(tab.id)}
                className={`flex-1 flex flex-col items-center py-2 rounded-lg transition-all ${activeExplorerTab === tab.id ? 'bg-indigo-600 text-white' : 'text-slate-500 hover:bg-slate-800'}`}
              >
                <tab.icon size={16} />
                <span className="text-[10px] mt-1 font-bold">{tab.label}</span>
              </button>
            ))}
          </div>
          <div className="flex-1 p-4 overflow-y-auto">
             {activeExplorerTab === 'dependencies' && <div className="text-sm text-slate-400">Mapping Call Hierarchy...</div>}
             {activeExplorerTab === 'logic' && <div className="text-sm text-slate-400">Extracting Business Rules...</div>}
             {activeExplorerTab === 'ddd' && <div className="text-sm text-slate-400">Defining Domain Boundaries...</div>}
          </div>
        </div>

        {/* CENTER: Execution Heart */}
        <div className="col-span-6 flex flex-col gap-6">
          {/* Chunk Viewer */}
          <div className="glass-card p-4">
            <div className="flex justify-between items-center mb-4">
              <h4 className="text-sm font-bold text-slate-300">Active Chunk: <span className="text-indigo-400">#42 / 80</span></h4>
              <span className="text-[10px] px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Processing</span>
            </div>
            <div className="bg-slate-950 rounded-xl p-4 font-mono text-xs text-indigo-300 border border-slate-800">
              <div><span className="text-slate-600">Line 120:</span> PERFORM CALCULATE-BALANCE</div>
              <div><span className="text-slate-600">Line 121:</span> IF WS-BAL &lt; 0 ...</div>
            </div>
          </div>

          {/* Terminal Console */}
          <div className="flex-1 bg-slate-950 rounded-2xl border border-slate-800 overflow-hidden flex flex-col shadow-2xl">
            <div className="bg-slate-900 px-4 py-2 border-b border-slate-800 flex justify-between items-center">
              <div className="flex gap-1.5">
                <div className="w-3 h-3 rounded-full bg-red-500/50" />
                <div className="w-3 h-3 rounded-full bg-amber-500/50" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/50" />
              </div>
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-widest">system_log_stream</span>
            </div>
            <div className="p-4 font-mono text-xs overflow-y-auto flex-1 space-y-2">
              {logs.map((log, i) => (
                <div key={i} className="flex gap-3">
                  <span className="text-slate-600 shrink-0">[{new Date().toLocaleTimeString()}]</span>
                  <span className={log.includes('Healing') ? 'text-amber-400' : 'text-emerald-400'}>{log}</span>
                </div>
              ))}
              {isRunning && <div className="text-indigo-400 animate-pulse">_ awaiting_next_chunk...</div>}
            </div>
          </div>
        </div>

        {/* RIGHT: Modernizer AI Assistant */}
        <div className="col-span-3 glass-card flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center gap-2">
            <MessageSquare size={18} className="text-indigo-500" />
            <h3 className="font-bold text-white">AI Analyst</h3>
          </div>
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            <div className="bg-slate-800/50 p-3 rounded-2xl rounded-tl-none text-xs text-slate-300">
              Hello! I am monitoring your migration. Ask me about any chunk or rule.
            </div>
          </div>
          <div className="p-4 border-t border-slate-800 flex gap-2">
            <input 
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white outline-none focus:ring-1 focus:ring-indigo-500" 
              placeholder="Ask about a rule..." 
            />
            <button onClick={() => setChatInput("")} className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-all">
              <Send size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Config Drawer (Slide-out) */}
      <AnimatePresence>
        {isConfigOpen && (
          <motion.div 
            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
            className="fixed right-0 top-0 h-full w-80 bg-slate-900 border-l border-slate-800 z-[100] p-6 shadow-2xl"
          >
            <div className="flex justify-between items-center mb-8">
              <h3 className="font-bold text-white">System Config</h3>
              <button onClick={() => setIsConfigOpen(false)} className="text-slate-500 hover:text-white"><X size={20}/></button>
            </div>
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-500 uppercase">Target Language</label>
                <select className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-sm text-white">
                  <option>Java 21 (Spring Boot)</option>
                  <option>C# 12 (.NET 8)</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-500 uppercase">Token Budget</label>
                <input type="number" className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-sm text-white" defaultValue={5000000} />
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <span className="text-xs text-slate-300">Self-Healing Loop</span>
                <div className="w-10 h-5 bg-indigo-600 rounded-full relative cursor-pointer">
                  <div className="absolute right-1 top-1 w-3 h-3 bg-white rounded-full" />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default MissionControl;
