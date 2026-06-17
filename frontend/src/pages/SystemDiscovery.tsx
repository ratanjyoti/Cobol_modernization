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
          <h1 className="text-3xl font-bold text-white">System Discovery</h1>
          <p className="text-slate-400">Visual Relationship Mapping & Domain Decomposition</p>
        </div>
        
        <div className="flex items-center gap-3 text-xs font-bold">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <div className="w-2 h-2 rounded-full bg-blue-500" /> Program
          </div>
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <div className="w-2 h-2 rounded-full bg-amber-500" /> File / DB
          </div>
        </div>
      </div>

      {/* MAIN SPLIT VIEW */}
      <div className="flex gap-6 h-[calc(100vh-200px)] w-full">
        
        {/* LEFT SIDE: Dependency Graph (40%) */}
        <div className="w-[40%] glass-card rounded-3xl border border-slate-800 overflow-hidden flex flex-col relative">
          <div className="p-4 border-b border-slate-800 flex items-center gap-2 bg-slate-900/50">
            <Share2 size={16} className="text-indigo-400" />
            <span className="text-sm font-bold text-white">Relationship Graph</span>
          </div>
          <div className="flex-1 relative">
            <DependencyGraph />
          </div>
        </div>

        {/* RIGHT SIDE: DDD Mapping (60%) */}
        <div className="w-[60%] glass-card rounded-3xl border border-slate-800 overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-800 flex items-center gap-2 bg-slate-900/50">
            <GitBranch size={16} className="text-indigo-400" />
            <span className="text-sm font-bold text-white">Domain Mapping (Legacy → Modern)</span>
          </div>
          <div className="flex-1 overflow-y-auto p-6">
            <DDDDiscovery />
          </div>
        </div>

      </div>
    </div>
  );
};

export default SystemDiscovery;
