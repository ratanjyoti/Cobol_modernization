import { useEffect, useMemo, useState } from 'react';
import DependencyGraph, {
  type DependencyGraphStats,
  type DependencyLink,
  type DependencyNode,
  type GraphMode
} from './DependencyGraph';
import DDDDiscovery from './DDDDiscovery';
import { Database, FileCode, FileQuestion, FileText, GitBranch, Loader2, Search, Share2 } from 'lucide-react';
import { getAnalysisWarmCache, warmDiscoveryData } from '../services/analysisPrefetch';
import type { DependencyRelation, FileRecord } from '../services/api';

const normalizeName = (value: string) => value.trim().toLowerCase().replace(/\\/g, '/');
const withoutExtension = (value: string) => value.replace(/\.[^.\/]+$/, '');

type ExplorerFilter = 'all' | 'connected' | 'isolated' | 'unresolved';

const isProgramFile = (file: FileRecord) => {
  const lang = (file.detected_lang || '').toLowerCase();
  const name = file.filename.toLowerCase();
  return lang.includes('cobol') || name.endsWith('.cbl') || name.endsWith('.cob');
};

const getFileType = (file: FileRecord): DependencyNode['type'] => {
  const lang = (file.detected_lang || '').toLowerCase();
  const name = file.filename.toLowerCase();

  if (lang.includes('jcl') || name.endsWith('.jcl')) return 'job';
  if (lang.includes('copy') || name.endsWith('.cpy')) return 'copybook';
  if (isProgramFile(file)) return 'program';
  if (name.endsWith('.sql')) return 'table';
  return 'file';
};

const getTargetType = (relationType: string): DependencyNode['type'] => {
  switch (relationType) {
    case 'CALLS':
      return 'external';
    case 'INCLUDES':
      return 'copybook';
    case 'READS_WRITES':
      return 'table';
    case 'IMPORTS':
    case 'REFERENCES':
    case 'INHERITS':
      return 'external';
    default:
      return 'external';
  }
};

const formatType = (type: DependencyNode['type']) => {
  switch (type) {
    case 'copybook':
      return 'copybook';
    case 'table':
      return 'data store';
    case 'job':
      return 'jcl job';
    case 'program':
      return 'program';
    case 'external':
      return 'external target';
    case 'group':
      return 'group';
    default:
      return 'file';
  }
};

const findFileForRelationName = (files: FileRecord[], relationName: string) => {
  const normalizedRelation = normalizeName(relationName);
  const relationBase = withoutExtension(normalizedRelation).split('/').pop();

  return files.find((file) => {
    const filename = normalizeName(file.filename);
    const filepath = normalizeName(file.filepath || file.filename);
    const filenameBase = withoutExtension(filename);
    const filepathBase = withoutExtension(filepath).split('/').pop();

    return (
      filename === normalizedRelation ||
      filepath === normalizedRelation ||
      filenameBase === normalizedRelation ||
      filenameBase === relationBase ||
      filepathBase === normalizedRelation ||
      filepathBase === relationBase
    );
  });
};

const unresolvedNodeId = (role: 'source' | 'target', relationType: string, name: string) => {
  return `${role}:${relationType}:${normalizeName(name)}`;
};

const buildGraphData = (files: FileRecord[], relations: DependencyRelation[]) => {
  const nodesById = new Map<string, DependencyNode>();
  const links: DependencyLink[] = [];
  const seenLinks = new Set<string>();

  files.forEach((file) => {
    const type = getFileType(file);
    nodesById.set(file.id, {
      id: file.id,
      label: file.filename,
      type,
      x: 0,
      y: 0,
      file,
      subtitle: `${formatType(type)} - ${file.detected_lang || 'unknown'}`,
      incoming: 0,
      outgoing: 0,
      isResolved: true,
    });
  });

  relations.forEach((relation) => {
    const resolvedSource = findFileForRelationName(files, relation.source_file);
    const resolvedTarget = findFileForRelationName(files, relation.target_item);
    const sourceType = resolvedSource ? getFileType(resolvedSource) : 'external';
    const targetType = resolvedTarget ? getFileType(resolvedTarget) : getTargetType(relation.relation_type);
    const sourceId = resolvedSource?.id || unresolvedNodeId('source', relation.relation_type, relation.source_file);
    const targetId = resolvedTarget?.id || unresolvedNodeId('target', relation.relation_type, relation.target_item);

    if (!nodesById.has(sourceId)) {
      nodesById.set(sourceId, {
        id: sourceId,
        label: relation.source_file,
        type: sourceType,
        x: 0,
        y: 0,
        subtitle: `${formatType(sourceType)} - unresolved source`,
        incoming: 0,
        outgoing: 0,
        isResolved: Boolean(resolvedSource),
      });
    }

    if (!nodesById.has(targetId)) {
      nodesById.set(targetId, {
        id: targetId,
        label: relation.target_item,
        type: targetType,
        x: 0,
        y: 0,
        subtitle: `${formatType(targetType)} - unresolved target`,
        incoming: 0,
        outgoing: 0,
        isResolved: Boolean(resolvedTarget),
      });
    }

    const key = `${sourceId}->${targetId}:${relation.relation_type}`;
    if (seenLinks.has(key)) return;
    seenLinks.add(key);

    links.push({
      id: key,
      from: sourceId,
      to: targetId,
      relationType: relation.relation_type,
    });
  });

  links.forEach((link) => {
    const source = nodesById.get(link.from);
    const target = nodesById.get(link.to);
    if (source) source.outgoing += 1;
    if (target) target.incoming += 1;
  });

  nodesById.forEach((node) => {
    const relationSummary = `${node.incoming} in - ${node.outgoing} out`;
    node.subtitle = node.isResolved
      ? `${formatType(node.type)} - ${relationSummary}`
      : `${formatType(node.type)} - unresolved`;
  });

  return { nodes: [...nodesById.values()], links };
};

