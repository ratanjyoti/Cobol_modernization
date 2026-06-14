import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe, Cpu, CheckCircle2, ArrowRight, X } from 'lucide-react';
import toast from 'react-hot-toast';

interface ConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const ConfigModal = ({ isOpen, onClose }: ConfigModalProps) => {
  const [step, setStep] = useState(1);
  const [mode, setMode] = useState<'api' | 'local' | null>(null);
  const [config, setConfig] = useState({ key: '', url: 'http://localhost:11434', model: 'llama3' });

  const localModels = ['llama3', 'mistral', 'phi3', 'codellama'];
  const cloudModels = ['gpt-4o', 'gpt-4-turbo', 'claude-3-5-sonnet'];

  const handleSave = () => {
    if (mode === 'api' && !config.key) {
      toast.error("Please enter your API Key");
      return;
    }
    // Save to localStorage to simulate persistent config
    localStorage.setItem('ai_config', JSON.stringify({ mode, ...config }));
    toast.success("Configuration saved successfully!");
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          {/* Backdrop blur */}
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm" 
          />

          {/* Modal Card */}
          <motion.div 
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden"
          >
            {/* Close Button */}
            <button onClick={onClose} className="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors">
              <X size={20} />
            </button>

            <div className="p-8">
              {step === 1 ? (
                <div className="space-y-6">
                  <div className="text-center space-y-2">
                    <h2 className="text-2xl font-bold text-white">Welcome to Modernizer AI</h2>
                    <p className="text-slate-400 text-sm">Select your AI engine to begin the conversion process.</p>
                  </div>

                  <div className="grid grid-cols-1 gap-4">
                    <div 
                      onClick={() => { setMode('api'); setStep(2); }}
                      className={`group cursor-pointer p-6 rounded-2xl border-2 transition-all ${
                        mode === 'api' ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-800 bg-slate-800/50 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="p-3 bg-indigo-500/20 text-indigo-400 rounded-xl group-hover:scale-110 transition-transform">
                            <Globe size={24} />
                          </div>
                          <div>
                            <h3 className="font-bold text-white">Cloud API</h3>
                            <p className="text-xs text-slate-400">High performance (OpenAI, Azure, Anthropic)</p>
                          </div>
                        </div>
                        <ArrowRight size={20} className="text-slate-600 group-hover:text-white transition-colors" />
                      </div>
                    </div>

                    <div 
                      onClick={() => { setMode('local'); setStep(2); }}
                      className={`group cursor-pointer p-6 rounded-2xl border-2 transition-all ${
                        mode === 'local' ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-800 bg-slate-800/50 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="p-3 bg-emerald-500/20 text-emerald-400 rounded-xl group-hover:scale-110 transition-transform">
                            <Cpu size={24} />
                          </div>
                          <div>
                            <h3 className="font-bold text-white">Local LLM</h3>
                            <p className="text-xs text-slate-400">Private & Secure (Ollama, vLLM)</p>
                          </div>
                        </div>
                        <ArrowRight size={20} className="text-slate-600 group-hover:text-white transition-colors" />
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="text-center space-y-2">
                    <h2 className="text-2xl font-bold text-white">
                      {mode === 'api' ? 'Cloud Configuration' : 'Local Configuration'}
                    </h2>
                    <p className="text-slate-400 text-sm">Enter your connection details below.</p>
                  </div>

                  <div className="space-y-4">
                    {mode === 'api' ? (
                      <>
                        <div className="space-y-2">
                          <label className="text-xs font-bold text-slate-500 uppercase ml-1">API Key</label>
                          <input 
                            type="password" 
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                            placeholder="sk-..."
                            value={config.key}
                            onChange={(e) => setConfig({...config, key: e.target.value})}
                          />
                        </div>
                        <div className="space-y-2">
                          <label className="text-xs font-bold text-slate-500 uppercase ml-1">Model</label>
                          <select 
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white outline-none focus:ring-2 focus:ring-indigo-500 appearance-none"
                            value={config.model}
                            onChange={(e) => setConfig({...config, model: e.target.value})}
                          >
                            {cloudModels.map(m => <option key={m} value={m}>{m}</option>)}
                          </select>
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="space-y-2">
                          <label className="text-xs font-bold text-slate-500 uppercase ml-1">Server URL</label>
                          <input 
                            type="text" 
                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                            placeholder="http://localhost:11434"
                            value={config.url}
                            onChange={(e) => setConfig({...config, url: e.target.value})}
                          />
                        </div>
                        <div className="space-y-2">
                          <label className="text-xs font-bold text-slate-500 uppercase ml-1">Select Model</label>
                          <div className="grid grid-cols-2 gap-2">
                            {localModels.map(m => (
                              <button 
                                key={m}
                                onClick={() => setConfig({...config, model: m})}
                                className={`p-2 text-xs rounded-lg border transition-all ${
                                  config.model === m ? 'border-indigo-500 bg-indigo-500/20 text-white' : 'border-slate-700 text-slate-400 hover:bg-slate-800'
                                }`}
                              >
                                {m}
                              </button>
                            ))}
                          </div>
                        </div>
                      </>
                    )}
                  </div>

                  <div className="flex gap-3 pt-4">
                    <button onClick={() => setStep(1)} className="flex-1 py-3 rounded-xl text-slate-400 font-bold hover:text-white transition-colors">
                      Back
                    </button>
                    <button onClick={handleSave} className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white py-3 rounded-xl font-bold transition-all flex items-center justify-center gap-2">
                      <CheckCircle2 size={18} /> Complete Setup
                    </button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default ConfigModal;
