import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, CheckCircle2, ArrowLeft } from 'lucide-react';

interface HITLModalProps {
  isOpen: boolean;
  onApprove: () => void;
  onDeny: () => void;
  config: {
    step: string;    // Changed from tabName to step
    message: string;
    reason: string;
  };
}

const HITLModal = ({ isOpen, onApprove, onDeny, config }: HITLModalProps) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
          {/* Backdrop with heavy blur for focus */}
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onDeny}
            className="absolute inset-0 bg-slate-950/80 backdrop-blur-md" 
          />

          {/* Modal Content */}
          <motion.div 
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            className="relative w-full max-w-md bg-slate-900 border border-amber-500/30 rounded-3xl shadow-2xl overflow-hidden"
          >
            {/* High-Visibility Warning Top Bar */}
            <div className="bg-amber-500/10 border-b border-amber-500/20 p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <AlertTriangle className="text-amber-500" size={20} />
                <span className="text-xs font-bold text-amber-500 uppercase tracking-widest">
                  Action Required
                </span>
              </div>
              {/* Step Badge */}
              <div className="px-2 py-1 rounded bg-amber-500/20 border border-amber-500/30 text-amber-500 text-[10px] font-black uppercase">
                {config.step}
              </div>
            </div>

            <div className="p-8 space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <h3 className="text-2xl font-bold text-white leading-tight">
                    Pipeline Paused for Approval
                  </h3>
                  <p className="text-slate-400 text-sm leading-relaxed">
                    {config.message}
                  </p>
                </div>
                
                {/* Reason/Context box */}
                <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 text-slate-400 text-xs italic">
                  "{config.reason}"
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button 
                  onClick={onDeny}
                  className="flex-1 py-3 rounded-xl bg-slate-800 text-slate-300 font-bold hover:bg-slate-700 transition-all flex items-center justify-center gap-2"
                >
                  <ArrowLeft size={16} /> Review Details
                </button>
                <button 
                  onClick={onApprove}
                  className="flex-1 py-3 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-500 transition-all shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2"
                >
                  <CheckCircle2 size={16} /> Approve & Resume
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default HITLModal;
