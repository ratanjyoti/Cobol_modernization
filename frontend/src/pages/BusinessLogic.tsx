import { useState } from 'react';
import { CheckCircle2, AlertCircle, Edit3, ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';

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

  // This function MUST be inside the component to use setRules
  const updateStatus = (id: string, newStatus: BusinessRule['status']) => {
    setRules(rules.map(r => r.id === id ? { ...r, status: newStatus } : r));
    
    if (newStatus === 'Verified') {
      toast.success("Rule verified successfully!", { icon: '✅' });
    } else {
      toast("Rule marked for modification", { icon: '📝' });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white">Business Logic Extraction</h1>
          <p className="text-slate-400">Review and verify rules extracted from COBOL Procedure Divisions.</p>
        </div>
        <button className="bg-accent text-white px-6 py-2 rounded-lg font-bold flex items-center gap-2 hover:bg-blue-600 transition-all">
          Approve All & Proceed <ArrowRight size={18} />
        </button>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {rules.map((rule) => (
          <div key={rule.id} className="bg-panel border border-slate-700 rounded-xl p-5 flex items-start justify-between hover:border-slate-500 transition-all group">
            <div className="space-y-3 flex-1">
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono text-accent bg-accent/10 px-2 py-1 rounded">{rule.id}</span>
                <h3 className="text-white font-bold">{rule.rule}</h3>
                <span className={`text-[10px] uppercase px-2 py-0.5 rounded-full font-bold ${
                  rule.status === 'Verified' ? 'bg-green-500/20 text-green-400' : 
                  rule.status === 'Modified' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'
                }`}>
                  {rule.status}
                </span>
              </div>
              <p className="text-slate-400 text-sm leading-relaxed max-w-3xl">
                {rule.description}
              </p>
            </div>

            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <button 
                onClick={() => updateStatus(rule.id, 'Modified')}
                className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-white border border-slate-600"
              >
                <Edit3 size={16} />
              </button>
              <button 
                onClick={() => updateStatus(rule.id, 'Verified')}
                className="p-2 rounded-lg bg-slate-800 text-slate-400 hover:text-green-400 border border-slate-600"
              >
                <CheckCircle2 size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-amber-500/10 border border-amber-500/30 p-4 rounded-xl flex items-center gap-3 text-amber-400">
        <AlertCircle size={20} />
        <p className="text-xs">
          <strong className="text-white">Human-in-the-Loop Required:</strong> The conversion engine will not start until at least 80% of rules are marked as <span className="text-white underline">Verified</span>.
        </p>
      </div>
    </div>
  );
};

export default BusinessLogic;
