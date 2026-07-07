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
  Scan,
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
const NODE_WIDTH = 220;
const NODE_HEIGHT = 74;
const SELECTED_NODE_WIDTH = 270;
const SELECTED_NODE_HEIGHT = 92;
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

const truncateLabel = (value: string, maxLength = 26) => {
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength - 1)}...`;
};

const formatNodeSubtitle = (node: DependencyNode) => {
  const kind = node.isResolved ? node.type : 'unresolved';
  if (!node.isResolved) return `${kind} - ${node.incoming} in / ${node.outgoing} out`;
  return `${kind} - ${node.incoming} in / ${node.outgoing} out`;
};

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
    const startY = Math.max(140, 370 - (layerNodes.length * 58));

    layerNodes.forEach((node, index) => {
      node.x = x;
      node.y = startY + index * 124;
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
  const maxColumnSize = Math.max(incomingNodes.length, Math.ceil(outgoingNodes.length / 2), focusNodes.length);
  const centerY = Math.max(330, maxColumnSize * 58 + 120);
  const centerX = 590;
  const spacing = 112;

  focusNodes.forEach((node, index) => {
    node.x = centerX;
    node.y = centerY + (index - (focusNodes.length - 1) / 2) * spacing;
  });

  incomingNodes.forEach((node, index) => {
    node.x = centerX - 410;
    node.y = centerY + (index - (incomingNodes.length - 1) / 2) * spacing;
  });

  outgoingNodes.forEach((node, index) => {
    const column = outgoingNodes.length > 8 ? index % 2 : 0;
    const row = outgoingNodes.length > 8 ? Math.floor(index / 2) : index;
    const rowCount = outgoingNodes.length > 8 ? Math.ceil(outgoingNodes.length / 2) : outgoingNodes.length;
    node.x = centerX + 410 + column * 270;
    node.y = centerY + (row - (rowCount - 1) / 2) * spacing;
  });

  return nodes;
};

const buildOverviewNodes = (stats: DependencyGraphStats): DependencyNode[] => {
  const groups: Array<Pick<DependencyNode, 'id' | 'label' | 'type' | 'groupCount' | 'subtitle'> & { x: number; y: number }> = [
    { id: 'group:uploaded', label: 'Uploaded Files', type: 'group', groupCount: stats.totalFiles, subtitle: 'All files preserved in explorer', x: 160, y: 170 },
    { id: 'group:connected', label: 'Connected Files', type: 'program', groupCount: stats.connectedFiles, subtitle: 'Files with detected relations', x: 430, y: 170 },
    { id: 'group:isolated', label: 'Isolated Files', type: 'file', groupCount: stats.isolatedFiles, subtitle: 'Hidden from graph canvas', x: 700, y: 170 },
    { id: 'group:external', label: 'Unresolved Targets', type: 'external', groupCount: stats.unresolvedTargets, subtitle: 'Referenced but not uploaded', x: 970, y: 170 },
    { id: 'group:relations', label: 'Relations', type: 'copybook', groupCount: stats.relations, subtitle: 'Dependency edges detected', x: 565, y: 350 },
  ];

  return groups.map((group) => ({
    ...group,
    incoming: 0,
    outgoing: 0,
    isResolved: true,
  }));
};

const statusForMode = (mode: GraphMode, stats: DependencyGraphStats, nodeCount: number, linkCount: number, selectedNode?: DependencyNode) => {
  if (mode === 'overview') {
    return `Overview: ${stats.totalFiles} uploaded files, ${stats.connectedFiles} connected files, ${stats.unresolvedTargets} unresolved targets.`;
  }

  if (mode === 'isolated') {
    return `${stats.isolatedFiles} isolated files shown in the file explorer`;
  }

  if (mode === 'impact' && selectedNode) {
    return `Impact View: ${selectedNode.label} - ${selectedNode.outgoing} outgoing dependencies - ${selectedNode.incoming} incoming dependencies`;
  }

  if (mode === 'connected') {
    return `Showing connected dependency map: ${stats.connectedFiles} connected files, ${stats.unresolvedTargets} unresolved targets, ${stats.isolatedFiles} isolated files hidden from graph.`;
  }

  if (mode === 'unresolved') {
    return `Showing unresolved references: ${stats.unresolvedTargets} unresolved targets with referencing files.`;
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
  const [showTwoHop, setShowTwoHop] = useState(false);

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
      setShowTwoHop(false);
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

  const selectedNode = selectedNodeId ? nodeById.get(selectedNodeId) : undefined;

  const visibleLinks = useMemo(() => {
    if (mode === 'overview' || mode === 'isolated') return [];
    if (mode === 'impact') {
      const firstHopLinks = filteredLinks.filter((link) => focusedNodeIds.has(link.from) || focusedNodeIds.has(link.to));
      if (!showTwoHop) return firstHopLinks;

      const firstHopIds = new Set<string>(focusedNodeIds);
      firstHopLinks.forEach((link) => {
        firstHopIds.add(link.from);
        firstHopIds.add(link.to);
      });
      return filteredLinks.filter((link) => firstHopIds.has(link.from) || firstHopIds.has(link.to));
    }
    if (mode === 'unresolved') {
      return filteredLinks.filter((link) => {
        const from = nodeById.get(link.from);
        const to = nodeById.get(link.to);
        return from?.isResolved === false || to?.isResolved === false;
      });
    }
    return filteredLinks;
  }, [filteredLinks, focusedNodeIds, mode, nodeById, showTwoHop]);

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
    const itemWidth = mode === 'overview' ? GROUP_WIDTH : NODE_WIDTH;
    const itemHeight = mode === 'overview' ? GROUP_HEIGHT : NODE_HEIGHT;
    const maxX = Math.max(1360, ...displayNodes.map((node) => node.x + itemWidth + 220));
    const maxY = Math.max(720, ...displayNodes.map((node) => node.y + itemHeight + 180));
    return { width: maxX, height: maxY };
  }, [displayNodes, mode]);

  const statusText = statusForMode(mode, stats, displayNodes.length, visibleLinks.length, selectedNode);

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
        initialScale={mode === 'impact' ? 0.82 : 0.9}
        minScale={0.1}
        maxScale={4}
        wheel={{ smoothStep: 0.002 }}
        centerOnInit
      >
        {({ zoomIn, zoomOut, centerView }) => (
          <div className="relative w-full h-full bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden min-h-[620px]">
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
                  <>
                  <button
                    type="button"
                    onClick={handleOverviewClick}
                    className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs font-bold text-slate-200 transition-colors hover:bg-slate-700"
                  >
                    <ArrowLeft size={14} />
                    Back to Overview
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowTwoHop((value) => !value)}
                    className={`rounded-lg border px-3 py-2 text-xs font-bold transition-colors ${
                      showTwoHop
                        ? 'border-sky-400 bg-sky-500/20 text-sky-200'
                        : 'border-slate-700 bg-slate-800/80 text-slate-200 hover:bg-slate-700'
                    }`}
                  >
                    {showTwoHop ? '1-hop only' : 'Expand 2-hop'}
                  </button>
                  </>
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
              <button type="button" aria-label="Fit graph to view" title="Fit to view" onClick={() => centerView(mode === 'impact' ? 0.82 : 0.9, 250)} className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700">
                <Scan size={20} />
              </button>
              <button type="button" aria-label={isFullscreen ? 'Exit fullscreen' : 'Open fullscreen graph'} title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen graph'} onClick={() => setIsFullscreen((value) => !value)} className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700">
                {isFullscreen ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
              </button>
              <button type="button" aria-label="Center graph" title="Center graph" onClick={() => centerView(mode === 'impact' ? 0.82 : 0.9, 250)} className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700">
                <Crosshair size={20} />
              </button>
              <button type="button" aria-label="Zoom out" title="Zoom out" onClick={() => zoomOut()} className="bg-slate-800/80 backdrop-blur-md text-white p-2 rounded-lg hover:bg-slate-700 transition-colors border border-slate-700">
                <ZoomOut size={20} />
              </button>
            </div>

            {nodes.length === 0 ? (
              <div className="flex h-full min-h-[620px] items-center justify-center text-center text-slate-500">
                <div>
                  <p className="text-sm font-bold text-slate-300">No uploaded files found</p>
                  <p className="mt-1 text-xs">Upload source files for the active run to populate this graph.</p>
                </div>
              </div>
            ) : mode === 'isolated' ? (
              <div className="flex h-full min-h-[620px] items-center justify-center text-center text-slate-500">
                <div>
                  <p className="text-sm font-bold text-slate-300">Isolated files are shown in the explorer</p>
                  <p className="mt-1 text-xs">Use the left panel to search and inspect files with no detected dependencies.</p>
                </div>
              </div>
            ) : displayNodes.length === 0 ? (
              <div className="flex h-full min-h-[620px] items-center justify-center text-center text-slate-500">
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
                      const fromSelected = focusedNodeIds.has(fromNode.id);
                      const toSelected = focusedNodeIds.has(toNode.id);
                      const fromWidth = fromSelected ? SELECTED_NODE_WIDTH : NODE_WIDTH;
                      const fromHeight = fromSelected ? SELECTED_NODE_HEIGHT : NODE_HEIGHT;
                      const toWidth = toSelected ? SELECTED_NODE_WIDTH : NODE_WIDTH;
                      const toHeight = toSelected ? SELECTED_NODE_HEIGHT : NODE_HEIGHT;
                      const x1 = fromNode.x + fromWidth;
                      const y1 = fromNode.y + fromHeight / 2;
                      const x2 = toNode.x;
                      const y2 = toNode.y + toHeight / 2;
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
                            strokeWidth={mode === 'impact' ? 3.5 : 2.5}
                            strokeOpacity={mode === 'impact' ? 0.95 : 0.72}
                            strokeDasharray={toNode.isResolved ? undefined : '7 7'}
                            markerEnd={`url(#${markerId})`}
                          />
                          {mode === 'impact' && (
                            <g transform={`translate(${(x1 + x2) / 2 - 44}, ${(y1 + y2) / 2 - 15})`}>
                              <rect width="88" height="24" rx="8" fill="#020617" stroke={color} strokeOpacity="0.65" />
                              <text x="44" y="16" fill={color} fontSize="11" fontWeight="800" textAnchor="middle">
                                {link.relationType}
                              </text>
                            </g>
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
                        className={`absolute flex flex-col justify-center rounded-2xl border px-4 py-3 text-left shadow-lg transition-all hover:scale-[1.03] ${chrome.className} ${isSelected ? 'ring-2 ring-emerald-300 ring-offset-4 ring-offset-slate-950 brightness-125 shadow-emerald-950/50' : ''}`}
                        style={{
                          left: node.x,
                          top: node.y,
                          width: isSelected ? `${SELECTED_NODE_WIDTH}px` : `${NODE_WIDTH}px`,
                          height: isSelected ? `${SELECTED_NODE_HEIGHT}px` : `${NODE_HEIGHT}px`,
                        }}
                        aria-pressed={isSelected}
                        title={`${node.file?.filepath || node.label} - ${node.incoming} incoming, ${node.outgoing} outgoing`}
                      >
                        <span className="flex min-w-0 items-center gap-3">
                          <span className={`shrink-0 rounded-full border border-white/10 bg-slate-950/50 ${isSelected ? 'p-3' : 'p-2'}`}>{chrome.icon}</span>
                          <span className="min-w-0">
                            <span className={`${isSelected ? 'text-base' : 'text-sm'} block truncate font-black leading-5`}>{truncateLabel(node.label, isSelected ? 28 : 24)}</span>
                            <span className="mt-1 block truncate text-xs text-slate-400">
                              {formatNodeSubtitle(node)}
                            </span>
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
