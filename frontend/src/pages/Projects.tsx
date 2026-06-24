import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, CheckCircle2, Clock, Calendar, ArrowRight, Database } from 'lucide-react';

const COMPLETED_PROJECTS = [
  { id: 'p1', name: 'Inventory_Legacy_v2', date: 'Oct 2023', duration: '4 Months', status: 'Deployed', health: '98%' },
  { id: 'p2', name: 'Billing_System_Mainframe', date: 'Jun 2023', duration: '6 Months', status: 'Deployed', health: '94%' },
  { id: 'p3', name: 'HR_Portal_Cobol', date: 'Jan 2023', duration: '3 Months', status: 'Archived', health: '88%' },
];

const Projects = () => {
  const navigate = useNavigate();

  const handleProjectSelect = () => {
    // Selecting the project moves us to the next stage: Source Ingestion
    navigate('/source-files');
  };

  return (
    <div className="space-y-10">
      <div className="flex justify-between items-center">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold text-white">Project Portfolio</h1>
          <p className="text-slate-400">Manage your legacy modernization workspaces.</p>
        </div>
        <button 
          onClick={() => navigate('/source-files')} // New project starts with source upload
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl font-bold flex items-center gap-2 transition-all shadow-lg shadow-indigo-500/20"
        >
          <Plus size={20} /> Create New Project
        </button>
      </div>

      {/* CURRENT ACTIVE PROJECT */}
      <div className="glass-card p-8 rounded-3xl border-indigo-500/50 bg-indigo-500/5 border-2 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-4">
          <span className="px-3 py-1 rounded-full bg-indigo-500 text-white text-[10px] font-bold uppercase">Active</span>
        </div>
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-6">
            <div className="p-4 bg-indigo-600 rounded-2xl text-white shadow-xl shadow-indigo-500/40">
              <Database size={32} />
            </div>
            <div className="space-y-1">
              <h2 className="text-2xl font-bold text-white">Payroll System v1</h2>
              <p className="text-slate-400 text-sm">Created 12 days ago • 422 Source Files • Java 21 Target</p>
            </div>
          </div>
          <button 
            onClick={handleProjectSelect} 
            className="px-6 py-3 bg-white text-indigo-900 rounded-xl font-bold hover:bg-indigo-50 transition-all flex items-center gap-2"
          >
            Continue Project <ArrowRight size={18} />
          </button>
        </div>
      </div>

      {/* COMPLETED PROJECTS TIMELINE */}
      <div className="space-y-6">
        <h3 className="text-xl font-bold text-white flex items-center gap-2">
          <Clock size={20} className="text-slate-500" /> Completed Modernizations
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {COMPLETED_PROJECTS.map((proj) => (
            <div key={proj.id} className="glass-card p-6 rounded-2xl border-slate-800 hover:border-slate-600 transition-all">
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-slate-800 rounded-lg text-slate-400">
                  <Database size={20} />
                </div>
                <div className="flex items-center gap-1 text-emerald-400 text-[10px] font-bold uppercase">
                  <CheckCircle2 size={12} /> {proj.status}
                </div>
              </div>
              <h4 className="text-white font-bold mb-1">{proj.name}</h4>
              <div className="flex items-center gap-4 text-xs text-slate-500">
                <div className="flex items-center gap-1"><Calendar size={12} /> {proj.date}</div>
                <div className="flex items-center gap-1"><Clock size={12} /> {proj.duration}</div>
              </div>
              <div className="mt-4 pt-4 border-t border-slate-800 flex justify-between items-center">
                <span className="text-xs text-slate-500">Health Score:</span>
                <span className="text-sm font-bold text-white">{proj.health}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Projects;
