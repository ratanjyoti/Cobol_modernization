import { Database, FileCode, GitBranch } from 'lucide-react';
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

const DDDDiscovery = ({ selectedNode, files, links, nodes }: DDDDiscoveryProps) => {
  const selectedFile = selectedNode?.file ?? files[0] ?? null;
  const selectedLinks = selectedNode
    ? links.filter((link) => link.from === selectedNode.id || link.to === selectedNode.id)
    : [];

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

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/5 p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
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
            <p className="text-sm leading-6 text-slate-300">
              This node is part of the discovered dependency graph. Dashed links mean the dependency was referenced in code but no matching uploaded file was found.
            </p>
          </div>

          <div className="grid min-w-[320px] grid-cols-2 gap-3 text-xs">
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Type</p>
              <p className="font-mono text-blue-400">{formatType(displayType)}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Status</p>
              <p className="text-slate-300">{selectedNode?.isResolved === false ? 'UNRESOLVED TARGET' : formatStatus(selectedFile?.status)}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Incoming</p>
              <p className="font-mono text-emerald-400">{selectedNode?.incoming ?? 0}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Outgoing</p>
              <p className="font-mono text-amber-400">{selectedNode?.outgoing ?? 0}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
          <GitBranch size={16} className="text-emerald-400" />
          Dependencies For Selected Node
        </div>
        {selectedLinks.length > 0 ? (
          <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
            {selectedLinks.map((link) => {
              const from = nodes.find((node) => node.id === link.from);
              const to = nodes.find((node) => node.id === link.to);

              return (
                <div key={link.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs">
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate font-mono text-slate-300">{from?.label || link.from}</span>
                    <span className="shrink-0 rounded bg-slate-800 px-2 py-1 font-bold uppercase text-slate-400">{link.relationType}</span>
                    <span className="truncate font-mono text-slate-300">{to?.label || link.to}</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No dependency relation was found for this selection.</p>
        )}
      </div>

      <div className="border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
            <tr className="border-b border-slate-700">
              <th className="p-4">Graph Node</th>
              <th className="p-4">Kind</th>
              <th className="p-4">Links</th>
              <th className="p-4">Resolved</th>
            </tr>
          </thead>
          <tbody className="text-slate-300 divide-y divide-slate-700">
            {nodes.map((node) => {
              const isSelected = node.id === selectedNode?.id;

              return (
                <tr key={node.id} className={`${isSelected ? 'bg-emerald-500/10' : 'hover:bg-slate-800/30'} transition-colors`}>
                  <td className={`p-4 font-mono text-xs ${isSelected ? 'text-emerald-300' : 'text-slate-300'}`}>{node.label}</td>
                  <td className="p-4 text-xs text-blue-300">{formatType(node.type)}</td>
                  <td className="p-4 font-mono text-xs text-slate-500">{node.incoming} in / {node.outgoing} out</td>
                  <td className="p-4">
                    <span className="bg-slate-700 text-slate-300 px-2 py-1 rounded text-[10px] uppercase font-bold">
                      {node.isResolved ? 'yes' : 'no'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DDDDiscovery;
