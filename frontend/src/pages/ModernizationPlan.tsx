import { CheckCircle2, Circle, Zap } from 'lucide-react';

const ModernizationPlan = () => {
  const phases = [
    { name: 'Environment Setup', status: 'Complete', tasks: ['AI Model Config', 'Token Budgeting'] },
    { name: 'Analysis Phase', status: 'Complete', tasks: ['Chunking', 'Dependency Mapping'] },
    { name: 'Logic Extraction', status: 'In Progress', tasks: ['Business Rule Mapping', 'HITL Approval'] },
    { name: 'Code Generation', status: 'Pending', tasks: ['DTO Creation', 'Service Layer', 'Controller Implementation'] },
    { name: 'Refinement', status: 'Pending', tasks: ['Agentic Compilation', 'Unit Test Generation'] },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Modernization Plan</h1>
        <p className="text-slate-400">The generated blueprint for transforming COBOL into a modern application.</p>
      </div>

      <div className="max-w-4xl space-y-8">
        {phases.map((phase, i) => (
          <div key={i} className="relative pl-8 border-l-2 border-slate-700 pb-8 last:pb-0">
            {/* Timeline Circle */}
            <div className={`absolute -left-3 top-0 w-5 h-5 rounded-full border-4 border-darkbg ${
              phase.status === 'Complete' ? 'bg-green-500' : 
              phase.status === 'In Progress' ? 'bg-accent animate-pulse' : 'bg-slate-600'
            }`} />
            
            <div className="bg-panel border border-slate-700 rounded-xl p-6 shadow-lg">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-white font-bold text-lg">{phase.name}</h3>
                <span className={`text-xs px-3 py-1 rounded-full font-bold ${
                  phase.status === 'Complete' ? 'bg-green-500/10 text-green-400' : 
                  phase.status === 'In Progress' ? 'bg-accent/10 text-accent' : 'bg-slate-700 text-slate-400'
                }`}>
                  {phase.status}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {phase.tasks.map((task, j) => (
                  <div key={j} className="flex items-center gap-2 text-sm text-slate-400">
                    {phase.status === 'Complete' ? <CheckCircle2 size={14} className="text-green-500" /> : <Circle size={14} />}
                    {task}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-center pt-6">
        <button className="bg-accent hover:bg-blue-600 text-white px-8 py-3 rounded-xl font-bold shadow-lg shadow-accent/20 transition-all flex items-center gap-2 group">
          <Zap size={20} />
          Execute Modernization Pipeline
          <span className="group-hover:translate-x-1 transition-transform">$\rightarrow$</span>
        </button>
      </div>
    </div>
  );
};

export default ModernizationPlan;
