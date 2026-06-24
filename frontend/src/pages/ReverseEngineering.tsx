import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { 
  LayoutDashboard, Share2, FileText, GitBranch, 
  AlertTriangle, FileCheck, Info, ChevronRight,
  Database, Download, X 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// --- MOCK API DATA (Simulating Backend Response) ---
const MOCK_DATA = {
  stats: {
    totalPrograms: 120,
    totalLines: 450000,
    dependencies: 3400,
    businessRules: 890,
    avgComplexity: 12.4,
  },
  dependencies: {
    nodes: [
      { id: 'P1', label: 'PAYROLL01', type: 'PROGRAM', risk: 'High' },
      { id: 'P2', label: 'TAXCALC', type: 'PROGRAM', risk: 'Medium' },
      { id: 'P3', label: 'CUST-DB', type: 'FILE', risk: 'Low' },
      { id: 'P4', label: 'REPORTGEN', type: 'PROGRAM', risk: 'Low' },
    ],
    edges: [
      { from: 'P1', to: 'P2', type: 'CALLS' },
      { from: 'P2', to: 'P3', type: 'READS' },
      { from: 'P1', to: 'P4', type: 'CALLS' },
    ]
  },
  rules: [
    { id: 'R1', title: 'Overdraft Limit', cobol: 'IF BAL < 0 PERFORM PENALTY', english: 'If account balance is negative, apply penalty fee.', status: 'Verified' },
    { id: 'R2', title: 'Tax Calc', cobol: 'COMPUTE TAX = SAL * 0.2', english: 'Calculate tax at 20% for salaries above 50k.', status: 'Review' },
    { id: 'R3', title: 'Customer Validation', cobol: 'IF CUST-ID NOT FOUND STOP', english: 'Verify customer existence before processing.', status: 'Verified' },
  ],
  domains: [
    { name: 'Account Management', programs: ['ACCT01', 'ACCT02'], rules: 45, color: 'bg-blue-500' },
    { name: 'Payment Processing', programs: ['PAY01', 'PAY05'], rules: 120, color: 'bg-emerald-500' },
    { name: 'Loan Management', programs: ['LOAN01', 'LOAN08'], rules: 80, color: 'bg-purple-500' },
  ],
  complexity: [
    { name: 'PAYROLL01', score: 18, level: 'HIGH', factors: ['EXEC SQL', 'CICS'] },
    { name: 'TAXCALC', score: 12, level: 'MEDIUM', factors: ['Nested PERFORM'] },
    { name: 'REPORTGEN', score: 4, level: 'LOW', factors: ['Simple I/O'] },
  ]
};

const ReverseEngineering = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedNode, setSelectedNode] = useState<(typeof MOCK_DATA.dependencies.nodes)[number] | null>(null);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'dependencies', label: 'Dependencies', icon: Share2 },
    { id: 'logic', label: 'Business Logic', icon: FileText },
    { id: 'ddd', label: 'DDD Discovery', icon: GitBranch },
    { id: 'complexity', label: 'Complexity', icon: AlertTriangle },
    { id: 'reports', label: 'Reports', icon: FileCheck },
  ];

  return (
    <div className="space-y-6 h-full">
      {/* Header */}
      <div className="flex justify-between items-end">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Reverse Engineering Explorer</h1>
          <p className="text-slate-400">Transforming raw COBOL into structured architectural intelligence.</p>
        </div>
        <div className="flex gap-3">
          <button className="btn-secondary flex items-center gap-2 text-sm"><Database size={16}/> Sync Graph</button>
          <button className="btn-primary flex items-center gap-2 text-sm"><Download size={16}/> Export Model</button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-2 p-1 bg-slate-900 rounded-xl border border-slate-800 w-fit">
        {tabs.map(tab => (
          <button 
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              activeTab === tab.id ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
            }`}
          >
            <tab.icon size={14} /> {tab.label}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-300px)]">
        <div className="col-span-9 glass-card p-6 overflow-y-auto relative">
          
          <AnimatePresence mode="wait">
            {activeTab === 'overview' && (
              <motion.div 
                key="overview"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} 
                className="grid grid-cols-3 gap-4"
              >
                {Object.entries(MOCK_DATA.stats).map(([key, val]) => (
                  <div key={key} className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                    <p className="text-xs font-bold text-slate-500 uppercase">{key.replace(/([A-Z])/g, ' $1')}</p>
                    <p className="text-2xl font-black text-white">{val}</p>
                  </div>
                ))}
              </motion.div>
            )}

            {activeTab === 'dependencies' && (
              <motion.div 
                key="dependencies"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} 
                className="h-full flex items-center justify-center bg-slate-950 rounded-xl border border-slate-800 relative overflow-hidden"
              >
                <div className="absolute inset-0 opacity-20" style={{backgroundImage: 'radial-gradient(#4f46e5 1px, transparent 1px)', backgroundSize: '30px 30px'}} />
                <div className="relative flex gap-12 items-center">
                  {MOCK_DATA.dependencies.nodes.map(node => (
                    <div 
                      key={node.id} 
                      onClick={() => setSelectedNode(node)}
                      className="w-32 h-32 rounded-full bg-slate-900 border-2 border-indigo-500 flex flex-col items-center justify-center cursor-pointer hover:scale-110 transition-all shadow-lg shadow-indigo-500/20"
                    >
                      <span className="text-[10px] text-slate-500 font-bold">{node.type}</span>
                      <span className="text-xs font-bold text-white">{node.label}</span>
                    </div>
                  ))}
                </div>
                <div className="absolute bottom-4 left-4 text-[10px] text-slate-500 font-mono">Graph View: Interactive Node Map</div>
              </motion.div>
            )}

            {activeTab === 'logic' && (
              <motion.div 
                key="logic"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} 
                className="space-y-6"
              >
                <div className="flex justify-between items-center">
                  <h3 className="text-white font-bold">Extracted Logic Preview</h3>
                  <Link 
                    to="/business-logic" 
                    className="text-xs bg-indigo-600 text-white px-3 py-1.5 rounded-lg font-bold hover:bg-indigo-500 transition-all flex items-center gap-1"
                  >
                    Manage All Rules <ChevronRight size={14} />
                  </Link>
                </div>
                <div className="grid grid-cols-1 gap-4">
                  {MOCK_DATA.rules.slice(0, 2).map(rule => (
                    <div key={rule.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-indigo-500 transition-all group">
                      <div className="flex justify-between mb-3">
                        <span className="text-sm font-bold text-white">{rule.title}</span>
                        <span className={`status-pill ${rule.status === 'Verified' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>{rule.status}</span>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 font-mono text-xs text-indigo-300 truncate">{rule.cobol}</div>
                        <div className="p-3 bg-slate-800/50 rounded-lg border border-slate-700 text-xs text-slate-300 italic truncate">{rule.english}</div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="p-4 rounded-xl bg-indigo-500/5 border border-indigo-500/20 text-center">
                  <p className="text-xs text-slate-500">
                    Showing 2 of {MOCK_DATA.rules.length} extracted rules. 
                    <Link to="/business-logic" className="text-indigo-400 ml-1 hover:underline">View full library $\rightarrow$</Link>
                  </p>
                </div>
              </motion.div>
            )}

            {activeTab === 'ddd' && (
              <motion.div 
                key="ddd"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} 
                className="grid grid-cols-2 gap-6"
              >
                {MOCK_DATA.domains.map(domain => (
                  <div key={domain.name} className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-4">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${domain.color}`} />
                      <h4 className="font-bold text-white">{domain.name}</h4>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {domain.programs.map(p => <span key={p} className="text-[10px] bg-slate-800 text-slate-400 px-2 py-1 rounded border border-slate-700">{p}</span>)}
                    </div>
                    <div className="text-xs text-slate-500">Extracted {domain.rules} business rules</div>
                  </div>
                ))}
              </motion.div>
            )}

            {activeTab === 'complexity' && (
              <motion.div 
                key="complexity"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} 
                className="space-y-4"
              >
                {MOCK_DATA.complexity.map(item => (
                  <div key={item.name} className="flex items-center gap-4 p-4 rounded-xl bg-slate-900 border border-slate-800">
                    <div className={`w-3 h-3 rounded-full ${item.level === 'HIGH' ? 'bg-red-500' : item.level === 'MEDIUM' ? 'bg-amber-500' : 'bg-emerald-500'}`} />
                    <span className="flex-1 text-sm font-bold text-white">{item.name}</span>
                    <span className="text-xs font-mono text-slate-500">Score: {item.score}</span>
                    <div className="flex gap-2">
                      {item.factors.map(f => <span key={f} className="text-[10px] bg-slate-800 px-2 py-1 rounded text-slate-400">{f}</span>)}
                    </div>
                  </div>
                ))}
              </motion.div>
            )}

            {activeTab === 'reports' && (
              <motion.div 
                key="reports"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} 
                className="space-y-6"
              >
                <div className="p-6 bg-indigo-600/10 border border-indigo-500/30 rounded-2xl">
                  <h3 className="text-lg font-bold text-white mb-2">Migration Readiness: 68%</h3>
                  <p className="text-sm text-slate-400">The system is largely ready for Java conversion. Highest risk detected in PAYMENT-ENGINE due to heavy CICS dependencies.</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                   <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
                      <p className="text-xs font-bold text-slate-500 mb-2">Bottlenecks</p>
                      <p className="text-sm text-white">CUST-DB access is a single point of failure for 12 programs.</p>
                   </div>
                   <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl">
                      <p className="text-xs font-bold text-slate-500 mb-2">Effort Estimate</p>
                      <p className="text-sm text-white">Estimated 450 developer-hours for manual rule validation.</p>
                   </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* RIGHT: Node Detail View */}
        <div className="col-span-3 glass-card p-6 border-indigo-500/30 bg-indigo-500/5">
          {selectedNode ? (
            <div className="space-y-6">
              <div className="flex justify-between items-center">
                <h3 className="text-xl font-bold text-white">{selectedNode.label}</h3>
                <button onClick={() => setSelectedNode(null)} className="text-slate-500 hover:text-white transition-colors">
                  <X size={18}/>
                </button>
              </div>
              <div className="space-y-4">
                <div className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                  <p className="text-xs font-bold text-slate-500 uppercase mb-1">Analysis</p>
                  <p className="text-sm text-slate-300 italic">"This program manages the core payroll logic and calculates monthly tax based on state codes."</p>
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-bold text-slate-500 uppercase">Dependencies</p>
                  <div className="flex flex-wrap gap-2">
                    {MOCK_DATA.dependencies.edges
                      .filter(e => e.from === selectedNode.id || e.to === selectedNode.id)
                      .map((e, i) => (
                        <span key={i} className="text-[10px] bg-slate-800 px-2 py-1 rounded border border-slate-700 text-slate-300">{e.type}</span>
                      ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
              <Info size={40} className="text-slate-600" />
              <p className="text-sm text-slate-500">Select a node from the graph to view detailed intelligence</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReverseEngineering;
