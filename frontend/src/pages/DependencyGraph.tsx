import { useMemo, useState } from 'react';
import {
  Crosshair,
  Database,
  Cpu,
  FileCode,
  FileQuestion,
  Maximize2,
  Minimize2,
  Network,
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
  type: 'program' | 'copybook' | 'table' | 'job' | 'file' | 'external';
  x: number;
  y: number;
  file?: FileRecord;
  subtitle?: string;
  incoming: number;
  outgoing: number;
  isResolved: boolean;
};

export type DependencyLink = {
  id: string;
  from: string;
  to: string;
  relationType: string;
};

type RelationFilter = 'ALL' | 'CALLS' | 'INCLUDES' | 'READS_WRITES';

type DependencyGraphProps = {
  nodes: DependencyNode[];
  links: DependencyLink[];
  selectedNodeId?: string;
  onNodeSelect?: (node: DependencyNode) => void;
};

const NODE_WIDTH = 240;
const NODE_HEIGHT = 64;
const OVERVIEW_LIMIT = 80;
const RELATION_FILTERS: RelationFilter[] = ['ALL', 'CALLS', 'INCLUDES', 'READS_WRITES'];

const getNodeChrome = (type: DependencyNode['type']) => {
  switch (type) {
    case 'program':
      return { icon: <Cpu size={24} />, className: 'bg-blue-500/10 border-blue-500/50 text-blue-300' };
    case 'copybook':
      return { icon: <FileCode size={24} />, className: 'bg-emerald-500/10 border-emerald-500/50 text-emerald-300' };
    case 'table':
      return { icon: <Database size={24} />, className: 'bg-rose-500/10 border-rose-500/50 text-rose-300' };
    case 'job':
      return { icon: <Network size={24} />, className: 'bg-violet-500/10 border-violet-500/50 text-violet-300' };
    case 'external':
      return { icon: <FileQuestion size={24} />, className: 'bg-amber-500/10 border-amber-500/50 text-amber-300' };
    default:
      return { icon: <FileQuestion size={24} />, className: 'bg-slate-500/10 border-slate-500/50 text-slate-300' };
  }
};

const getLinkColor = (relationType: string) => {
  switch (relationType) {
    case 'CALLS':
      return '#f59e0b';
    case 'INCLUDES':
      return '#10b981';
    case 'READS_WRITES':
      return '#38bdf8';
    default:
      return '#94a3b8';
  }
};

