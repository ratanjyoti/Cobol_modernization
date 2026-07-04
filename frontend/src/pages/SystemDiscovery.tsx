import { useEffect, useMemo, useRef, useState } from 'react';
import DependencyGraph, { type DependencyLink, type DependencyNode } from './DependencyGraph';
import DDDDiscovery from './DDDDiscovery';
import { FileText, GitBranch, Loader2, Share2 } from 'lucide-react';
import { ProjectAPI } from '../services/api';
import type { DependencyRelation, FileRecord } from '../services/api';

const normalizeName = (value: string) => value.trim().toLowerCase().replace(/\\/g, '/');
const withoutExtension = (value: string) => value.replace(/\.[^.\/]+$/, '');

const isProgramFile = (file: FileRecord) => {
  const lang = (file.detected_lang || '').toLowerCase();
  const name = file.filename.toLowerCase();
  return lang.includes('cobol') || lang.includes('jcl') || name.endsWith('.cbl') || name.endsWith('.cob') || name.endsWith('.jcl');
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

const buildGraphNodes = (files: FileRecord[]): DependencyNode[] => {
  if (files.length === 0) return [];

  const centerX = 520;
  const centerY = 320;
  const radiusX = Math.max(320, files.length * 42);
  const radiusY = Math.max(180, files.length * 24);

  return files.map((file, index) => {
    const angle = (Math.PI * 2 * index) / files.length - Math.PI / 2;
    const single = files.length === 1;

    return {
      id: file.id,
      label: file.filename,
      type: isProgramFile(file) ? 'program' : 'file',
      x: Math.round(single ? centerX : centerX + Math.cos(angle) * radiusX),
      y: Math.round(single ? centerY : centerY + Math.sin(angle) * radiusY),
      file,
    };
  });
};

const buildGraphLinks = (files: FileRecord[], relations: DependencyRelation[]): DependencyLink[] => {
  const links: DependencyLink[] = [];
  const seen = new Set<string>();

  relations.forEach((relation) => {
    const source = findFileForRelationName(files, relation.source_file);
    const target = findFileForRelationName(files, relation.target_item);

    if (!source || !target || source.id === target.id) return;

    const key = `${source.id}->${target.id}:${relation.relation_type}`;
    if (seen.has(key)) return;
    seen.add(key);

    links.push({
      id: key,
      from: source.id,
      to: target.id,
      relationType: relation.relation_type,
    });
  });

  return links;
};

const SystemDiscovery = () => {
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [relations, setRelations] = useState<DependencyRelation[]>([]);
  const [selectedNode, setSelectedNode] = useState<DependencyNode | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const detailSectionRef = useRef<HTMLDivElement | null>(null);

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
        setError('Unable to load uploaded files for this run.');
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

  const nodes = useMemo(() => buildGraphNodes(files), [files]);
  const links = useMemo(() => buildGraphLinks(files, relations), [files, relations]);

  useEffect(() => {
    setSelectedNode((current) => {
      if (current && nodes.some((node) => node.id === current.id)) {
        return nodes.find((node) => node.id === current.id) || current;
      }
      return nodes[0] || null;
    });
  }, [nodes]);

  const handleNodeSelect = (node: DependencyNode) => {
    setSelectedNode(node);
    window.setTimeout(() => {
      detailSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 80);
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
            Dependency view for the active run. Nodes are loaded from uploaded backend files only.
          </p>
        </div>
        
        <div className="flex items-center gap-4 text-xs font-bold uppercase tracking-widest">
          <div className="flex items-center gap-2 text-slate-500">
            <div className="w-2 h-2 rounded-full bg-indigo-500" />
            <span>{files.length} Files</span>
          </div>
          <div className="flex items-center gap-2 text-slate-500">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>{links.length} File Links</span>
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
              <DependencyGraph nodes={nodes} links={links} selectedNodeId={selectedNode?.id} onNodeSelect={handleNodeSelect} />
            )}
          </div>

          <div ref={detailSectionRef} className="flex items-center justify-between px-2 scroll-mt-6">
            <div className="flex items-center gap-2 text-white font-bold text-sm">
              <FileText size={16} className="text-emerald-400" />
              File Details
            </div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-slate-500">
              <GitBranch size={14} className="text-emerald-500" />
              Uploaded File Data
            </div>
          </div>

          <div className="min-h-[320px] rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-inner">
            <DDDDiscovery selectedNode={selectedNode} files={files} links={links} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemDiscovery;
