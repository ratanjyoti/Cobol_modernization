import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertCircle, CheckCircle2, ArrowLeft } from 'lucide-react';

interface HITLModalProps {
  isOpen: boolean;
  onApprove: () => void;
  onDeny: () => void;
  config: {
    tabName: string;
    message: string;
    reason: string;
  };
}

const HITLModal = ({ isOpen, onApprove, onDeny, config }: HITLModalProps) => {
  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onDeny}
            className="absolute inset-0 bg-slate-950/80 backdrop-blur-md" 
          />

          {/* Modal */}
          <motion.div 
            initial={{ scale: 0.9, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.9, opacity: 0, y: 20 }}
            className="relative w-full max-w-md bg-slate-900 border border-amber-500/30 rounded-3xl shadow-2xl overflow-hidden"
          >
            {/* Warning Top Bar */}
            <div className="bg-amber-500/10 border-b border-amber-500/20 p-4 flex items-center gap-3">
              <AlertCircle className="text-amber-500" size={20} />
              <span className="text-xs font-bold text-amber-500 uppercase tracking-widest">Human-in-the-Loop Required</span>
            </div>

            <div className="p-8 space-y-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase">
                  <span className="w-1 h-1 bg-slate-500 rounded-full"></span>
                  Target: {config.tabName}
                </div>
                <h3 className="text-xl font-bold text-white">{config.message}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">
                  {config.reason}
                </p>
              </div>

              <div className="flex gap-3 pt-4">
                <button 
                  onClick={onDeny}
                  className="flex-1 py-3 rounded-xl bg-slate-800 text-slate-300 font-bold hover:bg-slate-700 transition-all flex items-center justify-center gap-2"
                >
                  <ArrowLeft size={16} /> Edit Rules
                </button>
                <button 
                  onClick={onApprove}
                  className="flex-1 py-3 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-500 transition-all shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2"
                >
                  <CheckCircle2 size={16} /> Approve & Proceed
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
