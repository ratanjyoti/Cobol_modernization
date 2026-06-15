import React from 'react';
import { Settings as SettingsIcon, Key, Cpu, Save, RefreshCw, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';

const Settings = () => {
  const handleOpenConfig = () => {
    if ((window as any).openAIConfig) {
      (window as any).openAIConfig();
    } else {
      toast.error("Configuration system not initialized");
    }
  };

  const clearConfig = () => {
    if (window.confirm("Are you sure you want to clear all AI configurations?")) {
      localStorage.removeItem('ai_config');
      toast.success("Configuration cleared!");
      window.location.reload();
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <div className="flex justify-between items-center">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Settings</h1>
          <p className="text-slate-400">Manage your account, API keys, and system preferences.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1 space-y-2">
          <div className="p-4 bg-indigo-600 text-white rounded-xl flex items-center gap-3 cursor-pointer">
            <Cpu size={18} /> <span className="font-bold">AI Configuration</span>
          </div>
          <div className="p-4 text-slate-400 hover:bg-slate-900 rounded-xl flex items-center gap-3 cursor-pointer transition-all">
            <Key size={18} /> <span className="font-medium">API Management</span>
          </div>
          <div className="p-4 text-slate-400 hover:bg-slate-900 rounded-xl flex items-center gap-3 cursor-pointer transition-all">
            <SettingsIcon size={18} /> <span className="font-medium">General Preferences</span>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="glass-card p-8 rounded-3xl border-slate-800">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-indigo-500/20 text-indigo-400 rounded-lg"><Cpu size={20}/></div>
              <h3 className="text-xl font-bold text-white">AI Model Settings</h3>
            </div>

            <p className="text-slate-400 text-sm mb-8">
              Configure which Large Language Model (LLM) the system uses to analyze your COBOL code.
            </p>

            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-6 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-white font-bold">Active Configuration</p>
                <p className="text-xs text-slate-500">Change your API keys or model selection.</p>
              </div>
              <button 
                onClick={handleOpenConfig}
                className="btn-primary flex items-center gap-2"
              >
                <RefreshCw size={16} /> Change Config
              </button>
            </div>
            
            <div className="mt-10 pt-6 border-t border-slate-800">
              <h4 className="text-sm font-bold text-slate-500 uppercase mb-4">Danger Zone</h4>
              <button 
                onClick={clearConfig}
                className="text-xs text-red-400 hover:text-red-300 transition-colors flex items-center gap-2"
              >
                <AlertTriangle size={14} /> Reset all AI settings to default
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
