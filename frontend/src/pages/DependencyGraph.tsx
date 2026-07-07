import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  Box,
  Crosshair,
  Database,
  Cpu,
  FileCode,
  FileQuestion,
  FolderOpen,
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

export type GraphMode = 'overview' | 'connected' | 'impact' | 'unresolved' | 'isolated';

export type DependencyNode = {
  id: string;
  label: string;
  type: 'program' | 'copybook' | 'table' | 'job' | 'file' | 'external' | 'group';
  x: number;
  y: number;
  file?: FileRecord;
  subtitle?: string;
  incoming: number;
  outgoing: number;
  isResolved: boolean;
  groupCount?: number;
};

export type DependencyLink = {
  id: string;
  from: string;
  to: string;
  relationType: string;
};

export type DependencyGraphStats = {
  totalFiles: number;
  connectedFiles: number;
  isolatedFiles: number;
  unresolvedTargets: number;
  relations: number;
  programs: number;
  copybooks: number;
  tables: number;
  jobs: number;
};

type DependencyGraphProps = {
  nodes: DependencyNode[];
  links: DependencyLink[];
  mode: GraphMode;
  stats: DependencyGraphStats;
  selectedNodeId?: string;
  onModeChange?: (mode: GraphMode) => void;
  onNodeSelect?: (node: DependencyNode) => void;
  onOverviewSelect?: () => void;
};

type RelationFilter = 'ALL' | string;

const NODE_SIZE = 88;
const GROUP_WIDTH = 220;
const GROUP_HEIGHT = 118;
const LAYER_X: Record<string, number> = {
  job: 120,
  program: 450,
  copybook: 780,
  file: 780,
  table: 1110,
  external: 1110,
  group: 120,
};

const MODE_LABELS: Record<GraphMode, string> = {
  overview: 'Overview',
  connected: 'Connected Map',
  impact: 'Impact View',
  unresolved: 'Unresolved',
  isolated: 'Isolated Files',
};

const REQUESTED_RELATION_ORDER = ['CALLS', 'INCLUDES', 'READS_WRITES', 'IMPORTS', 'REFERENCES', 'INHERITS'];

const cloneNode = (node: DependencyNode): DependencyNode => ({ ...node });

const getNodeChrome = (type: DependencyNode['type']) => {
  switch (type) {
    case 'program':
      return { icon: <Cpu size={22} />, className: 'bg-blue-500/15 border-blue-400/60 text-blue-200 shadow-blue-950/40' };
    case 'copybook':
      return { icon: <FileCode size={22} />, className: 'bg-emerald-500/15 border-emerald-400/60 text-emerald-200 shadow-emerald-950/40' };
    case 'table':
      return { icon: <Database size={22} />, className: 'bg-rose-500/15 border-rose-400/60 text-rose-200 shadow-rose-950/40' };
    case 'job':
      return { icon: <Network size={22} />, className: 'bg-violet-500/15 border-violet-400/60 text-violet-200 shadow-violet-950/40' };
    case 'external':
      return { icon: <FileQuestion size={22} />, className: 'bg-orange-500/15 border-orange-400/70 text-orange-200 shadow-orange-950/40' };
    case 'group':
      return { icon: <FolderOpen size={24} />, className: 'bg-slate-800/95 border-slate-600 text-slate-100 shadow-black/30' };
    default:
      return { icon: <Box size={22} />, className: 'bg-slate-500/15 border-slate-400/50 text-slate-200 shadow-slate-950/40' };
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
    case 'IMPORTS':
      return '#818cf8';
    case 'REFERENCES':
      return '#60a5fa';
    case 'INHERITS':
      return '#a78bfa';
    default:
      return '#94a3b8';
  }
};

const getLayer = (node: DependencyNode) => {
  if (!node.isResolved || node.type === 'external') return 'external';
  if (node.type === 'job') return 'job';
  if (node.type === 'program') return 'program';
  if (node.type === 'copybook' || node.type === 'file') return node.type;
  if (node.type === 'table') return 'table';
  return 'file';
};

