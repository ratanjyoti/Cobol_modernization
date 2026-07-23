import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe, Cpu, CheckCircle2, ArrowRight, Lock, Server, Activity } from 'lucide-react';
import toast from 'react-hot-toast';
import { ProjectAPI, LLMHealthAPI, type LocalLLMHealthResponse, getApiErrorDetail } from '../services/api';

const LOCAL_MODELS = ['llama3.2:3b', 'llama-3.2-3b-instruct', 'llama3', 'mistral:7b', 'phi3', 'codellama:7b', 'deepseek-coder:6.7b', 'qwen2.5-coder:7b'];
const OPENROUTER_MODELS = [
  'openai/gpt-oss-20b:free',
  'nvidia/nemotron-3-nano-30b-a3b:free',
  'nvidia/nemotron-3-super-120b-a12b:free',
  'cohere/north-mini-code:free',
];

type AiMode = 'openrouter' | 'local' | 'custom';
type LocalProvider = 'ollama' | 'openai-compatible';

interface ConfigPanelProps {
  runId: string | null;
  onSave?: (config: any) => void;
}

const defaultsForMode = (mode: AiMode) => {
  if (mode === 'local') {
    return { key: '', url: 'http://localhost:11434', model: 'llama3.2:3b' };
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
  const [localProvider, setLocalProvider] = useState<LocalProvider>('ollama');
  const [checkingLocalLLM, setCheckingLocalLLM] = useState(false);
  const [localLLMStatus, setLocalLLMStatus] = useState<LocalLLMHealthResponse | null>(null);
  const backendCheckControllerRef = useRef<AbortController | null>(null);
  const browserCheckControllerRef = useRef<AbortController | null>(null);

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
      setLocalProvider(saved.local_provider === 'openai-compatible' || saved.local_provider === 'lmstudio' ? 'openai-compatible' : 'ollama');
      setCustomModel([...OPENROUTER_MODELS, ...LOCAL_MODELS].includes(savedModel) ? '' : savedModel);
      setLocalLLMStatus(null);
      setStep(2);
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
    if (mode !== nextMode) {
      setConfig(defaultsForMode(nextMode));
      setCustomModel('');
      setSavedKeyPreview(null);
    }
    setMode(nextMode);
    setLocalLLMStatus(null);
    setStep(2);
  };

  const selectedModel = () => (config.model === 'custom' ? customModel.trim() : config.model);
  const normalizeLocalBaseUrl = (url: string, provider: LocalProvider) => {
    const trimmed = (url || '').trim().replace(/\/+$/, '');
    if (provider === 'openai-compatible') {
      const base = trimmed || 'http://localhost:1234';
      return base.endsWith('/v1') ? base : `${base}/v1`;
    }
    return trimmed || 'http://localhost:11434';
  };

  const defaultEndpointForLocalProvider = (provider: LocalProvider) => {
    return provider === 'openai-compatible' ? 'http://localhost:1234/v1' : 'http://localhost:11434';
  };
  const checkBrowserOpenAICompatible = async (model: string, endpoint: string, externalSignal?: AbortSignal): Promise<LocalLLMHealthResponse> => {
    const started = performance.now();
    const base = endpoint.replace(/\/+$/, '');
    const apiBase = base.endsWith('/v1') ? base : `${base}/v1`;

    const requestWithTimeout = async (url: string, init: RequestInit, timeoutMs: number) => {
      const controller = new AbortController();
      browserCheckControllerRef.current = controller;
      const abortFromExternalSignal = () => controller.abort();
      const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
      externalSignal?.addEventListener('abort', abortFromExternalSignal, { once: true });
      try {
        return await fetch(url, { ...init, signal: controller.signal });
      } finally {
        window.clearTimeout(timeoutId);
        externalSignal?.removeEventListener('abort', abortFromExternalSignal);
        if (browserCheckControllerRef.current === controller) {
          browserCheckControllerRef.current = null;
        }
      }
    };

    try {
      const modelsResponse = await requestWithTimeout(`${apiBase}/models`, {}, 8000);
      if (!modelsResponse.ok) {
        return {
          ok: false,
          provider: 'browser-openai-compatible',
          model,
          status: 'SERVER_ERROR',
          message: 'Browser reached the local server, but the model list failed.',
          model_installed: false,
          server_reachable: true,
          error_detail: `GET ${apiBase}/models returned HTTP ${modelsResponse.status}: ${(await modelsResponse.text()).slice(0, 1000)}`,
        };
      }

      const modelsData = await modelsResponse.json();
      const availableModels = (modelsData.data || [])
        .map((item: any) => item.id || item.name)
        .filter(Boolean);

      if (!availableModels.includes(model)) {
        return {
          ok: false,
          provider: 'browser-openai-compatible',
          model,
          status: 'MODEL_NOT_FOUND',
          message: `Model '${model}' is not available from the local server.`,
          model_installed: false,
          server_reachable: true,
          error_detail: `Available models: ${availableModels.length ? availableModels.join(', ') : 'none'}`,
        };
      }

      const chatResponse = await requestWithTimeout(`${apiBase}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: 'Reply with exactly: OK' }],
          temperature: 0,
          max_tokens: 8,
          stream: false,
        }),
      }, 45000);
      const latencyMs = Math.round(performance.now() - started);

      if (!chatResponse.ok) {
        return {
          ok: false,
          provider: 'browser-openai-compatible',
          model,
          status: 'GENERATION_FAILED',
          message: 'The model is available but failed to generate output.',
          model_installed: true,
          server_reachable: true,
          latency_ms: latencyMs,
          error_detail: await chatResponse.text(),
        };
      }

      const chatData = await chatResponse.json();
      const output = (chatData.choices?.[0]?.message?.content || chatData.choices?.[0]?.text || '').trim();

      if (!output) {
        return {
          ok: false,
          provider: 'browser-openai-compatible',
          model,
          status: 'EMPTY_OUTPUT',
          message: 'The model responded, but the output was empty.',
          model_installed: true,
          server_reachable: true,
          latency_ms: latencyMs,
          sample_output: '',
          error_detail: 'The local server returned no chat completion text.',
        };
      }

      return {
        ok: true,
        provider: 'browser-openai-compatible',
        model,
        status: 'READY',
        message: `Local model '${model}' is available and generated output successfully.`,
        model_installed: true,
        server_reachable: true,
        latency_ms: latencyMs,
        sample_output: output.slice(0, 500),
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Browser request failed';
      return {
        ok: false,
        provider: 'browser-openai-compatible',
        model,
        status: message.toLowerCase().includes('abort') ? 'TIMEOUT' : 'SERVER_NOT_RUNNING',
        message: 'Browser could not reach the local OpenAI-compatible server.',
        model_installed: false,
        server_reachable: false,
        error_detail: `${message}. If this is LM Studio, enable the local server and allow CORS/origins for this frontend.`,
      };
    }
  };

  const stopLocalLLMCheck = () => {
    backendCheckControllerRef.current?.abort();
    browserCheckControllerRef.current?.abort();
    backendCheckControllerRef.current = null;
    browserCheckControllerRef.current = null;
    setCheckingLocalLLM(false);
    setLocalLLMStatus((current) => current || {
      ok: false,
      provider: localProvider,
      model: selectedModel(),
      status: 'CANCELLED',
      message: 'Local LLM check stopped by user.',
      model_installed: false,
      server_reachable: false,
    });
  };
  const checkLocalLLM = async () => {
    const model = selectedModel();
    if (!model) {
      toast.error('Please select or enter a local model name');
      return;
    }

    const controller = new AbortController();
    backendCheckControllerRef.current = controller;
    setCheckingLocalLLM(true);
    setLocalLLMStatus(null);

    try {
      let result = await LLMHealthAPI.checkLocal({
        provider: localProvider,
        model,
        base_url: normalizeLocalBaseUrl(config.url || '', localProvider),
      }, controller.signal);

      if (!result.ok && ['SERVER_NOT_RUNNING', 'TIMEOUT', 'UNKNOWN_ERROR'].includes(result.status)) {
        const browserResult = await checkBrowserOpenAICompatible(model, normalizeLocalBaseUrl(config.url || '', localProvider), controller.signal);
        if (browserResult.ok || browserResult.server_reachable) {
          result = browserResult;
        } else {
          result = {
            ...result,
            error_detail: `${result.error_detail || result.message}\n\nBrowser fallback: ${browserResult.error_detail || browserResult.message}`,
          };
        }
      }

      if (controller.signal.aborted) return;

      setLocalLLMStatus(result);
      if (result.ok) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    } catch (error) {
      if (controller.signal.aborted) {
        const cancelledStatus: LocalLLMHealthResponse = {
          ok: false,
          provider: localProvider,
          model,
          status: 'CANCELLED',
          message: 'Local LLM check stopped by user.',
          model_installed: false,
          server_reachable: false,
        };
        setLocalLLMStatus(cancelledStatus);
        toast.error(cancelledStatus.message);
        return;
      }

      const message = getApiErrorDetail(error, 'Failed to check local LLM');
      setLocalLLMStatus({
        ok: false,
        provider: localProvider,
        model,
        status: 'REQUEST_FAILED',
        message,
        model_installed: false,
        server_reachable: false,
        error_detail: message,
      });
      toast.error(message);
    } finally {
      if (backendCheckControllerRef.current === controller) {
        backendCheckControllerRef.current = null;
      }
      browserCheckControllerRef.current = null;
      setCheckingLocalLLM(false);
    }
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

    const finalModel = selectedModel();
    if (!finalModel) {
      toast.error('Please choose or enter a model');
      return;
    }

    const finalConfig: any = {
      mode,
      provider: mode,
      url: mode === 'local' ? normalizeLocalBaseUrl(config.url, localProvider) : config.url.trim() || defaultsForMode(mode).url,
      model: finalModel,
      ...(mode === 'local' ? { local_provider: localProvider } : {}),
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
      toast.error(getApiErrorDetail(e, 'Failed to sync configuration with server'));
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
                    <p className="text-[10px] text-slate-400">Ollama, LM Studio, or any OpenAI-compatible local server</p>
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

              {mode === 'local' && (
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-500 uppercase">Local Provider</label>
                  <select
                    value={localProvider}
                    onChange={(e) => {
                      const nextProvider = e.target.value as LocalProvider;
                      setLocalProvider(nextProvider);
                      setConfig({
                        ...config,
                        url: defaultEndpointForLocalProvider(nextProvider),
                        model: nextProvider === 'openai-compatible' ? 'custom' : 'llama3.2:3b',
                      });
                      setCustomModel(nextProvider === 'openai-compatible' ? customModel || 'llama-3.2-3b-instruct' : '');
                      setLocalLLMStatus(null);
                    }}
                    className="w-full rounded-xl bg-slate-950 border border-slate-800 px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 appearance-none"
                  >
                    <option value="ollama">Ollama</option>
                    <option value="openai-compatible">LM Studio / OpenAI-Compatible</option>
                  </select>
                </div>
              )}
              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-500 uppercase">Endpoint URL</label>
                <div className="relative">
                  <Server className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" size={14} />
                  <input
                    type="text"
                    value={config.url}
                    onChange={(e) => {
                      setConfig({ ...config, url: e.target.value });
                      setLocalLLMStatus(null);
                    }}
                    className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder={mode === 'local' ? defaultEndpointForLocalProvider(localProvider) : 'https://openrouter.ai/api/v1'}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold text-slate-500 uppercase">Model</label>
                <select
                  value={config.model}
                  onChange={(e) => {
                    setConfig({ ...config, model: e.target.value });
                    setLocalLLMStatus(null);
                  }}
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
                    placeholder={mode === 'local' ? 'e.g. llama3.2:3b or qwen2.5-coder:7b' : 'e.g. openrouter/provider-model:free'}
                    value={customModel}
                    onChange={(e) => {
                      setCustomModel(e.target.value);
                      setLocalLLMStatus(null);
                    }}
                    className="w-full rounded-xl bg-slate-950 border border-indigo-500 px-4 py-3 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </motion.div>
              )}

              {mode === 'local' && (
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <h4 className="text-sm font-black text-white">Local LLM Health Check</h4>
                      <p className="mt-1 text-xs leading-5 text-slate-400">
                        Checks if the local server is reachable, the selected model is available, and the model can generate output.
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={checkingLocalLLM ? stopLocalLLMCheck : checkLocalLLM}
                      className={`shrink-0 rounded-lg border px-3 py-2 text-xs font-black text-white ${checkingLocalLLM ? 'border-red-500/50 bg-red-600 hover:bg-red-500' : 'border-slate-700 bg-slate-900 hover:bg-slate-800'}`}
                    >
                      {checkingLocalLLM ? 'Stop Check' : 'Test Local LLM'}
                    </button>
                  </div>

                  <p className="mt-3 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3 text-xs leading-5 text-amber-100">
                    Local LLM mode requires the backend to reach your local server. Use Ollama, LM Studio, or any OpenAI-compatible endpoint exposed from this laptop.
                  </p>

                  {localLLMStatus && (
                    <div
                      className={`mt-4 rounded-xl border p-3 ${
                        localLLMStatus.ok
                          ? 'border-emerald-500/30 bg-emerald-500/10'
                          : 'border-red-500/30 bg-red-500/10'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p
                          className={`flex items-center gap-2 text-xs font-black ${
                            localLLMStatus.ok ? 'text-emerald-300' : 'text-red-300'
                          }`}
                        >
                          <Activity size={14} /> {localLLMStatus.status}
                        </p>

                        {localLLMStatus.latency_ms != null && (
                          <p className="text-xs text-slate-400">{localLLMStatus.latency_ms} ms</p>
                        )}
                      </div>

                      <p className="mt-2 text-xs leading-5 text-slate-300">{localLLMStatus.message}</p>

                      {localLLMStatus.status === 'MODEL_NOT_FOUND' && (
                        <p className="mt-2 rounded-lg bg-slate-950 p-3 text-xs text-slate-300">
                          Load or install this model in your local LLM app: <span className="font-mono text-emerald-300">{localLLMStatus.model}</span>
                        </p>
                      )}

                      {localLLMStatus.status === 'SERVER_NOT_RUNNING' && (
                        <p className="mt-2 rounded-lg bg-slate-950 p-3 text-xs text-slate-300">
                          Start your local server, then verify the endpoint URL. For LM Studio, enable the local server and use its reachable URL.
                        </p>
                      )}

                      {localLLMStatus.sample_output && (
                        <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950 p-3">
                          <p className="text-[10px] font-black uppercase tracking-wider text-slate-500">Sample Output</p>
                          <p className="mt-1 text-xs text-slate-300">{localLLMStatus.sample_output}</p>
                        </div>
                      )}

                      {localLLMStatus.error_detail && (
                        <details className="mt-3">
                          <summary className="cursor-pointer text-xs font-bold text-slate-400">Error details</summary>
                          <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-slate-950 p-3 text-[11px] text-red-200 whitespace-pre-wrap">
                            {localLLMStatus.error_detail}
                          </pre>
                        </details>
                      )}
                    </div>
                  )}
                </div>
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
















