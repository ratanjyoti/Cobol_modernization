import {
  Database,
  Cpu,
  ZoomIn,
  ZoomOut,
  Maximize,
  Share2
} from 'lucide-react';

import {
  TransformWrapper,
  TransformComponent
} from 'react-zoom-pan-pinch';

const DependencyGraph = () => {
  const nodes = [
    { id: 'n1', label: 'MAIN-SVR.cbl', type: 'program', x: 100, y: 100 },
    { id: 'n2', label: 'ACCT-PROC.cbl', type: 'program', x: 500, y: 100 },
    { id: 'n3', label: 'CUST-DB', type: 'file', x: 300, y: 300 },
    { id: 'n4', label: 'LOG-SVR.cbl', type: 'program', x: 800, y: 200 },
    { id: 'n5', label: 'COPYBOOK-A', type: 'file', x: 650, y: 400 },
    { id: 'n6', label: 'PAYMENT.cbl', type: 'program', x: 1050, y: 300 },
  ];

  const links = [
    { from: 'n1', to: 'n2' },
    { from: 'n1', to: 'n3' },
    { from: 'n2', to: 'n3' },
    { from: 'n2', to: 'n4' },
    { from: 'n4', to: 'n5' },
    { from: 'n5', to: 'n6' },
  ];

  return (
    <TransformWrapper
      initialScale={1}
      minScale={0.2}
      maxScale={4}
      wheel={{ smoothStep: 0.002 }}
      centerOnInit
    >
      {({ zoomIn, zoomOut, resetTransform }) => (
        <div className="relative w-full h-full bg-[var(--panel-bg)] border border-[var(--panel-border)] rounded-2xl overflow-hidden">
          
          {/* Zoom & Action Controls */}
          <div className="absolute top-4 right-4 z-50 flex gap-2">
            <button
              onClick={() => zoomIn()}
              className="bg-slate-800 text-white p-2 rounded-lg hover:bg-slate-700 transition-colors"
            >
              <ZoomIn size={18} />
            </button>

            <button
              onClick={() => zoomOut()}
              className="bg-slate-800 text-white p-2 rounded-lg hover:bg-slate-700 transition-colors"
            >
              <ZoomOut size={18} />
            </button>

            <button
              onClick={() => resetTransform()}
              className="bg-slate-800 text-white p-2 rounded-lg hover:bg-slate-700 transition-colors"
            >
              <Maximize size={18} />
            </button>

            <button
              className="bg-slate-800 text-white p-2 rounded-lg hover:bg-slate-700 transition-colors"
            >
              <Share2 size={18} />
            </button>
          </div>

          <TransformComponent
            wrapperStyle={{
              width: '100%',
              height: '100%',
            }}
          >
            <div
              className="relative"
              style={{
                width: '1800px',
                height: '1200px',
              }}
            >
              {/* Background Grid */}
              <div
                className="absolute inset-0 opacity-20"
                style={{
                  backgroundImage: 'radial-gradient(#334155 1px, transparent 1px)',
                  backgroundSize: '40px 40px',
                }}
              />

              {/* SVG Connection Lines */}
              <svg className="absolute inset-0 w-full h-full">
                {links.map((link, index) => {
                  const fromNode = nodes.find((n) => n.id === link.from);
                  const toNode = nodes.find((n) => n.id === link.to);

                  if (!fromNode || !toNode) return null;

                  return (
                    <line
                      key={index}
                      x1={fromNode.x + 80}
                      y1={fromNode.y + 25}
                      x2={toNode.x + 80}
                      y2={toNode.y + 25}
                      stroke="#64748b"
                      strokeWidth="2"
                    />
                  );
                })}
              </svg>

              {/* Map Nodes */}
              {nodes.map((node) => (
                <div
                  key={node.id}
                  className={`absolute p-3 rounded-xl border flex items-center gap-3 cursor-pointer hover:scale-105 transition-all shadow-lg ${
                    node.type === 'program'
                      ? 'bg-blue-500/10 border-blue-500/50 text-blue-400'
                      : 'bg-amber-500/10 border-amber-500/50 text-amber-400'
                  }`}
                  style={{
                    left: node.x,
                    top: node.y,
                    width: '180px',
                  }}
                >
                  {node.type === 'program' ? (
                    <Cpu size={18} />
                  ) : (
                    <Database size={18} />
                  )}

                  <span className="text-xs font-bold truncate">
                    {node.label}
                  </span>
                </div>
              ))}
            </div>
          </TransformComponent>
        </div>
      )}
    </TransformWrapper>
  );
};

export default DependencyGraph;
