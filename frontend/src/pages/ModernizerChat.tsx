import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, X, MessageSquare, Database, Cpu, LayoutTemplate, Sparkles, Loader2, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';

const EXAMPLE_QUERIES = {
  cobolAnalysis: [
    "Describe the top 3 critical copybooks and what they do",
    "Suggest a carveout strategy and where i should start",
    "Give me an overview of what the COBOL code is responsible for",
    "Which COBOL files have the highest impact?",
  ],
  migrationPlanning: [
    "What's the recommended migration order for these programs?",
    "Identify the main entry point programs",
    "Which copybooks are shared across multiple domains?",
  ]
};

interface ProcessingStepProps {
  active: boolean;
  label: string;
  sub: string;
  icon: React.ReactNode;
}

const ProcessingStep = ({ active, label, sub, icon }: ProcessingStepProps) => (
  <div className={`flex flex-col items-center gap-3 transition-all duration-500 ${active ? 'opacity-100 scale-110' : 'opacity-30'}`}>
    <div className={`p-4 rounded-full border-2 transition-all duration-500 ${active ? 'border-indigo-500 bg-indigo-500/20 text-indigo-400 shadow-lg shadow-indigo-500/30 animate-pulse' : 'border-slate-800 bg-slate-900 text-slate-600'}`}>
      {icon}
    </div>
    <div className="text-center">
      <p className={`text-xs font-bold ${active ? 'text-white' : 'text-slate-500'}`}>{label}</p>
      <p className="text-[10px] text-slate-600">{sub}</p>
    </div>
  </div>
);

const ModernizerChat = () => {
  const [prompt, setPrompt] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [response, setResponse] = useState('');
  const [processingStep, setProcessingStep] = useState(0);

  const handleSend = async (text: string = prompt) => {
    if (!text.trim()) return;
    setPrompt('');
    setIsProcessing(true);
    setResponse('');
    
    setProcessingStep(1); await new Promise(res => setTimeout(res, 1200));
    setProcessingStep(2); await new Promise(res => setTimeout(res, 1500));
    setProcessingStep(3); await new Promise(res => setTimeout(res, 1000));

    setResponse(`Based on the analyzed COBOL source, the ${text.includes('copybook') ? 'copybooks' : 'system'} shows a high degree of coupling. I recommend starting the migration with the 'Account-Service' as it has the lowest complexity score (4.2).`);
    setProcessingStep(0);
    setIsProcessing(false);
    toast.success("AI Analysis Complete");
  };

  return (
    <div className="h-full flex gap-6">
      {/* LEFT SIDEBAR: Example Queries */}
      <div className="w-80 flex flex-col gap-6">
        <div className="glass-card p-6 rounded-2xl space-y-6">
          <div className="flex items-center gap-2 text-white font-bold mb-4">
            <Sparkles size={18} className="text-indigo-400" />
            <h3>Example Queries</h3>
          </div>
          <div className="space-y-6">
            <div className="space-y-3">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">COBOL Analysis</p>
              <div className="flex flex-col gap-2">
                {EXAMPLE_QUERIES.cobolAnalysis.map((q, i) => (
                  <button key={i} onClick={() => handleSend(q)} className="text-left p-3 text-xs text-slate-300 bg-slate-800/50 hover:bg-indigo-500/20 border border-slate-800 hover:border-indigo-500/50 rounded-xl transition-all">
                    "{q}"
                  </button>
                ))}
              </div>
            </div>
            <div className="space-y-3">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Migration Planning</p>
              <div className="flex flex-col gap-2">
                {EXAMPLE_QUERIES.migrationPlanning.map((q, i) => (
                  <button key={i} onClick={() => handleSend(q)} className="text-left p-3 text-xs text-slate-300 bg-slate-800/50 hover:bg-indigo-500/20 border border-slate-800 hover:border-indigo-500/50 rounded-xl transition-all">
                    "{q}"
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* MAIN CHAT AREA */}
      <div className="flex-1 flex flex-col gap-6">
        <div className="glass-card p-6 rounded-3xl border-slate-800 relative">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-indigo-600 rounded-lg text-white"><MessageSquare size={18}/></div>
            <h3 className="font-bold text-white">Prompt</h3>
          </div>
          <div className="relative">
            <textarea 
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., What are the circular dependencies in this codebase?"
              className="w-full h-32 bg-slate-950 border border-slate-800 rounded-2xl p-4 text-sm text-slate-300 outline-none focus:ring-2 focus:ring-indigo-500 transition-all resize-none"
            />
            {prompt && (
              <button onClick={() => setPrompt('')} className="absolute top-4 right-4 text-slate-500 hover:text-white">
                <X size={16} />
              </button>
            )}
          </div>
          <div className="flex justify-end mt-4">
            <button onClick={() => handleSend()} disabled={isProcessing} className="btn-primary flex items-center gap-2 px-6">
              {isProcessing ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
              Send
            </button>
          </div>
        </div>

        <AnimatePresence>
          {isProcessing && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex justify-center gap-12 py-8">
              <ProcessingStep active={processingStep === 1} label="Database Query" sub="Fetching migration data..." icon={<Database size={20} />} />
              <ProcessingStep active={processingStep === 2} label="Azure OpenAI" sub="Processing with AI model..." icon={<Cpu size={20} />} />
              <ProcessingStep active={processingStep === 3} label="Building Response" sub="Formatting results..." icon={<LayoutTemplate size={20} />} />
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex-1 glass-card p-8 rounded-3xl border-slate-800 relative overflow-hidden">
          <div className="flex items-center gap-2 mb-6">
            <div className="p-2 bg-emerald-500/20 text-emerald-400 rounded-lg"><CheckCircle2 size={18}/></div>
            <h3 className="font-bold text-white">Response</h3>
          </div>
          <div className="space-y-6">
            {response ? (
              <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="text-slate-300 leading-relaxed text-sm">
                {response}
              </motion.div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center opacity-30 py-20">
                <MessageSquare size={48} className="mb-4 text-slate-600" />
                <p className="text-slate-500">Ask a question to see the AI analysis here.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModernizerChat;
