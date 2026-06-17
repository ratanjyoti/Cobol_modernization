import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Globe,
  Cpu,
  CheckCircle2,
  ArrowRight,
  X
} from 'lucide-react';
import toast from 'react-hot-toast';

interface ConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const ConfigModal = ({
  isOpen,
  onClose,
}: ConfigModalProps) => {
  const [step, setStep] = useState(1);

  const [mode, setMode] = useState<
    'api' | 'local' | null
  >(null);

  const [config, setConfig] = useState({
    key: '',
    url: 'http://localhost:11434',
    model: 'gpt-4o',
  });

  const [customModel, setCustomModel] =
    useState('');

  const localModels = [
    'llama3',
    'mistral',
    'phi3',
    'codellama',
  ];

  const cloudModels = [
    'gpt-4o',
    'gpt-4-turbo',
    'claude-3-5-sonnet',
  ];

  useEffect(() => {
    if (!isOpen) return;

    setStep(1);

    const savedConfig =
      localStorage.getItem('ai_config');

    if (savedConfig) {
      try {
        const parsed = JSON.parse(savedConfig);

        setMode(parsed.mode || null);

        setConfig({
          key: parsed.key || '',
          url:
            parsed.url ||
            'http://localhost:11434',
          model:
            parsed.model || 'gpt-4o',
        });

        const knownModels = [
          ...cloudModels,
          ...localModels,
        ];

        if (
          parsed.model &&
          !knownModels.includes(parsed.model)
        ) {
          setCustomModel(parsed.model);
        }
      } catch (error) {
        console.error(
          'Failed to parse AI config',
          error
        );
      }
    }
  }, [isOpen]);

  const handleSave = () => {
    if (!mode) {
      toast.error(
        'Please select a configuration mode'
      );
      return;
    }

    if (
      mode === 'api' &&
      !config.key.trim()
    ) {
      toast.error(
        'Please enter an API key'
      );
      return;
    }

    const finalModel =
      config.model === 'custom'
        ? customModel.trim()
        : config.model;

    if (!finalModel) {
      toast.error(
        'Please provide a model name'
      );
      return;
    }

    localStorage.setItem(
      'ai_config',
      JSON.stringify({
        mode,
        key: config.key,
        url: config.url,
        model: finalModel,
      })
    );

    toast.success(
      'Configuration saved successfully'
    );

    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
          />

          <motion.div
            initial={{
              scale: 0.95,
              opacity: 0,
              y: 20,
            }}
            animate={{
              scale: 1,
              opacity: 1,
              y: 0,
            }}
            exit={{
              scale: 0.95,
              opacity: 0,
              y: 20,
            }}
            className="relative w-full max-w-xl rounded-3xl border border-slate-700 bg-slate-900 shadow-2xl overflow-hidden"
          >
            <button
              onClick={onClose}
              className="absolute top-4 right-4 text-slate-500 hover:text-white"
            >
              <X size={20} />
            </button>

            <div className="p-8">
              {step === 1 ? (
                <div className="space-y-6">
                  <div className="text-center">
                    <h2 className="text-2xl font-bold text-white">
                      AI Configuration
                    </h2>

                    <p className="text-slate-400 mt-2">
                      Choose your preferred
                      AI engine
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div
                      onClick={() => {
                        setMode('api');
                        setStep(2);
                      }}
                      className="cursor-pointer rounded-2xl border border-slate-700 bg-slate-800 p-6 hover:border-indigo-500 transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex gap-4 items-center">
                          <Globe className="text-indigo-400" />
                          <div>
                            <h3 className="text-white font-semibold">
                              Cloud API
                            </h3>
                            <p className="text-xs text-slate-400">
                              OpenAI, Azure,
                              Anthropic
                            </p>
                          </div>
                        </div>

                        <ArrowRight />
                      </div>
                    </div>

                    <div
                      onClick={() => {
                        setMode('local');
                        setStep(2);
                      }}
                      className="cursor-pointer rounded-2xl border border-slate-700 bg-slate-800 p-6 hover:border-emerald-500 transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex gap-4 items-center">
                          <Cpu className="text-emerald-400" />
                          <div>
                            <h3 className="text-white font-semibold">
                              Local LLM
                            </h3>
                            <p className="text-xs text-slate-400">
                              Ollama, vLLM
                            </p>
                          </div>
                        </div>

                        <ArrowRight />
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-5">
                  <h2 className="text-2xl font-bold text-white text-center">
                    {mode === 'api'
                      ? 'Cloud Configuration'
                      : 'Local Configuration'}
                  </h2>

                  {mode === 'api' && (
                    <>
                      <input
                        type="password"
                        placeholder="API Key"
                        value={config.key}
                        onChange={(e) =>
                          setConfig({
                            ...config,
                            key:
                              e.target.value,
                          })
                        }
                        className="w-full rounded-xl bg-slate-800 border border-slate-700 px-4 py-3 text-white"
                      />

                      <select
                        value={config.model}
                        onChange={(e) =>
                          setConfig({
                            ...config,
                            model:
                              e.target.value,
                          })
                        }
                        className="w-full rounded-xl bg-slate-800 border border-slate-700 px-4 py-3 text-white"
                      >
                        {cloudModels.map(
                          (model) => (
                            <option
                              key={model}
                            >
                              {model}
                            </option>
                          )
                        )}

                        <option value="custom">
                          Custom Model
                        </option>
                      </select>
                    </>
                  )}

                  {mode === 'local' && (
                    <>
                      <input
                        type="text"
                        value={config.url}
                        placeholder="Server URL"
                        onChange={(e) =>
                          setConfig({
                            ...config,
                            url:
                              e.target.value,
                          })
                        }
                        className="w-full rounded-xl bg-slate-800 border border-slate-700 px-4 py-3 text-white"
                      />

                      <select
                        value={config.model}
                        onChange={(e) =>
                          setConfig({
                            ...config,
                            model:
                              e.target.value,
                          })
                        }
                        className="w-full rounded-xl bg-slate-800 border border-slate-700 px-4 py-3 text-white"
                      >
                        {localModels.map(
                          (model) => (
                            <option
                              key={model}
                            >
                              {model}
                            </option>
                          )
                        )}

                        <option value="custom">
                          Custom Model
                        </option>
                      </select>
                    </>
                  )}

                  {config.model ===
                    'custom' && (
                    <input
                      type="text"
                      placeholder="Enter model name"
                      value={customModel}
                      onChange={(e) =>
                        setCustomModel(
                          e.target.value
                        )
                      }
                      className="w-full rounded-xl bg-slate-950 border border-indigo-500 px-4 py-3 text-white"
                    />
                  )}

                  <div className="flex gap-3 pt-3">
                    <button
                      onClick={() =>
                        setStep(1)
                      }
                      className="flex-1 rounded-xl py-3 text-slate-300 hover:text-white"
                    >
                      Back
                    </button>

                    <button
                      onClick={handleSave}
                      className="flex-1 bg-indigo-600 hover:bg-indigo-500 rounded-xl py-3 text-white font-semibold flex justify-center items-center gap-2"
                    >
                      <CheckCircle2
                        size={18}
                      />
                      Save
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