const layoutLayered = (nodes: DependencyNode[]) => {
  const layerOrder = ['job', 'program', 'copybook', 'file', 'table', 'external'];
  const grouped = new Map<string, DependencyNode[]>();

  nodes.forEach((node) => {
    const layer = getLayer(node);
    grouped.set(layer, [...(grouped.get(layer) || []), node]);
  });

  layerOrder.forEach((layer) => {
    const layerNodes = (grouped.get(layer) || []).sort((a, b) => {
      const relationDelta = (b.incoming + b.outgoing) - (a.incoming + a.outgoing);
      return relationDelta || a.label.localeCompare(b.label);
    });
    const x = LAYER_X[layer] || LAYER_X.file;
    const startY = Math.max(120, 360 - (layerNodes.length * 58));

    layerNodes.forEach((node, index) => {
      node.x = x;
      node.y = startY + index * 132;
    });
  });

  return nodes;
};

const layoutImpact = (nodes: DependencyNode[], links: DependencyLink[], focusIds: Set<string>) => {
  const incomingIds = new Set<string>();
  const outgoingIds = new Set<string>();

  links.forEach((link) => {
    if (focusIds.has(link.to) && !focusIds.has(link.from)) incomingIds.add(link.from);
    if (focusIds.has(link.from) && !focusIds.has(link.to)) outgoingIds.add(link.to);
  });

  const focusNodes = nodes.filter((node) => focusIds.has(node.id));
  const incomingNodes = nodes.filter((node) => incomingIds.has(node.id));
  const outgoingNodes = nodes.filter((node) => outgoingIds.has(node.id));
  const centerY = Math.max(260, Math.max(incomingNodes.length, outgoingNodes.length, focusNodes.length) * 70);

  focusNodes.forEach((node, index) => {
    node.x = 560;
    node.y = centerY + (index - (focusNodes.length - 1) / 2) * 118;
  });

  incomingNodes.forEach((node, index) => {
    node.x = 160;
    node.y = centerY + (index - (incomingNodes.length - 1) / 2) * 128;
  });

  outgoingNodes.forEach((node, index) => {
    node.x = 960;
    node.y = centerY + (index - (outgoingNodes.length - 1) / 2) * 128;
  });

  return nodes;
};

const buildOverviewNodes = (stats: DependencyGraphStats): DependencyNode[] => {
  const groups: Array<Pick<DependencyNode, 'id' | 'label' | 'type' | 'groupCount' | 'subtitle'> & { x: number; y: number }> = [
    { id: 'group:uploaded', label: 'Uploaded Files', type: 'group', groupCount: stats.totalFiles, subtitle: 'All files preserved in explorer', x: 120, y: 160 },
    { id: 'group:programs', label: 'Programs', type: 'program', groupCount: stats.programs, subtitle: 'COBOL and program files', x: 420, y: 120 },
    { id: 'group:copybooks', label: 'Copybooks', type: 'copybook', groupCount: stats.copybooks, subtitle: 'Includes and shared records', x: 720, y: 120 },
    { id: 'group:tables', label: 'Tables / Data Stores', type: 'table', groupCount: stats.tables, subtitle: 'Data access targets', x: 1020, y: 120 },
    { id: 'group:jobs', label: 'Jobs', type: 'job', groupCount: stats.jobs, subtitle: 'JCL and orchestration', x: 420, y: 340 },
    { id: 'group:external', label: 'External / Unresolved', type: 'external', groupCount: stats.unresolvedTargets, subtitle: 'Referenced but not uploaded', x: 720, y: 340 },
    { id: 'group:isolated', label: 'Isolated Files', type: 'file', groupCount: stats.isolatedFiles, subtitle: 'Hidden from graph canvas', x: 1020, y: 340 },
  ];

  return groups.map((group) => ({
    ...group,
    incoming: 0,
    outgoing: 0,
    isResolved: true,
  }));
};

const statusForMode = (mode: GraphMode, stats: DependencyGraphStats, nodeCount: number, linkCount: number) => {
  if (mode === 'overview') {
    return `${stats.totalFiles} files uploaded - ${stats.relations} dependencies detected - ${stats.isolatedFiles} isolated files hidden from map`;
  }

  if (mode === 'isolated') {
    return `${stats.isolatedFiles} isolated files shown in the file explorer`;
  }

  return `${nodeCount} nodes - ${linkCount} dependencies`;
};

