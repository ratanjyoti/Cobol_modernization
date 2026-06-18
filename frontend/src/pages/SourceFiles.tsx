import React, { useState, useMemo, useRef, useEffect } from 'react';
import { 
  Upload, FileText, CheckCircle2, Clock, Search, ZoomIn, ZoomOut, Maximize, Share2, Database, 
  Cpu, GitBranch, Box, Info
} from 'lucide-react';
import { TransformWrapper, TransformComponent } from 'react-zoom-pan-pinch';

// --- Updated Mock Data: Nodes are now closer together ---
const MOCK_NODES = [
  { id: 'n1', label: 'MAIN-SVR.cbl', type: 'program', x: 300, y: 200, domain: 'AccountMgmt', priority: 'High', complexity: 12 },
  { id: 'n2', label: 'ACCT-PROC.cbl', type: 'program', x: 500, y: 150, domain: 'AccountMgmt', priority: 'Medium', complexity: 8 },
  { id: 'n3', label: 'CUST-DB', type: 'file', x: 400, y: 350, domain: 'CustomerCore', priority: 'High', complexity: 5 },
  { id: 'n4', label: 'LOG-SVR.cbl', type: 'program', x: 600, y: 250, domain: 'AuditTrail', priority: 'Low', complexity: 15 },
  { id: 'n5', label: 'COPYBOOK-A', type: 'file', x: 550, y: 380, domain: 'Shared', priority: 'Medium', complexity: 3 },
  { id: 'n6', label: 'PAYMENT.cbl', type: 'program', x: 700, y: 300, domain: 'PaymentProc', priority: 'High', complexity: 20 },
];

const MOCK_LINKS = [
  { from: 'n1', to: 'n2' }, { from: 'n1', to: 'n3' }, { from: 'n2', to: 'n3' },
  { from: 'n2', to: 'n4' }, { from: 'n4', to: 'n5' }, { from: 'n5', to: 'n6' },
];

