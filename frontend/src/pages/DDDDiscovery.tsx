import { Database, FileCode, GitBranch } from 'lucide-react';
import type { DependencyLink, DependencyNode } from './DependencyGraph';
import type { FileRecord } from '../services/api';

type DDDDiscoveryProps = {
  selectedNode: DependencyNode | null;
  files: FileRecord[];
  links: DependencyLink[];
};

const formatStatus = (value?: string) => (value || 'PENDING').replaceAll('_', ' ');

const DDDDiscovery = ({ selectedNode, files, links }: DDDDiscoveryProps) => {
  const selectedFile = selectedNode?.file ?? files[0] ?? null;
  const selectedLinks = selectedNode
    ? links.filter((link) => link.from === selectedNode.id || link.to === selectedNode.id)
    : [];

  if (!selectedFile) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-8 text-center text-slate-500">
        <p className="text-sm font-bold text-slate-300">No file details available</p>
        <p className="mt-1 text-xs">Upload files for the active run to inspect them here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/5 p-4">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3 min-w-0">
            <div className="flex items-center gap-3">
              {selectedNode?.type === 'program' ? (
                <FileCode size={22} className="text-emerald-400" />
              ) : (
                <Database size={22} className="text-amber-400" />
              )}
              <div className="min-w-0">
                <h3 className="truncate text-lg font-bold text-white">{selectedFile.filename}</h3>
                <p className="truncate text-xs font-mono text-slate-500">{selectedFile.filepath || selectedFile.filename}</p>
              </div>
            </div>
            <p className="text-sm leading-6 text-slate-300">
              This detail is loaded from the active run upload records. No inferred modernization target or domain role is shown unless it exists in backend data.
            </p>
          </div>

          <div className="grid min-w-[320px] grid-cols-2 gap-3 text-xs">
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Language</p>
              <p className="font-mono text-blue-400">{selectedFile.detected_lang || 'unknown'}</p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <p className="mb-1 font-bold uppercase tracking-widest text-slate-500">Status</p>
              <p className="text-slate-300">{formatStatus(selectedFile.status)}</p>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-4">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-white">
          <GitBranch size={16} className="text-emerald-400" />
          Dependencies For Selected File
        </div>
        {selectedLinks.length > 0 ? (
          <div className="grid grid-cols-1 gap-2 lg:grid-cols-2">
            {selectedLinks.map((link) => {
              const from = files.find((file) => file.id === link.from);
              const to = files.find((file) => file.id === link.to);

              return (
                <div key={link.id} className="rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs">
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate font-mono text-slate-300">{from?.filename || link.from}</span>
                    <span className="shrink-0 rounded bg-slate-800 px-2 py-1 font-bold uppercase text-slate-400">{link.relationType}</span>
                    <span className="truncate font-mono text-slate-300">{to?.filename || link.to}</span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No dependency relation was found between uploaded files for this selection.</p>
        )}
      </div>

      <div className="border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
            <tr className="border-b border-slate-700">
              <th className="p-4">Uploaded File</th>
              <th className="p-4">Path</th>
              <th className="p-4">Language</th>
              <th className="p-4">Status</th>
            </tr>
          </thead>
          <tbody className="text-slate-300 divide-y divide-slate-700">
            {files.map((file) => {
              const isSelected = file.id === selectedFile.id;

              return (
                <tr key={file.id} className={`${isSelected ? 'bg-emerald-500/10' : 'hover:bg-slate-800/30'} transition-colors`}>
                  <td className={`p-4 font-mono text-xs ${isSelected ? 'text-emerald-300' : 'text-slate-300'}`}>{file.filename}</td>
                  <td className="p-4 font-mono text-xs text-slate-500">{file.filepath || file.filename}</td>
                  <td className="p-4 text-xs text-blue-300">{file.detected_lang || 'unknown'}</td>
                  <td className="p-4">
                    <span className="bg-slate-700 text-slate-300 px-2 py-1 rounded text-[10px] uppercase font-bold">
                      {formatStatus(file.status)}
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
