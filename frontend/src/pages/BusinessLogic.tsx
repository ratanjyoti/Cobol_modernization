import { useState } from 'react';
import { CheckCircle2, AlertCircle, Edit3, ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';

interface BusinessRule {
  id: string;
  rule: string;
  description: string;
  status: 'AI-Generated' | 'Verified' | 'Modified';
}

const BusinessLogic = () => {
  const [rules, setRules] = useState<BusinessRule[]>([
    { id: 'R1', rule: 'Overdraft Limit', description: 'If account balance drops below $0, apply a 5% penalty fee and set flag WS-OVERDRAFT to "Y".', status: 'AI-Generated' },
    { id: 'R2', rule: 'Interest Calculation', description: 'Calculate monthly interest using the formula: (Balance * Rate) / 12.', status: 'Verified' },
    { id: 'R3', rule: 'Customer Validation', description: 'Verify if Customer ID exists in CUST-DB before processing any transaction.', status: 'AI-Generated' },
  ]);

  const updateStatus = (id: string, newStatus: BusinessRule['status']) => {
    setRules(rules.map(r => r.id === id ? { ...r, status: newStatus } : r));

    if (newStatus === 'Verified') {
      toast.success('Rule verified successfully!', { icon: 'OK' });
    } else {
      toast('Rule marked for modification', { icon: 'Edit' });
    }
  };

  const handleFinalApproval = () => {
    if (window.triggerHITL) {
      window.triggerHITL(
        'Business Logic',
        'Confirm Logic Baseline',
        'The AI has extracted 890 rules. Once approved, these will be used as the source of truth for Java code generation. This action cannot be undone.'
      );
    }
  };

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-5 border-b border-slate-800 pb-7 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="mb-3 flex items-center gap-2">
            <span className="label">Modernization Pipeline</span>
            <span className="text-[var(--corporate-faint)]">/</span>
            <span className="label text-[var(--corporate-accent)]">Business Logic</span>
          </div>
          <h1 className="text-page-title">Business Logic Extraction</h1>
          <p className="text-body-sm mt-2 max-w-2xl">Review, edit, and verify rules extracted from COBOL Procedure Divisions before code generation.</p>
        </div>
        <button onClick={handleFinalApproval} className="btn-glow">
          Approve All & Proceed <ArrowRight size={18} />
        </button>
      </header>

      <section>
        <SectionLabel>Extracted Rules</SectionLabel>
        <div className="grid grid-cols-1 gap-4">
          {rules.map((rule) => (
            <div key={rule.id} className="glass-card group flex items-start justify-between gap-5 border border-slate-700 bg-panel p-5 transition-all hover:border-slate-500">
              <div className="min-w-0 flex-1 space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="rounded-lg bg-accent/10 px-2 py-1 font-mono text-xs font-bold text-accent">{rule.id}</span>
                  <h3 className="text-card-title">{rule.rule}</h3>
                  <StatusBadge status={rule.status} />
                </div>
                <p className="text-body-sm max-w-4xl">{rule.description}</p>
              </div>

              <div className="flex gap-2 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100">
                <button
                  aria-label="Mark rule modified"
                  onClick={() => updateStatus(rule.id, 'Modified')}
                  className="rounded-lg border border-slate-600 bg-slate-800 p-2 text-slate-400 transition-all hover:text-white"
                >
                  <Edit3 size={16} />
                </button>
                <button
                  aria-label="Verify rule"
                  onClick={() => updateStatus(rule.id, 'Verified')}
                  className="rounded-lg border border-slate-600 bg-slate-800 p-2 text-slate-400 transition-all hover:text-green-400"
                >
                  <CheckCircle2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="glass-card flex items-center gap-3 border border-amber-500/30 bg-amber-500/10 p-4 text-amber-400">
        <AlertCircle size={20} />
        <p className="text-body-sm">
          <strong className="text-[var(--corporate-text)]">Human-in-the-Loop Required:</strong> The conversion engine will not start until at least 80% of rules are marked as <span className="underline">Verified</span>.
        </p>
      </div>
    </div>
  );
};

export default BusinessLogic;
