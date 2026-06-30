import React, { useState, useEffect } from 'react';
import { Globe, Cpu, CheckCircle2, ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';

type ConfigMode = 'api' | 'local' | null;

interface AIConfigForm {
  key: string;
  url: string;
  model: string;
}

const LOCAL_MODELS = ['llama3', 'mistral', 'phi3', 'codellama'];
const CLOUD_MODELS = ['gpt-4o', 'gpt-4-turbo', 'claude-3-5-sonnet'];

const DEFAULT_CONFIG: AIConfigForm = {
  key: '',
  url: 'http://localhost:11434',
  model: 'gpt-4o',
};
interface ConfigPanelProps {
  runId: string | null;
}
const ConfigPanel = ({ runId }: ConfigPanelProps) => {
  // Now you can use runId inside this component to make API calls
  console.log("Current Project ID:", runId);  const [step, setStep] = useState(1);
  const [mode, setMode] = useState<ConfigMode>(null);
  const [config, setConfig] = useState<AIConfigForm>(DEFAULT_CONFIG);
  const [customModel, setCustomModel] = useState('');

  useEffect(() => {
    const savedConfig = localStorage.getItem('ai_config');
    if (savedConfig) {
      try {
        const parsed = JSON.parse(savedConfig);
        setMode(parsed.mode);
        setConfig({
          key: parsed.key || '',
          url: parsed.url || DEFAULT_CONFIG.url,
          model: parsed.model || DEFAULT_CONFIG.model,
        });
      } catch (e) { console.error("Config load error", e); }
    }
  }, []);

  const handleSave = () => {
    if (!mode) {
      toast.error('Please select a configuration mode');
      return;
    }
    if (mode === 'api' && !config.key.trim()) {
      toast.error('Please enter an API key');
      return;
    }

    const finalModel = config.model === 'custom' ? customModel.trim() : config.model;
    if (!finalModel) {
      toast.error('Please provide a model name');
      return;
    }

    localStorage.setItem('ai_config', JSON.stringify({
      mode,
      key: config.key,
      url: config.url,
      model: finalModel,
    }));

    toast.success('Configuration saved successfully');
  };

  return (
    <div className="w-full h-full">
      {step === 1 ? (
        <div className="space-y-4">
          <div className="text-center mb-4">
            <h3 className="text-lg font-bold text-white">AI Configuration</h3>
            <p className="text-xs text-slate-400">Choose your preferred AI engine</p>
          </div>
          <div className="space-y-3">
            <div
              onClick={() => { setMode('api'); setStep(2); }}
              className="cursor-pointer rounded-2xl border border-slate-700 bg-slate-800 p-4 hover:border-indigo-500 transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex gap-3 items-center">
                  <Globe className="text-indigo-400" size={20} />
                  <div>
                    <p className="text-sm font-semibold text-white">Cloud API</p>
                    <p className="text-[10px] text-slate-400">OpenAI, Azure, Anthropic</p>
                  </div>
                </div>
                <ArrowRight size={16} className="text-slate-500" />
              </div>
            </div>
            <div
              onClick={() => { setMode('local'); setStep(2); }}
              className="cursor-pointer rounded-2xl border border-slate-700 bg-slate-800 p-4 hover:border-emerald-500 transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="flex gap-3 items-center">
                  <Cpu className="text-emerald-400" size={20} />
                  <div>
                    <p className="text-sm font-semibold text-white">Local LLM</p>
                    <p className="text-[10px] text-slate-400">Ollama, vLLM</p>
                  </div>
                </div>
                <ArrowRight size={16} className="text-slate-500" />
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-md font-bold text-white">
              {mode === 'api' ? 'Cloud Config' : 'Local Config'}
            </h3>
            <button onClick={() => setStep(1)} className="text-[10px] text-indigo-400 hover:underline">Back</button>
          </div>

          {mode === 'api' && (
            <div className="space-y-3">
              <input
                type="password"
                placeholder="API Key"
                value={config.key}
                onChange={(e) => setConfig({ ...config, key: e.target.value })}
                className="w-full rounded-xl bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-white outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <select
                value={config.model}
                onChange={(e) => setConfig({ ...config, model: e.target.value })}
                className="w-full rounded-xl bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-white outline-none"
              >
                {CLOUD_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                <option value="custom">Custom Model</option>
              </select>
            </div>
          )}

          {mode === 'local' && (
            <div className="space-y-3">
              <input
                type="text"
                value={config.url}
                placeholder="Server URL"
                onChange={(e) => setConfig({ ...config, url: e.target.value })}
                className="w-full rounded-xl bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-white outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <select
                value={config.model}
                onChange={(e) => setConfig({ ...config, model: e.target.value })}
                className="w-full rounded-xl bg-slate-800 border border-slate-700 px-3 py-2 text-sm text-white outline-none"
              >
                {LOCAL_MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                <option value="custom">Custom Model</option>
              </select>
            </div>
          )}

          {config.model === 'custom' && (
            <input
              type="text"
              placeholder="Enter model name"
              value={customModel}
              onChange={(e) => setCustomModel(e.target.value)}
              className="w-full rounded-xl bg-slate-950 border border-indigo-500 px-3 py-2 text-sm text-white"
            />
          )}

          <button
            onClick={handleSave}
            className="w-full bg-indigo-600 hover:bg-indigo-500 rounded-xl py-2 text-white text-sm font-semibold flex items-center justify-center gap-2 transition-all"
          >
            <CheckCircle2 size={16} /> Save Config
          </button>
        </div>
      )}
    </div>
  );
};

export default ConfigPanel;
