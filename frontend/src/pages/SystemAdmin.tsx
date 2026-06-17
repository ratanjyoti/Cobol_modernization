
import React, { useState } from 'react';
import PromptStudio from './PromptStudio';
import Settings from './Settings';
import { Settings as SettingsIcon, MessageSquareCode } from 'lucide-react';

const SystemAdmin = () => {
  const [activeView, setActiveView] = useState<'prompts' | 'settings'>('prompts');

  return (
    <div className="space-y-6 h-full">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">System Administration</h1>
          <p className="text-slate-400">Configure AI constitutions and global system settings.</p>
        </div>

        <div className="flex p-1 bg-slate-900 rounded-xl border border-slate-800">
          <button 
            onClick={() => setActiveView('prompts')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${activeView === 'prompts' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <MessageSquareCode size={14} /> Prompt Studio
          </button>
          <button 
            onClick={() => setActiveView('settings')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all ${activeView === 'settings' ? 'bg-indigo-600 text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}
          >
            <SettingsIcon size={14} /> System Settings
          </button>
        </div>
      </div>

      <div className="h-[calc(100vh-200px)]">
        {activeView === 'prompts' ? <PromptStudio /> : <Settings />}
      </div>
    </div>
  );
};

export default SystemAdmin;
