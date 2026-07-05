import { useEffect, useMemo, useState } from 'react';
import DependencyGraph, { type DependencyLink, type DependencyNode } from './DependencyGraph';
import DDDDiscovery from './DDDDiscovery';
import { FileText, GitBranch, Loader2, Share2 } from 'lucide-react';
import { ProjectAPI } from '../services/api';
import type { DependencyRelation, FileRecord } from '../services/api';

const normalizeName = (value: string) => value.trim().toLowerCase().replace(/\\/g, '/');
const withoutExtension = (value: string) => value.replace(/\.[^.\/]+$/, '');
const nodeWidth = 240;

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

const placeUnlinkedNodes = (nodes: DependencyNode[]) => {
  const groups: DependencyNode['type'][] = ['job', 'program', 'copybook', 'table', 'file', 'external'];
  let index = 0;

  groups.forEach((type) => {
    nodes
      .filter((node) => node.type === type)
      .forEach((node) => {
        node.x = 120 + (index % 3) * 300;
        node.y = 120 + Math.floor(index / 3) * 110;
        index += 1;
      });
  });
};

const placeConnectedNodes = (nodes: DependencyNode[], links: DependencyLink[]) => {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const hub = [...nodes].sort((a, b) => (b.incoming + b.outgoing) - (a.incoming + a.outgoing))[0];

  if (!hub) return;

  hub.x = 520;
  hub.y = 310;

  const neighborIds = new Set<string>();
  links.forEach((link) => {
    if (link.from === hub.id) neighborIds.add(link.to);
    if (link.to === hub.id) neighborIds.add(link.from);
  });

  const neighbors = [...neighborIds]
    .map((id) => byId.get(id))
    .filter((node): node is DependencyNode => Boolean(node))
    .sort((a, b) => b.outgoing + b.incoming - (a.outgoing + a.incoming));

  const radiusX = Math.max(340, Math.min(620, neighbors.length * 62));
  const radiusY = Math.max(190, Math.min(360, neighbors.length * 36));

  neighbors.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(neighbors.length, 1) - Math.PI / 2;
    node.x = Math.round(hub.x + Math.cos(angle) * radiusX);
    node.y = Math.round(hub.y + Math.sin(angle) * radiusY);
  });

  const placed = new Set([hub.id, ...neighbors.map((node) => node.id)]);
  const remaining = nodes.filter((node) => !placed.has(node.id));
  const linkedRemaining = remaining.filter((node) => node.incoming + node.outgoing > 0);
  const unlinked = remaining.filter((node) => node.incoming + node.outgoing === 0);

  linkedRemaining.forEach((node, index) => {
    const side = index % 2 === 0 ? 1 : -1;
    node.x = hub.x + side * (560 + Math.floor(index / 2) * 280);
    node.y = 120 + (Math.floor(index / 2) % 5) * 108;
  });

  unlinked.forEach((node, index) => {
    node.x = 1040 + (index % 2) * 300;
    node.y = 120 + Math.floor(index / 2) * 104;
  });
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
    const source = findFileForRelationName(files, relation.source_file);
    if (!source) return;

    const resolvedTarget = findFileForRelationName(files, relation.target_item);
    const targetType = resolvedTarget ? getFileType(resolvedTarget) : getTargetType(relation.relation_type);
    const targetId = resolvedTarget?.id || `target:${relation.relation_type}:${normalizeName(relation.target_item)}`;

    if (!nodesById.has(targetId)) {
      nodesById.set(targetId, {
        id: targetId,
        label: relation.target_item,
        type: targetType,
        x: 0,
        y: 0,
        subtitle: `${formatType(targetType)} - unresolved`,
        incoming: 0,
        outgoing: 0,
        isResolved: Boolean(resolvedTarget),
      });
    }

    const key = `${source.id}->${targetId}:${relation.relation_type}`;
    if (seenLinks.has(key)) return;
    seenLinks.add(key);

    links.push({
      id: key,
      from: source.id,
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

  const nodes = [...nodesById.values()];
  if (links.length > 0) {
    placeConnectedNodes(nodes, links);
  } else {
    placeUnlinkedNodes(nodes);
  }

  nodes.forEach((node) => {
    node.x = Math.max(80, node.x);
    node.y = Math.max(80, node.y);
    if (node.x < 80 + nodeWidth) node.x = Math.max(80, node.x);
  });

  return { nodes, links };
};

const SystemDiscovery = () => {
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [relations, setRelations] = useState<DependencyRelation[]>([]);
  const [selectedNode, setSelectedNode] = useState<DependencyNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const runId = localStorage.getItem('active_run_id');

  useEffect(() => {
    let active = true;

    const loadGraphData = async () => {
      setLoading(true);
      setError('');

      if (!runId) {
        setFiles([]);
        setRelations([]);
        setSelectedNode(null);
        setLoading(false);
        return;
      }

      try {
        const [fileData, relationData] = await Promise.all([
          ProjectAPI.listFiles(runId),
          ProjectAPI.listRelations(runId),
        ]);

        if (!active) return;
        setFiles(fileData.files || []);
        setRelations(relationData.relations || []);
      } catch {
        if (!active) return;
        setError('Unable to load dependency graph for this run.');
        setFiles([]);
        setRelations([]);
        setSelectedNode(null);
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

  useEffect(() => {
    setSelectedNode((current) => {
      if (!current) return null;
      return nodes.find((node) => node.id === current.id) || null;
    });
  }, [nodes]);

  const handleNodeSelect = (node: DependencyNode) => {
    setSelectedNode(node);
  };

  const handleOverviewSelect = () => {
    setSelectedNode(null);
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex justify-between items-center">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Share2 className="text-indigo-500" size={28} />
            <h1 className="text-3xl font-bold text-white">System Discovery</h1>
          </div>
          <p className="text-slate-400">
            Dependency view for the active run, showing programs, copybooks, data stores, and unresolved external targets.
          </p>
        </div>
        
        <div className="flex items-center gap-4 text-xs font-bold uppercase tracking-widest">
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

      <div className="flex-1 min-h-0 overflow-y-auto pr-1">
        <div className="flex min-h-[calc(100vh-220px)] flex-col gap-6">
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

          <div className="h-[62vh] min-h-[560px] overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50 shadow-inner">
            {loading ? (
              <div className="flex h-full items-center justify-center gap-2 text-slate-400">
                <Loader2 size={18} className="animate-spin" /> Loading graph files...
              </div>
            ) : error ? (
              <div className="flex h-full items-center justify-center text-sm text-red-300">{error}</div>
            ) : (
              <DependencyGraph nodes={nodes} links={links} selectedNodeId={selectedNode?.id} onNodeSelect={handleNodeSelect} onOverviewSelect={handleOverviewSelect} />
            )}
          </div>

          <div className="flex items-center justify-between px-2 scroll-mt-6">
            <div className="flex items-center gap-2 text-white font-bold text-sm">
              <FileText size={16} className="text-emerald-400" />
              Node Details
            </div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-500">
              <GitBranch size={14} className="text-emerald-500" />
              Dependency Data
            </div>
          </div>

          <div className="min-h-[320px] rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-inner">
            <DDDDiscovery selectedNode={selectedNode} files={files} links={links} nodes={nodes} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemDiscovery;
