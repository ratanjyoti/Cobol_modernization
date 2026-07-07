import { useMemo, useState } from 'react';
import { AlertTriangle, ChevronDown, Database, FileCode, GitBranch, Search } from 'lucide-react';
import type { DependencyLink, DependencyNode } from './DependencyGraph';
import type { FileRecord } from '../services/api';

type DDDDiscoveryProps = {
  selectedNode: DependencyNode | null;
  files: FileRecord[];
  links: DependencyLink[];
  nodes: DependencyNode[];
};

const formatStatus = (value?: string) => (value || 'PENDING').replaceAll('_', ' ');
const formatType = (value?: string) => (value || 'file').replaceAll('_', ' ');

const getComplexityScore = (file?: FileRecord) => {
  const maybeFile = file as (FileRecord & { complexity_score?: number; complexity?: number; score?: number }) | undefined;
  return maybeFile?.complexity_score ?? maybeFile?.complexity ?? maybeFile?.score;
};

const RelationRows = ({
  title,
  rows,
  nodes,
  emptyText,
}: {
  title: string;
  rows: DependencyLink[];
  nodes: DependencyNode[];
  emptyText: string;
}) => (
  <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
    <div className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
      <GitBranch size={16} className="text-emerald-400" />
      {title}
    </div>
    {rows.length > 0 ? (
      <div className="space-y-2">
        {rows.map((link) => {
          const from = nodes.find((node) => node.id === link.from);
          const to = nodes.find((node) => node.id === link.to);

          return (
            <div key={link.id} className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-xs">
              <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3">
                <span className="truncate font-mono text-slate-300">{from?.label || link.from}</span>
                <span className="shrink-0 rounded bg-slate-800 px-2 py-1 font-bold uppercase text-slate-400">{link.relationType}</span>
                <span className={`truncate font-mono ${to?.isResolved === false ? 'text-orange-300' : 'text-slate-300'}`}>{to?.label || link.to}</span>
              </div>
            </div>
          );
        })}
      </div>
    ) : (
      <p className="text-sm text-slate-500">{emptyText}</p>
    )}
  </div>
);

