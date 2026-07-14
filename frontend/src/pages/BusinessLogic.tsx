import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle2, AlertCircle, Edit3, ArrowRight, 
  Code, Loader2, X, Save, Search, FileText, Zap, Info
} from 'lucide-react';
import toast from 'react-hot-toast';
import { ProjectAPI } from '../services/api';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';

interface BusinessRule {
  id: number;
  rule_id: string;
  rule_text: string;
  technical_yaml: string; // Changed from technical_ref to match backend
  status: 'PENDING' | 'VERIFIED' | 'REJECTED';
  filename: string;
}

const BusinessLogic = () => {
  const navigate = useNavigate();
  const runId = localStorage.getItem('active_run_id');
  
  const [rules, setRules] = useState<BusinessRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRule, setSelectedRule] = useState<BusinessRule | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    loadRules();
  }, [runId]);

  const loadRules = async () => {
    if (!runId) return;
    setLoading(true);
    try {
      const data = await ProjectAPI.getBusinessRules(runId);
      setRules(data);
    } catch (e) {
      toast.error("Failed to load business rules");
    } finally {
      setLoading(false);
    }
  };

  const handleExtract = async () => {
    setLoading(true);
    try {
      await ProjectAPI.extractBusinessRules(runId!);
      await loadRules();
      toast.success("Business rules extracted successfully!");
    } catch (e) {
      toast.error("Extraction failed");
    } finally {
      setLoading(false);
    }
  };

  const updateRule = async (id: number, status: string, text?: string) => {
    try {
      await ProjectAPI.verifyRule(id, { status, text });
      setRules(prev => prev.map(r => r.id === id ? { ...r, status, rule_text: text || r.rule_text } : r));
      toast.success(`Rule ${status === 'VERIFIED' ? 'verified' : 'updated'}`);
      if (selectedRule?.id === id) {
        setSelectedRule(prev => prev ? { ...prev, status, rule_text: text || prev.rule_text } : null);
      }
    } catch (e) {
      toast.error("Failed to update rule");
    }
  };

  const verificationPercentage = useMemo(() => {
    if (rules.length === 0) return 0;
    const verified = rules.filter(r => r.status === 'VERIFIED').length;
    return Math.round((verified / rules.length) * 100);
  }, [rules]);

  const filteredRules = rules.filter(r => 
    r.rule_text.toLowerCase().includes(searchTerm.toLowerCase()) || 
    r.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6 h-full">
      {/* HEADER */}
      <header className="flex flex-col gap-5 border-b border-slate-800 pb-7 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-1">
          <div className="mb-3 flex items-center gap-2">
            <span className="label">Modernization Pipeline</span>
            <span className="text-slate-600">/</span>
            <span className="label text-indigo-400">Business Logic</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight">Business Logic Extraction</h1>
          <p className="text-slate-400">Review and verify extracted rules. This is the source of truth for the AI Converter.</p>
        </div>
        
        <div className="flex flex-col items-end gap-3">
          <div className="flex items-center gap-4">
             <div className="text-right">
                <p className="text-xs font-bold text-slate-500 uppercase">Verification Progress</p>
                <p className={`text-xl font-black ${verificationPercentage >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {verificationPercentage}%
                </p>
              </div>
              <button 
                onClick={handleExtract}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-bold transition-all flex items-center gap-2 border border-slate-700"
              >
                <Zap size={14} /> Re-Extract Rules
              </button>
          </div>
          <button 
            onClick={() => navigate('/code-generation')} 
            disabled={verificationPercentage < 80}
            className={`btn-glow flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all ${verificationPercentage >= 80 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-500 cursor-not-allowed'}`}
          >
            Approve Baseline & Proceed <ArrowRight size={18} />
          </button>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-6 h-[calc(100vh-300px)]">
        {/* LEFT: Rules List */}
        <div className="col-span-5 space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
            <input 
              type="text" 
              placeholder="Search rules or files..." 
              className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="space-y-3 overflow-y-auto max-h-[60vh] pr-2">
            {loading ? (
              <div className="flex justify-center p-10"><Loader2 className="animate-spin text-indigo-500" /></div>
            ) : filteredRules.map((rule) => (
              <div 
                key={rule.id} 
                onClick={() => setSelectedRule(rule)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${selectedRule?.id === rule.id ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-800 bg-slate-900 hover:border-slate-600'}`}
              >
                <div className="flex justify-between items-center mb-2">
                  <span className="font-mono text-[10px] text-indigo-400 font-bold">{rule.rule_id}</span>
                  <StatusBadge status={rule.status === 'VERIFIED' ? 'Verified' : 'Pending'} />
                </div>
                <p className="text-sm text-slate-300 line-clamp-2">{rule.rule_text}</p>
                <p className="text-[10px] text-slate-500 mt-2">{rule.filename}</p>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT: Detail & Evidence Panel */}
        <div className="col-span-7 glass-card p-6 border-indigo-500/30 bg-slate-900/50 rounded-3xl overflow-y-auto">
          {selectedRule ? (
            <div className="space-y-6">
              <div className="flex justify-between items-center border-b border-slate-800 pb-4">
                <div>
                  <h3 className="text-xl font-bold text-white">{selectedRule.rule_id}</h3>
                  <p className="text-xs text-slate-500 font-mono">{selectedRule.filename}</p>
                </div>
                <div className="flex gap-2">
                  <button 
                    onClick={() => setIsEditing(true)}
                    className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition-all"
                  >
                    <Edit3 size={18}/>
                  </button>
                  <button 
                    onClick={() => updateRule(selectedRule.id, 'VERIFIED')}
                    className="p-2 rounded-lg bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600 hover:text-white transition-all"
                  >
                    <CheckCircle2 size={18}/>
                  </button>
                </div>
              </div>

              <div className="space-y-4">
                {/* Business Logic Section */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-500 uppercase">Business Rule (Plain English)</label>
                  {isEditing ? (
                    <textarea 
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm text-white outline-none focus:ring-2 focus:ring-indigo-500 h-32"
                      value={selectedRule.rule_text}
                      onChange={(e) => setSelectedRule({...selectedRule, rule_text: e.target.value})}
                    />
                  ) : (
                    <div className="p-4 bg-slate-800/50 rounded-xl border border-slate-700 text-slate-200 text-sm leading-relaxed">
                      {selectedRule.rule_text}
                    </div>
                  )}
                  {isEditing && (
                    <div className="flex justify-end gap-2">
                      <button onClick={() => setIsEditing(false)} className="px-3 py-1 text-xs text-slate-400">Cancel</button>
                      <button 
                        onClick={() => {
                          updateRule(selectedRule.id, 'VERIFIED', selectedRule.rule_text);
                          setIsEditing(false);
                        }} 
                        className="px-3 py-1 bg-indigo-600 text-white rounded-lg text-xs font-bold"
                      >
                        Save Changes
                      </button>
                    </div>
                  )}
                </div>

                {/* Technical Evidence Section */}
                <div className="space-y-2">
                  <label className="text-xs font-bold text-slate-500 uppercase flex items-center gap-2">
                    <Code size={14} /> Technical Evidence (AI Analysis)
                  </label>
                  <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 font-mono text-xs text-indigo-300 whitespace-pre-wrap overflow-x-auto">
                    {selectedRule.technical_yaml}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
              <Info size={40} className="text-slate-600" />
              <p className="text-sm text-slate-500">Select a rule from the left to review the technical evidence and verify the business logic.</p>
            </div>
          )}
        </div>
      </div>

      {/* FOOTER ALERT */}
      <div className="glass-card flex items-center gap-3 border border-amber-500/30 bg-amber-500/10 p-4 text-amber-400 rounded-2xl">
        <AlertCircle size={20} />
        <p className="text-body-sm">
          <strong className="text-white">Human-in-the-Loop Gate:</strong> The conversion engine is locked. You must verify <span className="font-bold underline">{Math.ceil(rules.length * 0.8)}</span> rules to unlock the Java Generation phase.
        </p>
      </div>
    </div>
  );
};

export default BusinessLogic;