const DDD_DOMAINS = [
  { id: 'AccountMgmt', name: 'Account Management', color: 'text-blue-400', border: 'border-blue-500/30', bg: 'bg-blue-500/10' },
  { id: 'CustomerCore', name: 'Customer Core', color: 'text-emerald-400', border: 'border-emerald-500/30', bg: 'bg-emerald-500/10' },
  { id: 'PaymentProc', name: 'Payment Processing', color: 'text-purple-400', border: 'border-purple-500/30', bg: 'bg-purple-500/10' },
  { id: 'AuditTrail', name: 'Audit Trail', color: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' },
  { id: 'Shared', name: 'Shared Commons', color: 'text-slate-400', border: 'border-slate-500/30', bg: 'bg-slate-500/10' },
];

const SourceFilesWorkbench = () => {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [leftWidth, setLeftWidth] = useState(40); // Percentage for resizable panels
  const [isResizing, setIsResizing] = useState(false);
  
  const transformComponentRef = useRef<any>(null);

  const [files] = useState([
    { id: '1', name: 'ACCOUNT-PROC.cbl', size: 1200, status: 'Analyzed', chunks: 1 },
    { id: '2', name: 'MAIN-SVR.cbl', size: 4500, status: 'Chunking', chunks: 15 },
    { id: '3', name: 'REPORT-GEN.cbl', size: 800, status: 'Pending', chunks: 1 },
  ]);

  const selectedNode = useMemo(() => MOCK_NODES.find(n => n.id === selectedId), [selectedId]);
  const getNodesByDomain = (domainId: string) => MOCK_NODES.filter(n => n.domain === domainId);

  // --- RESIZE LOGIC ---
  const startResizing = () => setIsResizing(true);
  const stopResizing = () => setIsResizing(false);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const newWidth = (e.clientX / window.innerWidth) * 100;
      if (newWidth > 20 && newWidth < 80) {
        setLeftWidth(newWidth);
      }
    };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', stopResizing);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', stopResizing);
    };
  }, [isResizing]);

  return (
    <div className="flex flex-col gap-6 h-full space-y-0">
      {/* TOP SECTION: Source Files Explorer */}
      <div className="glass-card p-6 rounded-2xl border-slate-800">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Source Files Explorer</h1>
            <p className="text-slate-400 text-sm">Ingestion status and chunking orchestrator</p>
          </div>
          <label className="cursor-pointer bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg font-bold transition-all flex items-center gap-2 text-sm">
            <Upload size={16} /> Upload COBOL Files
            <input type="file" multiple className="hidden" />
          </label>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-900/50 text-slate-400 text-[10px] uppercase tracking-wider">
              <tr>
                <th className="p-3 font-semibold">File Name</th>
                <th className="p-3 font-semibold">Size</th>
                <th className="p-3 font-semibold">Status</th>
                <th className="p-3 font-semibold">Chunks</th>
                <th className="p-3 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="text-slate-300 text-sm">
              {files.map(file => (
                <tr key={file.id} className="border-t border-slate-800 hover:bg-slate-800/30 transition-colors">
                  <td className="p-3 flex items-center gap-3"><FileText size={14} className="text-slate-500" /> {file.name}</td>
                  <td className="p-3">{file.size} LLOC</td>
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      {file.status === 'Analyzed' ? <CheckCircle2 size={14} className="text-emerald-400" /> : <Clock size={14} className="text-slate-400" />}
                      {file.status}
                    </div>
                  </td>
                  <td className="p-3">{file.chunks > 1 ? `${file.chunks} Chunks` : 'Single'}</td>
                  <td className="p-3"><button className="text-xs bg-slate-800 px-2 py-1 rounded hover:bg-slate-700 text-white">View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* MIDDLE SECTION: Resizable Discovery Workspace */}
      <div className="flex gap-0 h-[600px]">
        
        {/* Left Side: Relationship Map */}
        <div 
          className="glass-card rounded-l-2xl border border-r-0 border-slate-800 overflow-hidden flex flex-col" 
          style={{ width: `${leftWidth}%` }}
        >
          <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/30">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Share2 size={16} className="text-indigo-400" /> Relationship Map
            </h3>
            <div className="flex gap-2">
              <button onClick={() => transformComponentRef.current?.zoomIn()} className="p-1.5 bg-slate-800 rounded hover:bg-slate-700 text-slate-400"><ZoomIn size={14} /></button>
              <button onClick={() => transformComponentRef.current?.zoomOut()} className="p-1.5 bg-slate-800 rounded hover:bg-slate-700 text-slate-400"><ZoomOut size={14} /></button>
              <button onClick={() => transformComponentRef.current?.resetTransform()} className="p-1.5 bg-slate-800 rounded hover:bg-slate-700 text-slate-400"><Maximize size={14} /></button>
            </div>
          </div>
          
          <div className="p-3">
            <div className="relative mb-3">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
              <input 
                type="text" placeholder="Search node..." 
                className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white outline-none focus:ring-1 focus:ring-indigo-500"
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          <div className="flex-1 relative bg-slate-950/50">
            <TransformWrapper 
              ref={transformComponentRef} 
              centerOnInit 
              minScale={0.2} // FIXED: Allows zooming out
              maxScale={4}
            >
              <TransformComponent wrapperStyle={{ width: '100%', height: '100%' }}>
                <div className="relative" style={{ width: '1000px', height: '800px' }}>
                  <div className="absolute inset-0 opacity-10" style={{ backgroundImage: 'radial-gradient(#4f46e5 1px, transparent 1px)', backgroundSize: '30px 30px' }} />
                  
                  <svg className="absolute inset-0 w-full h-full">
                    {MOCK_LINKS.map((link, i) => {
                      const from = MOCK_NODES.find(n => n.id === link.from);
                      const to = MOCK_NODES.find(n => n.id === link.to);
                      if (!from || !to) return null;
                      // FIXED: Lines now point to the center of the node (x+70, y+18)
                      return <line key={i} x1={from.x+70} y1={from.y+18} x2={to.x+70} y2={to.y+18} stroke="#475569" strokeWidth="2" />;
                    })}
                  </svg>

                  {MOCK_NODES.map(node => {
                    const isSelected = selectedId === node.id;
                    const isHighlighted = selectedNode && node.domain === selectedNode.domain;
                    return (
                      <div 
                        key={node.id}
                        onClick={() => setSelectedId(node.id)}
                        className={`absolute p-2 rounded-lg border cursor-pointer transition-all duration-300 flex items-center gap-2 shadow-lg
                          ${isSelected ? 'bg-indigo-600 border-indigo-400 scale-110 z-10' : 
                            isHighlighted ? 'bg-indigo-500/20 border-indigo-500/50 scale-105' : 'bg-slate-900 border-slate-700 text-slate-400'}`}
                        style={{ left: node.x, top: node.y, width: '140px' }}
                      >
                        {node.type === 'program' ? <Cpu size={14} /> : <Database size={14} />}
                        <span className={`text-[10px] font-bold truncate ${isSelected ? 'text-white' : ''}`}>{node.label}</span>
                      </div>
                    );
                  })}
                </div>
              </TransformComponent>
            </TransformWrapper>
          </div>
        </div>

        {/* DRAGGABLE DIVIDER */}
        <div 
          onMouseDown={startResizing}
          className={`w-1 cursor-col-resize transition-colors ${isResizing ? 'bg-indigo-500' : 'bg-slate-800 hover:bg-indigo-400'}`}
        />

        {/* Right Side: DDD Discovery Panel */}
        <div 
          className="glass-card rounded-r-2xl border border-l-0 border-slate-800 overflow-hidden flex flex-col" 
          style={{ width: `${100 - leftWidth}%` }}
        >
          <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/30">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <GitBranch size={16} className="text-emerald-400" /> Domain Driven Discovery
            </h3>
            <span className="text-[10px] text-slate-500 uppercase">Bounded Contexts: 5</span>
          </div>

          <div className="flex-1 overflow-y-auto p-6 grid grid-cols-2 gap-6">
            {DDD_DOMAINS.map(domain => {
              const isSelected = selectedNode?.domain === domain.id;
              const domainNodes = getNodesByDomain(domain.id);
              return (
                <div 
                  key={domain.id}
                  onClick={() => {
                    const firstNode = domainNodes[0];
                    if (firstNode) setSelectedId(firstNode.id);
                  }}
                  className={`p-5 rounded-2xl border transition-all cursor-pointer group ${
                    isSelected ? `${domain.border} ${domain.bg} ring-2 ring-indigo-500/50` : 'border-slate-800 bg-slate-900/40 hover:border-slate-600'
                  }`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex items-center gap-2">
                      <Box size={16} className={domain.color} />
                      <h4 className={`font-bold text-sm ${isSelected ? 'text-white' : 'text-slate-300'}`}>{domain.name}</h4>
                    </div>
                    <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-500">{domainNodes.length} Artifacts</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {domainNodes.map(node => (
                      <span key={node.id} className={`text-[10px] px-2 py-1 rounded border ${selectedId === node.id ? 'bg-indigo-600 border-indigo-400 text-white' : 'bg-slate-800 border-slate-700 text-slate-400'}`}>
                        {node.label}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* BOTTOM SECTION: Selected Component Inspector */}
      <div className="glass-card p-6 rounded-2xl border-slate-800 bg-slate-900/50">
        <div className="flex items-center gap-3 mb-6 border-b border-slate-800 pb-4">
          <Info size={20} className="text-indigo-400" />
          <h3 className="text-lg font-bold text-white">Component Inspector</h3>
          {selectedNode && (
            <span className="ml-4 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 text-xs font-bold border border-indigo-500/20">
              {selectedNode.label}
            </span>
          )}
        </div>

        {!selectedNode ? (
          <div className="py-10 text-center opacity-40">
            <p className="text-slate-500 text-sm">Select a node in the graph or a domain context to inspect details</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="space-y-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Technical Metadata</p>
              <div className="space-y-2">
                <div className="flex justify-between text-sm"><span className="text-slate-400">Source File:</span> <span className="text-white font-mono">{selectedNode.label}</span></div>
                <div className="flex justify-between text-sm"><span className="text-slate-400">Type:</span> <span className="text-white capitalize">{selectedNode.type}</span></div>
                <div className="flex justify-between text-sm"><span className="text-slate-400">Complexity:</span> <span className="text-white">{selectedNode.complexity} (Scale 1-30)</span></div>
              </div>
            </div>
            <div className="space-y-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Architectural Context</p>
              <div className="space-y-2">
                <div className="flex justify-between text-sm"><span className="text-slate-400">Bounded Context:</span> <span className="text-indigo-400 font-bold">{selectedNode.domain}</span></div>
                <div className="flex justify-between text-sm"><span className="text-slate-400">Migration Priority:</span> <span className={`font-bold ${selectedNode.priority === 'High' ? 'text-red-400' : 'text-emerald-400'}`}>{selectedNode.priority}</span></div>
              </div>
            </div>
            <div className="space-y-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Relationships</p>
              <div className="flex flex-wrap gap-2">
                {MOCK_LINKS.filter(l => l.from === selectedNode.id || l.to === selectedNode.id).map((l, i) => (
                  <span key={i} className="text-[10px] bg-slate-800 px-2 py-1 rounded border border-slate-700 text-slate-300">
                    {l.from === selectedNode.id ? `Calls → ${l.to}` : `Called by ← ${l.from}`}
                  </span>
                ))}
              </div>
            </div>
            <div className="space-y-4">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">AI Insight</p>
              <div className="p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg text-xs text-indigo-300 italic">
                "High coupling detected with {MOCK_LINKS.find(l => l.from === selectedNode.id)?.to || 'system core'}. Recommend splitting into two services."
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SourceFilesWorkbench;