const DependencyGraph = ({ nodes, links, selectedNodeId, onNodeSelect }: DependencyGraphProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeRelation, setActiveRelation] = useState<RelationFilter>('ALL');

  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);

  const filteredLinks = useMemo(() => {
    if (activeRelation === 'ALL') return links;
    return links.filter((link) => link.relationType === activeRelation);
  }, [activeRelation, links]);

  const visibleLinks = useMemo(() => {
    if (!selectedNodeId) {
      return filteredLinks.slice(0, OVERVIEW_LIMIT);
    }

    return filteredLinks.filter((link) => link.from === selectedNodeId || link.to === selectedNodeId);
  }, [filteredLinks, selectedNodeId]);

  const visibleNodeIds = useMemo(() => {
    if (!selectedNodeId) {
      const ids = new Set<string>();
      nodes
        .slice()
        .sort((a, b) => (b.incoming + b.outgoing) - (a.incoming + a.outgoing))
        .slice(0, OVERVIEW_LIMIT)
        .forEach((node) => ids.add(node.id));
      visibleLinks.forEach((link) => {
        ids.add(link.from);
        ids.add(link.to);
      });
      return ids;
    }

    const ids = new Set<string>([selectedNodeId]);
    visibleLinks.forEach((link) => {
      ids.add(link.from);
      ids.add(link.to);
    });
    return ids;
  }, [nodes, selectedNodeId, visibleLinks]);

  const visibleNodes = useMemo(() => {
    return nodes.filter((node) => visibleNodeIds.has(node.id));
  }, [nodes, visibleNodeIds]);

  const canvasSize = useMemo(() => {
    const maxX = Math.max(900, ...visibleNodes.map((node) => node.x + NODE_WIDTH + 160));
    const maxY = Math.max(600, ...visibleNodes.map((node) => node.y + NODE_HEIGHT + 160));
    return { width: maxX, height: maxY };
  }, [visibleNodes]);

  const hiddenCount = Math.max(0, links.length - visibleLinks.length);

  return (
    <div className={isFullscreen ? 'fixed inset-4 z-[100] rounded-2xl bg-slate-950 shadow-2xl shadow-black/60' : 'h-full w-full'}>
      <TransformWrapper
        key={`${visibleNodes.length}-${visibleLinks.length}-${selectedNodeId || 'overview'}-${activeRelation}`}
        initialScale={1}
        minScale={0.1}
        maxScale={4}
        wheel={{ smoothStep: 0.002 }}
        centerOnInit
      >
        {({ zoomIn, zoomOut, centerView }) => (
          <div className="relative w-full h-full bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden min-h-[600px]">
            <div className="absolute left-4 top-4 z-50 flex flex-wrap gap-2 pr-52">
              {RELATION_FILTERS.map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setActiveRelation(type)}
                  className={`rounded-lg border px-3 py-2 text-xs font-bold transition-colors ${
                    activeRelation === type
                      ? 'border-emerald-400 bg-emerald-500/20 text-emerald-300'
                      : 'border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {type}
                </button>
              ))}
              <div className="rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-xs font-semibold text-slate-400">
                {selectedNodeId ? 'Selected node impact' : 'Overview'} - {visibleLinks.length} shown{hiddenCount > 0 ? `, ${hiddenCount} hidden` : ''}
              </div>
            </div>

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
            ) : visibleNodes.length === 0 ? (
              <div className="flex h-full min-h-[600px] items-center justify-center text-center text-slate-500">
                <div>
                  <p className="text-sm font-bold text-slate-300">No relations match this filter</p>
                  <p className="mt-1 text-xs">Choose another relation type or select a different graph node.</p>
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
                    {visibleLinks.map((link) => {
                      const fromNode = nodeById.get(link.from);
                      const toNode = nodeById.get(link.to);

                      if (!fromNode || !toNode) return null;

                      const color = getLinkColor(link.relationType);
                      const x1 = fromNode.x + NODE_WIDTH;
                      const y1 = fromNode.y + NODE_HEIGHT / 2;
                      const x2 = toNode.x;
                      const y2 = toNode.y + NODE_HEIGHT / 2;
                      const midX = (x1 + x2) / 2;
                      const path = `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`;

                      return (
                        <g key={link.id}>
                          <path
                            d={path}
                            fill="none"
                            stroke={color}
                            strokeWidth="2"
                            strokeOpacity={selectedNodeId ? 0.9 : 0.35}
                            strokeDasharray={toNode.isResolved ? undefined : '7 7'}
                          />
                          {selectedNodeId && (
                            <text
                              x={(x1 + x2) / 2}
                              y={(y1 + y2) / 2 - 8}
                              fill={color}
                              fontSize="12"
                              fontWeight="700"
                            >
                              {link.relationType}
                            </text>
                          )}
                        </g>
                      );
                    })}
                  </svg>

                  {visibleNodes.map((node) => {
                    const isSelected = node.id === selectedNodeId;
                    const chrome = getNodeChrome(node.type);

                    return (
                      <button
                        type="button"
                        key={node.id}
                        onClick={() => onNodeSelect?.(node)}
                        className={`absolute min-h-[64px] rounded-xl border px-4 py-3 flex items-center gap-3 cursor-pointer hover:scale-105 transition-all shadow-lg text-left ${chrome.className} ${isSelected ? 'ring-2 ring-emerald-400 ring-offset-2 ring-offset-slate-950 scale-105' : ''}`}
                        style={{ left: node.x, top: node.y, width: `${NODE_WIDTH}px` }}
                        aria-pressed={isSelected}
                      >
                        {chrome.icon}
                        <span className="min-w-0">
                          <span className="block truncate text-base font-bold leading-5">{node.label}</span>
                          <span className="mt-1 block truncate text-xs font-semibold uppercase tracking-wide text-slate-400">
                            {node.subtitle || `${node.incoming} in - ${node.outgoing} out`}
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
