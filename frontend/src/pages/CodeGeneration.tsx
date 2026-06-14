import { useState } from 'react';
import { Download, Copy, CheckCircle2, ChevronRight, Search } from 'lucide-react';
import { motion } from 'framer-motion';

const artifacts = [
  { id: '1', name: 'AccountService.java', type: 'Service', readiness: 92, status: 'Verified' },
  { id: '2', name: 'CustomerEntity.java', type: 'Entity', readiness: 88, status: 'Verified' },
  { id: '3', name: 'AccountRepository.java', type: 'Repository', readiness: 76, status: 'Review' },
  { id: '4', name: 'TransactionDTO.java', type: 'DTO', readiness: 61, status: 'Review' },
];

const CodeGeneration = () => {
  const [selectedId, setSelectedId] = useState('1');
  const selected = artifacts.find(a => a.id === selectedId);

  return (
    <div className="h-[calc(100vh-160px)] flex gap-6">
      <div className="w-1/3 flex flex-col gap-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-bold text-white">Artifacts</h2>
          <button className="btn-secondary text-xs">Regenerate</button>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
          <input type="text" placeholder="Find artifact..." className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500" />
        </div>
        <div className="grid grid-cols-1 gap-3 overflow-y-auto">
          {artifacts.map(item => (
            <motion.div 
              key={item.id}
              onClick={() => setSelectedId(item.id)}
              className={`p-4 rounded-xl cursor-pointer border transition-all ${selectedId === item.id ? 'bg-indigo-500/10 border-indigo-500' : 'bg-slate-900 border-slate-800 hover:border-slate-700'}`}
            >
              <div className="flex justify-between mb-2">
                <span className="text-sm font-semibold text-white">{item.name}</span>
                <span className={`status-pill ${item.status === 'Verified' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>{item.status}</span>
              </div>
              <div className="flex items-center justify-between text-[10px] text-slate-500">
                <span>{item.type}</span>
                <span>{item.readiness}% Ready</span>
              </div>
              <div className="h-1 w-full bg-slate-800 rounded-full mt-2 overflow-hidden">
                <div className={`h-full ${item.status === 'Verified' ? 'bg-emerald-500' : 'bg-amber-500'}`} style={{ width: `${item.readiness}%` }} />
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      <div className="flex-1 flex flex-col gap-6">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2 text-slate-500 text-sm">
            <span>Artifacts</span> <ChevronRight size={14} /> <span className="text-white font-medium">{selected?.name}</span>
          </div>
          <button className="btn-primary flex items-center gap-2"><Download size={16} /> Export Project</button>
        </div>
        <div className="flex-1 glass-card p-8 flex flex-col">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h3 className="text-2xl font-bold text-white mb-1">{selected?.name}</h3>
              <p className="text-slate-400 text-sm">Modernized Java 21 implementation.</p>
            </div>
            <button className="btn-secondary flex items-center gap-2 px-3 py-1.5"><Copy size={14} /> Copy</button>
          </div>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <p className="text-xs font-bold text-slate-500 uppercase mb-2">Coverage</p>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-600" style={{ width: `${selected?.readiness}%` }} />
                </div>
                <span className="text-sm font-bold text-white">{selected?.readiness}%</span>
              </div>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <p className="text-xs font-bold text-slate-500 uppercase mb-2">Complexity</p>
              <span className="text-lg font-bold text-white">Medium</span>
            </div>
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
              <p className="text-xs font-bold text-slate-500 uppercase mb-2">Verification</p>
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm"><CheckCircle2 size={16} /> Passed</div>
            </div>
          </div>
          <div className="flex-1 bg-slate-950 rounded-xl p-6 font-mono text-sm text-indigo-300 overflow-auto border border-slate-800">
            <pre>{`public class ${selected?.name.replace('.java', '')} {\n  @Service\n  public void process() {\n    // AI Modernized Logic\n    if (balance < 0) applyPenalty();\n  }\n}`}</pre>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CodeGeneration;