const DependencyGraph = ({
  nodes,
  links,
  mode,
  stats,
  selectedNodeId,
  onModeChange,
  onNodeSelect,
  onOverviewSelect
}: DependencyGraphProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [activeRelation, setActiveRelation] = useState<RelationFilter>('ALL');
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set());

  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);
  const availableRelations = useMemo(() => {
    const counts = new Map<string, number>();
    links.forEach((link) => counts.set(link.relationType, (counts.get(link.relationType) || 0) + 1));
    return REQUESTED_RELATION_ORDER
      .filter((type) => counts.has(type))
      .concat([...counts.keys()].filter((type) => !REQUESTED_RELATION_ORDER.includes(type)).sort())
      .map((type) => ({ type, count: counts.get(type) || 0 }));
  }, [links]);

  useEffect(() => {
    if (activeRelation !== 'ALL' && !availableRelations.some((relation) => relation.type === activeRelation)) {
      setActiveRelation('ALL');
    }
  }, [activeRelation, availableRelations]);

  useEffect(() => {
    if (mode !== 'impact') {
      setExpandedNodeIds(new Set());
      return;
    }

    setExpandedNodeIds((current) => {
      const validIds = new Set(nodes.map((node) => node.id));
      const next = new Set([...current].filter((id) => validIds.has(id)));

      if (selectedNodeId && validIds.has(selectedNodeId)) {
        next.add(selectedNodeId);
      }

      return next;
    });
  }, [mode, nodes, selectedNodeId]);

  const filteredLinks = useMemo(() => {
    if (activeRelation === 'ALL') return links;
    return links.filter((link) => link.relationType === activeRelation);
  }, [activeRelation, links]);

  const relationNodeIds = useMemo(() => {
    const ids = new Set<string>();
    filteredLinks.forEach((link) => {
      ids.add(link.from);
      ids.add(link.to);
    });
    return ids;
  }, [filteredLinks]);

  const focusedNodeIds = useMemo(() => {
    if (mode !== 'impact') return new Set<string>();
    const ids = new Set(expandedNodeIds);
    if (selectedNodeId) ids.add(selectedNodeId);
    return ids;
  }, [expandedNodeIds, mode, selectedNodeId]);

  const visibleLinks = useMemo(() => {
    if (mode === 'overview' || mode === 'isolated') return [];
    if (mode === 'impact') {
      return filteredLinks.filter((link) => focusedNodeIds.has(link.from) || focusedNodeIds.has(link.to));
    }
    if (mode === 'unresolved') {
      return filteredLinks.filter((link) => {
        const from = nodeById.get(link.from);
        const to = nodeById.get(link.to);
        return from?.isResolved === false || to?.isResolved === false;
      });
    }
    return filteredLinks;
  }, [filteredLinks, focusedNodeIds, mode, nodeById]);

  const displayNodes = useMemo(() => {
    if (mode === 'overview') return buildOverviewNodes(stats);
    if (mode === 'isolated') return [];

    let visibleIds = new Set<string>();

    if (mode === 'impact') {
      visibleIds = new Set(focusedNodeIds);
      visibleLinks.forEach((link) => {
        visibleIds.add(link.from);
        visibleIds.add(link.to);
      });
    } else if (mode === 'unresolved') {
      visibleLinks.forEach((link) => {
        visibleIds.add(link.from);
        visibleIds.add(link.to);
      });
    } else {
      visibleIds = relationNodeIds;
    }

    const visibleNodes = nodes.filter((node) => visibleIds.has(node.id)).map(cloneNode);
    if (mode === 'impact') return layoutImpact(visibleNodes, visibleLinks, focusedNodeIds);
    return layoutLayered(visibleNodes);
  }, [focusedNodeIds, mode, nodes, relationNodeIds, stats, visibleLinks]);

  const displayNodeById = useMemo(() => new Map(displayNodes.map((node) => [node.id, node])), [displayNodes]);
  const canvasSize = useMemo(() => {
    const itemWidth = mode === 'overview' ? GROUP_WIDTH : NODE_SIZE;
    const itemHeight = mode === 'overview' ? GROUP_HEIGHT : NODE_SIZE;
    const maxX = Math.max(1360, ...displayNodes.map((node) => node.x + itemWidth + 180));
    const maxY = Math.max(700, ...displayNodes.map((node) => node.y + itemHeight + 180));
    return { width: maxX, height: maxY };
  }, [displayNodes, mode]);

  const statusText = statusForMode(mode, stats, displayNodes.length, visibleLinks.length);

  const handleNodeClick = (node: DependencyNode) => {
    if (node.type === 'group') return;
    if (mode === 'overview') return;

    if (mode === 'impact') {
      setExpandedNodeIds((current) => new Set([...current, node.id]));
    }

    onNodeSelect?.(node);
  };

  const handleOverviewClick = () => {
    setExpandedNodeIds(new Set());
    onOverviewSelect?.();
    onModeChange?.('overview');
  };

  return (
    <div className={isFullscreen ? 'fixed inset-4 z-[100] rounded-2xl bg-slate-950 shadow-2xl shadow-black/60' : 'h-full w-full'}>
      <TransformWrapper
        key={`${mode}-${displayNodes.length}-${visibleLinks.length}-${[...focusedNodeIds].join(',') || 'none'}-${activeRelation}`}
        initialScale={1}
        minScale={0.1}
        maxScale={4}
        wheel={{ smoothStep: 0.002 }}
        centerOnInit
      >
        {({ zoomIn, zoomOut, centerView }) => (
          <div className="relative w-full h-full bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden min-h-[600px]">
            <div className="absolute left-4 top-4 z-50 flex flex-wrap gap-2 pr-56">
              {(Object.keys(MODE_LABELS) as GraphMode[]).map((graphMode) => (
                <button
                  key={graphMode}
                  type="button"
                  onClick={() => onModeChange?.(graphMode)}
                  className={`rounded-lg border px-3 py-2 text-xs font-bold transition-colors ${
                    mode === graphMode
                      ? 'border-indigo-400 bg-indigo-500/20 text-indigo-200'
                      : 'border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {MODE_LABELS[graphMode]}
                </button>
              ))}

              <div className="flex flex-wrap gap-2 basis-full">
                <button
                  type="button"
                  onClick={() => setActiveRelation('ALL')}
                  className={`rounded-lg border px-3 py-2 text-xs font-bold transition-colors ${
                    activeRelation === 'ALL'
                      ? 'border-emerald-400 bg-emerald-500/20 text-emerald-300'
                      : 'border-slate-700 bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  ALL <span className="text-slate-400">{links.length}</span>
                </button>
                {availableRelations.map(({ type, count }) => (
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
                    {type} <span className="text-slate-400">{count}</span>
                  </button>
                ))}
                {mode === 'impact' && (
                  <button
                    type="button"
                    onClick={handleOverviewClick}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs font-bold text-slate-200 transition-colors hover:bg-slate-700"
                  >
                    <ArrowLeft size={14} />
                    Back to Overview
                  </button>
                )}
                <div className="rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-xs font-semibold text-slate-400">
                  {statusText}
                </div>
              </div>
            </div>

            <div className="absolute top-4 right-4 z-50 flex gap-2">
              <button type="button" aria-label="Zoom in" title="Zoom in" onClick={() => zoomIn()} className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700">
                <ZoomIn size={20} />
              </button>
              <button type="button" aria-label={isFullscreen ? 'Exit fullscreen' : 'Open fullscreen graph'} title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen graph'} onClick={() => setIsFullscreen((value) => !value)} className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700">
                {isFullscreen ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
              </button>
              <button type="button" aria-label="Center graph" title="Center graph" onClick={() => centerView(1, 250)} className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700">
                <Crosshair size={20} />
              </button>
              <button type="button" aria-label="Zoom out" title="Zoom out" onClick={() => zoomOut()} className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700">
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
            ) : mode === 'isolated' ? (
              <div className="flex h-full min-h-[600px] items-center justify-center text-center text-slate-500">
                <div>
                  <p className="text-sm font-bold text-slate-300">Isolated files are shown in the explorer</p>
                  <p className="mt-1 text-xs">Use the left panel to search and inspect files with no detected dependencies.</p>
                </div>
              </div>
            ) : displayNodes.length === 0 ? (
              <div className="flex h-full min-h-[600px] items-center justify-center text-center text-slate-500">
                <div>
                  <p className="text-sm font-bold text-slate-300">No relations match this view</p>
                  <p className="mt-1 text-xs">Choose another mode, relation type, or select a file from the explorer.</p>
                </div>
              </div>
            ) : (
              <TransformComponent wrapperStyle={{ width: '100%', height: '100%' }}>
                <div className="relative" style={{ width: `${canvasSize.width}px`, height: `${canvasSize.height}px` }}>
                  <div
                    className="absolute inset-0 opacity-20"
                    style={{
                      backgroundImage: 'radial-gradient(#334155 1px, transparent 1px)',
                      backgroundSize: '40px 40px',
                    }}
                  />

                  <svg className="absolute inset-0 w-full h-full">
                    <defs>
                      {availableRelations.concat([{ type: 'DEFAULT', count: 0 }]).map(({ type }) => {
                        const markerId = `arrow-${type.replace(/[^a-zA-Z0-9_-]/g, '-')}`;
                        return (
                          <marker key={markerId} id={markerId} markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
                            <path d="M 0 0 L 9 3 L 0 6 z" fill={type === 'DEFAULT' ? '#94a3b8' : getLinkColor(type)} />
                          </marker>
                        );
                      })}
                    </defs>
                    {visibleLinks.map((link) => {
                      const fromNode = displayNodeById.get(link.from);
                      const toNode = displayNodeById.get(link.to);

                      if (!fromNode || !toNode) return null;

                      const color = getLinkColor(link.relationType);
                      const x1 = fromNode.x + NODE_SIZE / 2;
                      const y1 = fromNode.y + NODE_SIZE / 2;
                      const x2 = toNode.x + NODE_SIZE / 2;
                      const y2 = toNode.y + NODE_SIZE / 2;
                      const deltaX = Math.max(120, Math.abs(x2 - x1) / 2);
                      const controlOffset = x2 >= x1 ? deltaX : -deltaX;
                      const path = `M ${x1} ${y1} C ${x1 + controlOffset} ${y1}, ${x2 - controlOffset} ${y2}, ${x2} ${y2}`;
                      const markerId = `arrow-${link.relationType.replace(/[^a-zA-Z0-9_-]/g, '-')}`;

                      return (
                        <g key={link.id}>
                          <path
                            d={path}
                            fill="none"
                            stroke={color}
                            strokeWidth={mode === 'impact' ? 3 : 2}
                            strokeOpacity={mode === 'impact' ? 0.95 : 0.72}
                            strokeDasharray={toNode.isResolved ? undefined : '7 7'}
                            markerEnd={`url(#${markerId})`}
                          />
                          {mode === 'impact' && (
                            <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 10} fill={color} fontSize="12" fontWeight="700">
                              {link.relationType}
                            </text>
                          )}
                        </g>
                      );
                    })}
                  </svg>

                  {displayNodes.map((node) => {
                    const isSelected = node.id === selectedNodeId || focusedNodeIds.has(node.id);
                    const chrome = getNodeChrome(node.type);
                    const isGroupNode = mode === 'overview';

                    if (isGroupNode) {
                      return (
                        <button
                          type="button"
                          key={node.id}
                          onClick={() => {
                            if (node.id === 'group:isolated') onModeChange?.('isolated');
                            else if (node.id === 'group:external') onModeChange?.('unresolved');
                            else onModeChange?.('connected');
                          }}
                          className={`absolute rounded-xl border p-4 text-left shadow-lg transition-all hover:-translate-y-1 ${chrome.className}`}
                          style={{ left: node.x, top: node.y, width: `${GROUP_WIDTH}px`, height: `${GROUP_HEIGHT}px` }}
                        >
                          <span className="flex items-center justify-between gap-3">
                            <span className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-slate-950/50">{chrome.icon}</span>
                            <span className="font-mono text-3xl font-black text-white">{node.groupCount ?? 0}</span>
                          </span>
                          <span className="mt-3 block truncate text-sm font-bold">{node.label}</span>
                          <span className="mt-1 block truncate text-xs text-slate-400">{node.subtitle}</span>
                        </button>
                      );
                    }

                    return (
                      <button
                        type="button"
                        key={node.id}
                        onClick={() => handleNodeClick(node)}
                        className={`absolute flex h-[88px] w-[88px] flex-col items-center justify-center rounded-full border p-2 text-center shadow-lg transition-all hover:scale-110 ${chrome.className} ${isSelected ? 'ring-2 ring-emerald-300 ring-offset-4 ring-offset-slate-950 scale-110 brightness-125' : ''}`}
                        style={{ left: node.x, top: node.y }}
                        aria-pressed={isSelected}
                        title={`${node.label} - ${node.incoming} incoming, ${node.outgoing} outgoing`}
                      >
                        {chrome.icon}
                        <span className="mt-1 w-full truncate text-[11px] font-bold leading-4">{node.label}</span>
                        <span className="font-mono text-[10px] text-slate-400">{node.incoming}/{node.outgoing}</span>
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