const DDDDiscovery = ({ selectedNode, files, links, nodes }: DDDDiscoveryProps) => {
  const [showAllFiles, setShowAllFiles] = useState(false);
  const [fileSearch, setFileSearch] = useState('');
  const selectedFile = selectedNode?.file ?? files[0] ?? null;
  const incomingLinks = selectedNode ? links.filter((link) => link.to === selectedNode.id) : [];
  const outgoingLinks = selectedNode ? links.filter((link) => link.from === selectedNode.id) : [];
  const impactedLinks = outgoingLinks.filter((link) => nodes.find((node) => node.id === link.to)?.isResolved !== false);
  const missingLinks = selectedNode
    ? links.filter((link) => {
        const from = nodes.find((node) => node.id === link.from);
        const to = nodes.find((node) => node.id === link.to);
        return (link.from === selectedNode.id || link.to === selectedNode.id) && (from?.isResolved === false || to?.isResolved === false);
      })
    : [];
  const filteredNodes = useMemo(() => {
    const query = fileSearch.trim().toLowerCase();
    return nodes
      .filter((node) => !query || node.label.toLowerCase().includes(query) || (node.file?.filepath || '').toLowerCase().includes(query))
      .sort((a, b) => (b.incoming + b.outgoing) - (a.incoming + a.outgoing) || a.label.localeCompare(b.label))
      .slice(0, 50);
  }, [fileSearch, nodes]);

  if (!selectedNode && !selectedFile) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-8 text-center text-slate-500">
        <p className="text-sm font-bold text-slate-300">No dependency details available</p>
        <p className="mt-1 text-xs">Upload files for the active run to inspect them here.</p>
      </div>
    );
  }

  const displayName = selectedNode?.label || selectedFile?.filename || 'Unknown node';
  const displayPath = selectedFile?.filepath || (selectedNode?.isResolved ? displayName : 'Not found as an uploaded file');
  const displayType = selectedNode?.type || 'file';
  const complexityScore = getComplexityScore(selectedFile || undefined);
  const isIsolated = selectedNode ? selectedNode.incoming + selectedNode.outgoing === 0 && selectedNode.isResolved : false;

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/5 p-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-3 min-w-0">
            <div className="flex items-center gap-3">
              {displayType === 'table' ? (
                <Database size={22} className="text-rose-400" />
              ) : (
                <FileCode size={22} className="text-emerald-400" />
              )}
              <div className="min-w-0">
                <h3 className="truncate text-lg font-bold text-white">{displayName}</h3>
                <p className="truncate text-xs font-mono text-slate-500">{displayPath}</p>
              </div>
            </div>
            {selectedNode?.isResolved === false ? (
              <p className="inline-flex items-center gap-2 rounded-lg border border-orange-500/40 bg-orange-500/10 px-3 py-2 text-sm text-orange-200">
                <AlertTriangle size={16} />
                This dependency was referenced in code but was not found among uploaded files.
              </p>
            ) : isIsolated ? (
              <p className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-400">This file is isolated.</p>
            ) : (
              <p className="text-sm leading-6 text-slate-300">This file is part of the discovered dependency map. Incoming and outgoing relations are split below for impact analysis.</p>
            )}
          </div>

          <div className="grid w-full gap-2 text-xs sm:grid-cols-2 xl:w-full">
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Type</p>
              <p className="font-mono text-blue-400">{formatType(displayType)}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Resolved</p>
              <p className={selectedNode?.isResolved === false ? 'text-orange-300' : 'text-emerald-300'}>{selectedNode?.isResolved === false ? 'no' : 'yes'}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Incoming</p>
              <p className="font-mono text-emerald-400">{selectedNode?.incoming ?? 0}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Outgoing</p>
              <p className="font-mono text-amber-400">{selectedNode?.outgoing ?? 0}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Status</p>
              <p className="text-slate-300">{selectedNode?.isResolved === false ? 'UNRESOLVED' : formatStatus(selectedFile?.status)}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Complexity</p>
              <p className="font-mono text-indigo-300">{complexityScore ?? 'n/a'}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-3">
        <RelationRows title="Incoming dependencies" rows={incomingLinks} nodes={nodes} emptyText="No incoming dependencies found" />
        <RelationRows title="Outgoing dependencies" rows={outgoingLinks} nodes={nodes} emptyText="No outgoing dependencies found" />
        <RelationRows title="Impacted files" rows={impactedLinks} nodes={nodes} emptyText={isIsolated ? 'This file is isolated' : 'No impacted files found'} />
        <RelationRows title="Missing / unresolved targets" rows={missingLinks} nodes={nodes} emptyText="No missing or unresolved targets found" />
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-950">
        <button
          type="button"
          onClick={() => setShowAllFiles((value) => !value)}
          className="flex w-full items-center justify-between gap-3 p-4 text-left text-sm font-bold text-white"
        >
          <span>Show all uploaded files</span>
          <span className="flex items-center gap-2 font-mono text-xs text-slate-500">
            {nodes.length} nodes
            <ChevronDown size={16} className={`transition-transform ${showAllFiles ? 'rotate-180' : ''}`} />
          </span>
        </button>

        {showAllFiles && (
          <div className="border-t border-slate-800 p-3">
            <label className="relative mb-3 block">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                value={fileSearch}
                onChange={(event) => setFileSearch(event.target.value)}
                placeholder="Search uploaded files"
                className="w-full rounded-lg border border-slate-700 bg-slate-900 py-2 pl-9 pr-3 text-sm text-slate-200 outline-none placeholder:text-slate-600 focus:border-emerald-400"
              />
            </label>

            <div className="max-h-[360px] overflow-auto rounded-lg border border-slate-800">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
                  <tr className="border-b border-slate-700">
                    <th className="p-3">Graph Node</th>
                    <th className="p-3">Kind</th>
                    <th className="p-3">Links</th>
                    <th className="p-3">Resolved</th>
                  </tr>
                </thead>
                <tbody className="text-slate-300 divide-y divide-slate-700">
                  {filteredNodes.map((node) => {
                    const isSelected = node.id === selectedNode?.id;

                    return (
                      <tr key={node.id} className={`${isSelected ? 'bg-emerald-500/10' : 'hover:bg-slate-800/30'} transition-colors`}>
                        <td className={`p-3 font-mono text-xs ${isSelected ? 'text-emerald-300' : 'text-slate-300'}`} title={node.file?.filepath || node.label}>{node.label}</td>
                        <td className="p-3 text-xs text-blue-300">{formatType(node.type)}</td>
                        <td className="p-3 font-mono text-xs text-slate-500">{node.incoming} in / {node.outgoing} out</td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded text-[10px] uppercase font-bold ${node.isResolved ? 'bg-emerald-500/10 text-emerald-300' : 'bg-orange-500/10 text-orange-300'}`}>
                            {node.isResolved ? 'yes' : 'no'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-xs text-slate-500">Showing up to 50 rows. Use search to narrow large uploads.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DDDDiscovery;