const getNodeIcon = (node: DependencyNode) => {
  if (!node.isResolved) return <FileQuestion size={14} className="text-orange-300" />;
  if (node.type === 'table') return <Database size={14} className="text-rose-300" />;
  return <FileCode size={14} className="text-emerald-300" />;
};

const SystemDiscovery = () => {
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [relations, setRelations] = useState<DependencyRelation[]>([]);
  const [selectedNode, setSelectedNode] = useState<DependencyNode | null>(null);
  const [graphMode, setGraphMode] = useState<GraphMode>('overview');
  const [explorerFilter, setExplorerFilter] = useState<ExplorerFilter>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const runId = localStorage.getItem('active_run_id');

  useEffect(() => {
    let active = true;

    const loadGraphData = async () => {
      setError('');

      if (!runId) {
        setFiles([]);
        setRelations([]);
        setSelectedNode(null);
        setLoading(false);
        return;
      }

      const cached = getAnalysisWarmCache(runId);
      const hadWarmData = Boolean(cached?.files || cached?.relations);
      if (cached?.files) setFiles(cached.files);
      if (cached?.relations) setRelations(cached.relations);
      setLoading(!hadWarmData);

      try {
        const warmData = await warmDiscoveryData(runId, true);

        if (!active) return;
        setFiles(warmData.files || []);
        setRelations(warmData.relations || []);
      } catch {
        if (!active) return;
        setError('Unable to load dependency graph for this run.');
        if (!hadWarmData) {
          setFiles([]);
          setRelations([]);
          setSelectedNode(null);
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    loadGraphData();

    return () => {
      active = false;
    };
  }, [runId]);

  const graphData = useMemo(() => buildGraphData(files, relations), [files, relations]);
  const { nodes, links } = graphData;

  const connectedNodes = useMemo(() => nodes.filter((node) => node.incoming + node.outgoing > 0 && node.isResolved), [nodes]);
  const isolatedNodes = useMemo(() => nodes.filter((node) => node.incoming + node.outgoing === 0 && node.isResolved), [nodes]);
  const unresolvedNodes = useMemo(() => nodes.filter((node) => !node.isResolved), [nodes]);

  const graphStats: DependencyGraphStats = useMemo(() => ({
    totalFiles: files.length,
    connectedFiles: connectedNodes.length,
    isolatedFiles: isolatedNodes.length,
    unresolvedTargets: unresolvedNodes.length,
    relations: links.length,
    programs: nodes.filter((node) => node.isResolved && node.type === 'program').length,
    copybooks: nodes.filter((node) => node.isResolved && node.type === 'copybook').length,
    tables: nodes.filter((node) => node.isResolved && node.type === 'table').length,
    jobs: nodes.filter((node) => node.isResolved && node.type === 'job').length,
  }), [connectedNodes.length, files.length, isolatedNodes.length, links.length, nodes, unresolvedNodes.length]);

  const explorerCounts: Record<ExplorerFilter, number> = useMemo(() => ({
    all: nodes.length,
    connected: connectedNodes.length,
    isolated: isolatedNodes.length,
    unresolved: unresolvedNodes.length,
  }), [connectedNodes.length, isolatedNodes.length, nodes.length, unresolvedNodes.length]);

  const explorerNodes = useMemo(() => {
    const lowerSearch = searchTerm.trim().toLowerCase();

    return nodes
      .filter((node) => {
        if (explorerFilter === 'connected') return node.isResolved && node.incoming + node.outgoing > 0;
        if (explorerFilter === 'isolated') return node.isResolved && node.incoming + node.outgoing === 0;
        if (explorerFilter === 'unresolved') return !node.isResolved;
        return true;
      })
      .filter((node) => {
        if (!lowerSearch) return true;
        return node.label.toLowerCase().includes(lowerSearch) || (node.file?.filepath || '').toLowerCase().includes(lowerSearch);
      })
      .sort((a, b) => {
        const relationDelta = (b.incoming + b.outgoing) - (a.incoming + a.outgoing);
        return relationDelta || a.label.localeCompare(b.label);
      });
  }, [explorerFilter, nodes, searchTerm]);

  useEffect(() => {
    setSelectedNode((current) => {
      if (!current) return null;
      return nodes.find((node) => node.id === current.id) || null;
    });
  }, [nodes]);

  const handleModeChange = (mode: GraphMode) => {
    setGraphMode(mode);
    if (mode === 'overview') setSelectedNode(null);
    if (mode === 'isolated') setExplorerFilter('isolated');
    if (mode === 'unresolved') setExplorerFilter('unresolved');
    if (mode === 'connected') {
      setExplorerFilter('connected');
      setSelectedNode((current) => current ?? connectedNodes[0] ?? null);
    }
  };

  const handleNodeSelect = (node: DependencyNode) => {
    setSelectedNode(node);
    setGraphMode('impact');
  };

  const handleOverviewSelect = () => {
    setSelectedNode(null);
    setGraphMode('overview');
  };

  const summaryCards = [
    { label: 'Files', value: graphStats.totalFiles, color: 'text-indigo-300' },
    { label: 'Connected', value: graphStats.connectedFiles, color: 'text-emerald-300' },
    { label: 'Isolated', value: graphStats.isolatedFiles, color: 'text-slate-300' },
    { label: 'Unresolved', value: graphStats.unresolvedTargets, color: 'text-orange-300' },
    { label: 'Relations', value: graphStats.relations, color: 'text-sky-300' },
  ];

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="flex shrink-0 justify-between items-center">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Share2 className="text-indigo-500" size={28} />
            <h1 className="text-3xl font-bold text-white">System Discovery</h1>
          </div>
          <p className="text-slate-400">
            Dependency view for the active run, focused on meaningful connections while preserving every uploaded file in the explorer.
          </p>
        </div>

        <div className="hidden items-center gap-4 text-xs font-bold uppercase tracking-widest lg:flex">
          <div className="flex items-center gap-2 text-slate-500">
            <div className="w-2 h-2 rounded-full bg-indigo-500" />
            <span>{files.length} Files</span>
          </div>
          <div className="flex items-center gap-2 text-slate-500">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>{links.length} Relations</span>
          </div>
        </div>
      </div>

      <div className="grid shrink-0 gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {summaryCards.map((card) => (
          <div key={card.label} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
            <p className="text-xs font-bold uppercase tracking-widest text-slate-500">{card.label}</p>
            <p className={`mt-2 font-mono text-2xl font-black ${card.color}`}>{card.value}</p>
          </div>
        ))}
      </div>

      <div className="min-h-0 flex-1">
        <div className="grid min-h-0 grid-cols-1 gap-4 xl:h-[calc(100vh-245px)] xl:min-h-[720px] xl:grid-cols-[300px_minmax(0,1fr)]">
          <aside className="min-h-[420px] rounded-2xl border border-slate-800 bg-slate-900/60 p-4 shadow-inner xl:h-full">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <FileText size={16} className="text-indigo-400" />
                File Explorer
              </div>
              <span className="font-mono text-xs text-slate-500">{explorerNodes.length}</span>
            </div>

            <label className="relative block">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Search files"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 py-2 pl-9 pr-3 text-sm text-slate-200 outline-none transition-colors placeholder:text-slate-600 focus:border-indigo-400"
              />
            </label>

            <div className="my-4 grid grid-cols-2 gap-2">
              {(['all', 'connected', 'isolated', 'unresolved'] as ExplorerFilter[]).map((filter) => (
                <button
                  key={filter}
                  type="button"
                  onClick={() => setExplorerFilter(filter)}
                  className={`rounded-lg border px-3 py-2 text-xs font-bold capitalize transition-colors ${
                    explorerFilter === filter
                      ? 'border-indigo-400 bg-indigo-500/20 text-indigo-200'
                      : 'border-slate-700 bg-slate-950 text-slate-400 hover:bg-slate-800'
                  }`}
                >
                  {filter} <span className="ml-1 font-mono text-slate-500">{explorerCounts[filter]}</span>
                </button>
              ))}
            </div>

            <div className="h-[calc(100%-154px)] min-h-[260px] space-y-2 overflow-y-auto pr-1">
              {explorerNodes.map((node) => {
                const isSelected = node.id === selectedNode?.id;
                return (
                  <button
                    key={node.id}
                    type="button"
                    onClick={() => handleNodeSelect(node)}
                    className={`w-full rounded-lg border p-3 text-left transition-colors ${
                      isSelected
                        ? 'border-emerald-400 bg-emerald-500/10'
                        : 'border-slate-800 bg-slate-950 hover:border-slate-600 hover:bg-slate-800/60'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      <span className="mt-0.5 shrink-0">{getNodeIcon(node)}</span>
                      <span className="min-w-0">
                        <span className={`block truncate text-xs font-bold ${isSelected ? 'text-emerald-200' : 'text-slate-200'}`}>{node.label}</span>
                        <span className="mt-1 block truncate text-[11px] text-slate-500">{formatType(node.type)} - {node.file?.detected_lang || (node.isResolved ? 'uploaded' : 'unresolved')}</span>
                        <span className="mt-2 block font-mono text-[11px] text-slate-500">{node.incoming} in / {node.outgoing} out</span>
                      </span>
                    </div>
                  </button>
                );
              })}

              {explorerNodes.length === 0 && (
                <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 text-center text-sm text-slate-500">
                  No files match this filter.
                </div>
              )}
            </div>
          </aside>

          <main className="min-w-0 space-y-3 xl:h-full xl:overflow-y-auto">
            <div className="flex items-center justify-between px-2">
              <div className="flex items-center gap-2 text-white font-bold text-sm">
                <Share2 size={16} className="text-indigo-400" />
                Dependency Graph
              </div>
              <div className="text-xs font-semibold text-slate-500">
                Active run: <span className="font-mono text-slate-300">{runId || 'none'}</span>
                {selectedNode && <span className="ml-3">Selected: <span className="font-mono text-emerald-400">{selectedNode.label}</span></span>}
              </div>
            </div>

            <div className="h-[72vh] min-h-[640px] max-h-[780px] overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50 shadow-inner xl:h-[calc(100%-44px)]">
              {loading ? (
                <div className="flex h-full items-center justify-center gap-2 text-slate-400">
                  <Loader2 size={18} className="animate-spin" /> Loading graph files...
                </div>
              ) : error ? (
                <div className="flex h-full items-center justify-center text-sm text-red-300">{error}</div>
              ) : (
                <DependencyGraph
                  nodes={nodes}
                  links={links}
                  mode={graphMode}
                  stats={graphStats}
                  selectedNodeId={selectedNode?.id}
                  onModeChange={handleModeChange}
                  onNodeSelect={handleNodeSelect}
                  onOverviewSelect={handleOverviewSelect}
                />
              )}
            </div>

            {graphMode === 'isolated' && (
              <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-inner xl:hidden">
                <div className="mb-3 flex items-center justify-between">
                  <div className="text-sm font-bold text-white">Isolated Files</div>
                  <div className="font-mono text-xs text-slate-500">{isolatedNodes.length} files</div>
                </div>
                <div className="max-h-[360px] overflow-auto rounded-xl border border-slate-800">
                  <table className="w-full text-left text-sm">
                    <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
                      <tr>
                        <th className="p-3">File</th>
                        <th className="p-3">Type</th>
                        <th className="p-3">Language / Status</th>
                        <th className="p-3">Links</th>
                        <th className="p-3">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-300">
                      {isolatedNodes
                        .filter((node) => !searchTerm || node.label.toLowerCase().includes(searchTerm.toLowerCase()))
                        .map((node) => (
                          <tr key={node.id} className="hover:bg-slate-800/40">
                            <td className="p-3 font-mono text-xs">{node.label}</td>
                            <td className="p-3 text-xs text-blue-300">{formatType(node.type)}</td>
                            <td className="p-3 text-xs text-slate-400">{node.file?.detected_lang || 'unknown'} / {node.file?.status || 'uploaded'}</td>
                            <td className="p-3 font-mono text-xs text-slate-500">{node.incoming} in / {node.outgoing} out</td>
                            <td className="p-3">
                              <button type="button" onClick={() => handleNodeSelect(node)} className="rounded-lg border border-slate-700 px-3 py-1 text-xs font-bold text-slate-200 hover:bg-slate-800">
                                Inspect
                              </button>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            <section className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-inner">
              <div className="mb-3 flex items-center justify-between px-1">
                <div className="flex items-center gap-2 text-white font-bold text-sm">
                  <FileText size={16} className="text-emerald-400" />
                  Node Details
                </div>
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-500">
                  <GitBranch size={14} className="text-emerald-500" />
                  Dependency Data
                </div>
              </div>

              <DDDDiscovery selectedNode={selectedNode} files={files} links={links} nodes={nodes} />
            </section>
          </main>
        </div>
      </div>
    </div>
  );
};

export default SystemDiscovery;
