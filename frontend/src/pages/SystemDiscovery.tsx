import React from 'react';
import DependencyGraph from './DependencyGraph';
import DDDDiscovery from './DDDDiscovery';
import { Share2, GitBranch } from 'lucide-react';

const SystemDiscovery = () => {
  return (
    <div className="space-y-6 h-full flex flex-col">
      {/* Header Section */}
      <div className="flex justify-between items-center">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Share2 className="text-indigo-500" size={28} />
            <h1 className="text-3xl font-bold text-white">System Discovery</h1>
          </div>
          <p className="text-slate-400">
            Deep dive into application architecture and domain mappings side-by-side.
          </p>
        </div>
        
        <div className="flex items-center gap-4 text-xs font-bold uppercase tracking-widest">
          <div className="flex items-center gap-2 text-slate-500">
            <div className="w-2 h-2 rounded-full bg-indigo-500" />
            <span>Architectural Map (40%)</span>
          </div>
          <div className="flex items-center gap-2 text-slate-500">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span>Domain Mapping (60%)</span>
          </div>
        </div>
      </div>

      {/* Side-by-Side Layout */}
      <div className="flex gap-6 h-[calc(100vh-220px)] w-full">
        
        {/* Left Column: Dependency Graph (40%) */}
        <div className="w-[40%] flex flex-col gap-4">
          <div className="flex items-center gap-2 text-white font-bold text-sm px-2">
            <Share2 size={16} className="text-indigo-400" />
            Dependency Graph
          </div>
          <div className="flex-1 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50 shadow-inner">
             <DependencyGraph />
          </div>
        </div>

        {/* Right Column: DDD Discovery (60%) */}
        <div className="w-[60%] flex flex-col gap-4">
          <div className="flex items-center gap-2 text-white font-bold text-sm px-2">
            <GitBranch size={16} className="text-emerald-400" />
            DDD Domain Mapping
          </div>
          <div className="flex-1 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/50 shadow-inner">
            <DDDDiscovery />
          </div>
        </div>

      </div>
    </div>
  );
};

export default SystemDiscovery;
