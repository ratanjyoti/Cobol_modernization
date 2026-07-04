import { useMemo, useState } from 'react';
import {
  Crosshair,
  Database,
  Cpu,
  Maximize2,
  Minimize2,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';

import {
  TransformWrapper,
  TransformComponent
} from 'react-zoom-pan-pinch';

import type { FileRecord } from '../services/api';

export type DependencyNode = {
  id: string;
  label: string;
  type: 'program' | 'file';
  x: number;
  y: number;
  file: FileRecord;
};

export type DependencyLink = {
  id: string;
  from: string;
  to: string;
  relationType: string;
};

type DependencyGraphProps = {
  nodes: DependencyNode[];
  links: DependencyLink[];
  selectedNodeId?: string;
  onNodeSelect?: (node: DependencyNode) => void;
};

const NODE_WIDTH = 240;
const NODE_HEIGHT = 64;

const DependencyGraph = ({ nodes, links, selectedNodeId, onNodeSelect }: DependencyGraphProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const canvasSize = useMemo(() => {
    const maxX = Math.max(900, ...nodes.map((node) => node.x + NODE_WIDTH + 160));
    const maxY = Math.max(600, ...nodes.map((node) => node.y + NODE_HEIGHT + 160));
    return { width: maxX, height: maxY };
  }, [nodes]);

  return (
    <div className={isFullscreen ? 'fixed inset-4 z-[100] rounded-2xl bg-slate-950 shadow-2xl shadow-black/60' : 'h-full w-full'}>
      <TransformWrapper
        key={`${nodes.length}-${links.length}`}
        initialScale={1}
        minScale={0.1}
        maxScale={4}
        wheel={{ smoothStep: 0.002 }}
        centerOnInit
      >
        {({ zoomIn, zoomOut, centerView }) => (
          <div className="relative w-full h-full bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden min-h-[600px]">
            <div className="absolute top-4 right-4 z-50 flex gap-2">
              <button
                type="button"
                aria-label="Zoom in"
                title="Zoom in"
                onClick={() => zoomIn()}
                className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700"
              >
                <ZoomIn size={20} />
              </button>

              <button
                type="button"
                aria-label={isFullscreen ? 'Exit fullscreen' : 'Open fullscreen graph'}
                title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen graph'}
                onClick={() => setIsFullscreen((value) => !value)}
                className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700"
              >
                {isFullscreen ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
              </button>

              <button
                type="button"
                aria-label="Center graph"
                title="Center graph"
                onClick={() => centerView(1, 250)}
                className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700"
              >
                <Crosshair size={20} />
              </button>

              <button
                type="button"
                aria-label="Zoom out"
                title="Zoom out"
                onClick={() => zoomOut()}
                className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700"
              >
                <ZoomOut size={20} />
              </button>
            </div>

            {nodes.length === 0 ? (
              <div className="flex h-full min-h-[600px] items-center justify-center text-center text-slate-500">
                <div>
                  <p className="text-sm font-bold text-slate-300">No uploaded files found</p>
                  <p className="mt-1 text-xs">Upload source files for the active run to populate this graph.</p>
                </div>
              </div>
            ) : (
              <TransformComponent
                wrapperStyle={{ width: '100%', height: '100%' }}
              >
                <div
                  className="relative"
                  style={{ width: `${canvasSize.width}px`, height: `${canvasSize.height}px` }}
                >
                  <div
                    className="absolute inset-0 opacity-20"
                    style={{
                      backgroundImage: 'radial-gradient(#334155 1px, transparent 1px)',
                      backgroundSize: '40px 40px',
                    }}
                  />

                  <svg className="absolute inset-0 w-full h-full">
                    {links.map((link) => {
                      const fromNode = nodes.find((node) => node.id === link.from);
                      const toNode = nodes.find((node) => node.id === link.to);

                      if (!fromNode || !toNode) return null;

                      return (
                        <g key={link.id}>
                          <line
                            x1={fromNode.x + NODE_WIDTH / 2}
                            y1={fromNode.y + NODE_HEIGHT / 2}
                            x2={toNode.x + NODE_WIDTH / 2}
                            y2={toNode.y + NODE_HEIGHT / 2}
                            stroke="#64748b"
                            strokeWidth="3"
                            strokeDasharray="6"
                          />
                          <text
                            x={(fromNode.x + toNode.x + NODE_WIDTH) / 2}
                            y={(fromNode.y + toNode.y + NODE_HEIGHT) / 2 - 8}
                            fill="#94a3b8"
                            fontSize="18"
                            fontWeight="700"
                          >
                            {link.relationType}
                          </text>
                        </g>
                      );
                    })}
                  </svg>

                  {nodes.map((node) => {
                    const isSelected = node.id === selectedNodeId;

                    return (
                      <button
                        type="button"
                        key={node.id}
                        onClick={() => onNodeSelect?.(node)}
                        className={`absolute min-h-[64px] rounded-xl border px-4 py-3 flex items-center gap-3 cursor-pointer hover:scale-105 transition-all shadow-lg text-left ${
                          node.type === 'program'
                            ? 'bg-blue-500/10 border-blue-500/50 text-blue-300'
                            : 'bg-amber-500/10 border-amber-500/50 text-amber-300'
                        } ${isSelected ? 'ring-2 ring-emerald-400 ring-offset-2 ring-offset-slate-950 scale-105' : ''}`}
                        style={{ left: node.x, top: node.y, width: `${NODE_WIDTH}px` }}
                        aria-pressed={isSelected}
                      >
                        {node.type === 'program' ? <Cpu size={24} /> : <Database size={24} />}
                        <span className="min-w-0">
                          <span className="block truncate text-base font-bold leading-5">{node.label}</span>
                          <span className="mt-1 block truncate text-xs font-semibold uppercase tracking-wide text-slate-400">
                            {node.file.detected_lang || 'unknown'} - {node.file.status || 'pending'}
                          </span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </TransformComponent>
            )}
          </div>
        )}
      </TransformWrapper>
    </div>
  );
};

export default DependencyGraph;
