import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe, Cpu, CheckCircle2, ArrowRight, Lock, Server } from 'lucide-react';
import toast from 'react-hot-toast';
import { ProjectAPI } from '../services/api';

const LOCAL_MODELS = ['llama3', 'mistral', 'phi3', 'codellama'];
const OPENROUTER_MODELS = [
  'openai/gpt-oss-20b:free',
  'nvidia/nemotron-3-nano-30b-a3b:free',
  'nvidia/nemotron-3-super-120b-a12b:free',
  'cohere/north-mini-code:free',
];

type AiMode = 'openrouter' | 'local' | 'custom';

interface ConfigPanelProps {
  runId: string | null;
  onSave?: (config: any) => void;
}

const defaultsForMode = (mode: AiMode) => {
  if (mode === 'local') {
    return { key: '', url: 'http://localhost:11434', model: 'llama3' };
  }
  return { key: '', url: 'https://openrouter.ai/api/v1', model: 'openai/gpt-oss-20b:free' };
};

const normalizeMode = (value: unknown): AiMode => {
  return value === 'local' || value === 'custom' || value === 'openrouter' ? value : 'openrouter';
};

const storageKeyForRun = (runId: string | null) => runId ? `ai_config_${runId}` : 'ai_config';

const ConfigPanel = ({ runId, onSave }: ConfigPanelProps) => {
  const [step, setStep] = useState(1);
  const [mode, setMode] = useState<AiMode | null>(null);
  const [config, setConfig] = useState(defaultsForMode('openrouter'));
  const [customModel, setCustomModel] = useState('');
  const [savedKeyPreview, setSavedKeyPreview] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const applySavedConfig = (saved: any) => {
      const savedMode = normalizeMode(saved.mode || saved.provider);
      const savedModel = saved.model || defaultsForMode(savedMode).model;
      setMode(savedMode);
      setConfig({
        ...defaultsForMode(savedMode),
        key: '',
        url: saved.url || defaultsForMode(savedMode).url,
        model: [...OPENROUTER_MODELS, ...LOCAL_MODELS].includes(savedModel) ? savedModel : 'custom',
      });
      setSavedKeyPreview(saved.has_api_key ? saved.key_preview || 'saved' : null);
      setCustomModel([...OPENROUTER_MODELS, ...LOCAL_MODELS].includes(savedModel) ? '' : savedModel);
    };

    const loadSavedConfig = async () => {
      const runScopedKey = storageKeyForRun(runId);
      if (runId) {
        try {
          const serverConfig = await ProjectAPI.getConfig(runId);
          if (!cancelled && (serverConfig.mode || serverConfig.provider || serverConfig.model)) {
            applySavedConfig(serverConfig);
            const safeServerConfig = { ...serverConfig, key: '' };
            localStorage.setItem(runScopedKey, JSON.stringify(safeServerConfig));
            localStorage.setItem('ai_config', JSON.stringify(safeServerConfig));
            return;
          }
        } catch (e) {
          console.error('Server config load error', e);
        }
      }

      const runScopedConfig = localStorage.getItem(runScopedKey);
      if (runScopedConfig) {
        try {
          applySavedConfig(JSON.parse(runScopedConfig));
          return;
        } catch (e) {
          console.error('Run config load error', e);
        }
      }

      const globalConfig = localStorage.getItem('ai_config');
      if (!globalConfig) return;
      try {
        applySavedConfig(JSON.parse(globalConfig));
      } catch (e) {
        console.error('Config load error', e);
      }
    };

    void loadSavedConfig();

    return () => {
      cancelled = true;
    };
  }, [runId]);

  const chooseMode = (nextMode: AiMode) => {
    setMode(nextMode);
    setConfig(defaultsForMode(nextMode));
    setCustomModel('');
    setSavedKeyPreview(null);
    setStep(2);
  };

  const handleSave = async () => {
    if (!mode) {
      toast.error('Please select a configuration mode');
      return;
    }
    if ((mode === 'openrouter' || mode === 'custom') && !config.key.trim() && !savedKeyPreview) {
      toast.error(mode === 'openrouter' ? 'Enter your OpenRouter API key' : 'Custom API key is required');
      return;
    }

    const finalModel = config.model === 'custom' ? customModel.trim() : config.model;
    if (!finalModel) {
      toast.error('Please choose or enter a model');
      return;
    }

    const finalConfig: any = {
      mode,
      provider: mode,
      url: config.url.trim() || defaultsForMode(mode).url,
      model: finalModel,
    };
    if (config.key.trim()) {
      finalConfig.key = config.key.trim();
    }

    try {
      if (runId) {
        await ProjectAPI.updateConfig(runId, finalConfig);
      }
      const safeConfig = {
        ...finalConfig,
        key: '',
        has_api_key: Boolean(config.key.trim() || savedKeyPreview),
        key_preview: config.key.trim() ? `${config.key.trim().slice(0, 5)}****${config.key.trim().slice(-4)}` : savedKeyPreview,
      };
      localStorage.setItem(storageKeyForRun(runId), JSON.stringify(safeConfig));
      localStorage.setItem('ai_config', JSON.stringify(safeConfig));
      setSavedKeyPreview(safeConfig.key_preview);
      setConfig({ ...config, key: '' });
      window.dispatchEvent(new CustomEvent('ai-config-updated', { detail: safeConfig }));
      onSave?.(finalConfig);
      toast.success('AI configuration saved');
      setStep(1);
    } catch (e) {
      toast.error('Failed to sync configuration with server');
    }
  };

  const modelOptions = mode === 'local' ? LOCAL_MODELS : OPENROUTER_MODELS;

  return (
    <div className="w-full h-full">
      <AnimatePresence mode="wait">
        {step === 1 ? (
          <motion.div
            key="step1"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-6"
          >
            <div className="text-center mb-6">
              <h3 className="text-xl font-bold text-white">AI Engine Configuration</h3>
              <p className="text-xs text-slate-400">Add your free API key and choose the model used by extraction</p>
            </div>

            <div className="grid grid-cols-1 gap-4">
              <div
                onClick={() => chooseMode('openrouter')}
                className={`cursor-pointer rounded-2xl border p-4 transition-all flex items-center justify-between ${mode === 'openrouter' ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-700 bg-slate-800 hover:border-slate-600'}`}
              >
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-xl bg-indigo-500/20 text-indigo-400"><Globe size={20} /></div>
                  <div>
                    <p className="text-sm font-semibold text-white">OpenRouter API</p>
                    <p className="text-[10px] text-slate-400">Use your OpenRouter free key for business-rule extraction</p>
                  </div>
                </div>
                <ArrowRight size={16} className="text-slate-500" />
              </div>

              <div
                onClick={() => chooseMode('local')}
                className={`cursor-pointer rounded-2xl border p-4 transition-all flex items-center justify-between ${mode === 'local' ? 'border-emerald-500 bg-emerald-500/10' : 'border-slate-700 bg-slate-800 hover:border-slate-600'}`}
              >
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-xl bg-emerald-500/20 text-emerald-400"><Cpu size={20} /></div>
                  <div>
                    <p className="text-sm font-semibold text-white">Local LLM</p>
                    <p className="text-[10px] text-slate-400">Ollama, LM Studio, or a local compatible server</p>
                  </div>
                </div>
                <ArrowRight size={16} className="text-slate-500" />
              </div>

              <div
                onClick={() => chooseMode('custom')}
                className={`cursor-pointer rounded-2xl border p-4 transition-all flex items-center justify-between ${mode === 'custom' ? 'border-purple-500 bg-purple-500/10' : 'border-slate-700 bg-slate-800 hover:border-slate-600'}`}
              >
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-xl bg-purple-500/20 text-purple-400"><Lock size={20} /></div>
                  <div>
                    <p className="text-sm font-semibold text-white">Custom Compatible API</p>
                    <p className="text-[10px] text-slate-400">Use any OpenAI-compatible endpoint and key</p>
                  </div>
                </div>
                <ArrowRight size={16} className="text-slate-500" />
              </div>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key="step2"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="space-y-6"
          >
            <div className="flex justify-between items-center mb-2">
              <h3 className="text-lg font-bold text-white">
                {mode === 'openrouter' ? 'OpenRouter Config' : mode === 'local' ? 'Local Server Config' : 'Custom API Config'}
              </h3>
              <button onClick={() => setStep(1)} className="text-xs text-indigo-400 hover:underline">Back to Modes</button>
            </div>

            <div className="space-y-4">
              {(mode === 'openrouter' || mode === 'custom') && (
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-500 uppercase">API Key</label>
                  <input
                    type="password"
                    placeholder={savedKeyPreview ? `Saved key: ${savedKeyPreview}` : mode === 'openrouter' ? 'Paste your OpenRouter API key' : 'Enter your API key'}
                    value={config.key}
                    onChange={(e) => setConfig({ ...config, key: e.target.value })}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 transition-all"
                  />
                </div>
              )}

              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-500 uppercase">Endpoint URL</label>
                <div className="relative">
                  <Server className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" size={14} />
                  <input
                    type="text"
                    value={config.url}
                    onChange={(e) => setConfig({ ...config, url: e.target.value })}
                    className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder={mode === 'local' ? 'http://localhost:11434' : 'https://openrouter.ai/api/v1'}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-500 uppercase">Model</label>
                <select
                  value={config.model}
                  onChange={(e) => setConfig({ ...config, model: e.target.value })}
                  className="w-full rounded-xl bg-slate-950 border border-slate-800 px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 appearance-none"
                >
                  {modelOptions.map((modelName) => <option key={modelName} value={modelName}>{modelName}</option>)}
                  <option value="custom">Custom Model Name...</option>
                </select>
              </div>

              {config.model === 'custom' && (
                <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="space-y-2">
                  <input
                    type="text"
                    placeholder={mode === 'local' ? 'e.g. codellama-7b-instruct' : 'e.g. openrouter/provider-model:free'}
                    value={customModel}
                    onChange={(e) => setCustomModel(e.target.value)}
                    className="w-full rounded-xl bg-slate-950 border border-indigo-500 px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </motion.div>
              )}

              <button
                onClick={handleSave}
                className="w-full bg-indigo-600 hover:bg-indigo-500 rounded-xl py-3 text-white text-sm font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-indigo-500/20"
              >
                <CheckCircle2 size={18} /> Save & Sync Configuration
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ConfigPanel;
