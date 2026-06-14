import { Share2, Database, Cpu } from 'lucide-react';

const DependencyGraph = () => {
  // Mocking Nodes for the Graph
  const nodes = [
    { id: 'n1', label: 'MAIN-SVR.cbl', type: 'program', x: 100, y: 100 },
    { id: 'n2', label: 'ACCT-PROC.cbl', type: 'program', x: 400, y: 100 },
    { id: 'n3', label: 'CUST-DB', type: 'file', x: 250, y: 250 },
    { id: 'n4', label: 'LOG-SVR.cbl', type: 'program', x: 600, y: 200 },
  ];

  const links = [
    { from: 'n1', to: 'n2' },
    { from: 'n1', to: 'n3' },
    { from: 'n2', to: 'n3' },
    { from: 'n2', to: 'n4' },
  ];

  return (
    <div className="space-y-6 h-full">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Dependency Graph</h1>
          <p className="text-slate-400">Visual mapping of program relationships and file access.</p>
        </div>
        <div className="flex gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-400 bg-panel px-3 py-1 rounded-full border border-slate-700">
            <div className="w-2 h-2 rounded-full bg-blue-500"></div> Program
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400 bg-panel px-3 py-1 rounded-full border border-slate-700">
            <div className="w-2 h-2 rounded-full bg-amber-500"></div> File/DB
          </div>
        </div>
      </div>

      {/* The "Graph Canvas" */}
      <div className="relative w-full h-[600px] bg-panel border border-slate-700 rounded-2xl overflow-hidden shadow-inner">
        <div className="absolute inset-0 opacity-20" 
             style={{ backgroundImage: 'radial-gradient(#334155 1px, transparent 1px)', backgroundSize: '30px 30px' }}></div>
        
        {/* Render SVG Links */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          {links.map((link, i) => {
            const fromNode = nodes.find(n => n.id === link.from);
            const toNode = nodes.find(n => n.id === link.to);
            if (!fromNode || !toNode) return null;
            return (
              <line 
                key={i} 
                x1={fromNode.x + 50} y1={fromNode.y + 25} 
                x2={toNode.x + 50} y2={toNode.y + 25} 
                stroke="#475569" strokeWidth="2" 
              />
            );
          })}
        </svg>

        {/* Render Nodes */}
        {nodes.map((node) => (
          <div 
            key={node.id}
            className={`absolute p-3 rounded-lg border flex items-center gap-3 cursor-pointer transition-transform hover:scale-105 ${
              node.type === 'program' ? 'bg-blue-500/10 border-blue-500/50 text-blue-400' : 'bg-amber-500/10 border-amber-500/50 text-amber-400'
            }`}
            style={{ left: node.x, top: node.y, width: '160px' }}
          >
            {node.type === 'program' ? <Cpu size={16} /> : <Database size={16} />}
            <span className="text-xs font-bold truncate">{node.label}</span>
          </div>
        ))}
        
        <div className="absolute bottom-6 right-6 flex gap-2">
          <button className="bg-slate-800 text-white p-2 rounded-lg hover:bg-slate-700 border border-slate-600"><Share2 size={20} /></button>
          <button className="bg-slate-800 text-white p-2 rounded-lg hover:bg-slate-700 border border-slate-600">Zoom In</button>
        </div>
      </div>
    </div>
  );
};

export default DependencyGraph;
