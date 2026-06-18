import React, { useState } from 'react';
import ModernizationPlan from './ModernizationPlan';
import CodeGeneration from './CodeGeneration';
import { LayoutTemplate, Code2 } from 'lucide-react';

const ModernizationHub = () => {
  const [activeView, setActiveView] = useState<'plan' | 'gen'>('plan');

  return (
    <div className="space-y-6 h-full">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Modernization Hub</h1>
          <p className="text-slate-400">From architectural blueprint to generated source code.</p>
        </div>

        <div className="flex p-1 bg-slate-900 rounded-xl border border-slate-800">
          <button 
            onClick={() => setActiveView('plan')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${activeView === 'plan' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <LayoutTemplate size={14} /> Modern Plan
          </button>
          <button 
            onClick={() => setActiveView('gen')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${activeView === 'gen' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <Code2 size={14} /> Code Generation
          </button>
        </div>
      </div>

      <div className="h-[calc(100vh-200px)]">
        {activeView === 'plan' ? <ModernizationPlan /> : <CodeGeneration />}
      </div>
    </div>
  );
};

export default ModernizationHub;