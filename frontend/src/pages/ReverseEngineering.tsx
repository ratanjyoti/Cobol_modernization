import { useState } from 'react';
import { FileSearch, Layout, ListChecks, ChevronRight } from 'lucide-react';

const ReverseEngineering = () => {
  const [activeTab, setActiveTab] = useState('structure');

  const mockAnalysis = {
    structure: [
      { name: 'Identification Division', status: 'Complete', detail: 'Program ID: ACCT-PROC-01' },
      { name: 'Environment Division', status: 'Complete', detail: 'Input-Output Section mapped' },
      { name: 'Data Division', status: 'Analyzing', detail: 'Extracting Working-Storage variables' },
      { name: 'Procedure Division', status: 'Pending', detail: 'Paragraph flow analysis' },
    ],
    variables: [
      { name: 'WS-CUST-BALANCE', type: 'PIC S9(7)V99', usage: 'Balance calculation' },
      { name: 'WS-CUST-NAME', type: 'PIC X(30)', usage: 'Customer identification' },
      { name: 'WS-TRAN-DATE', type: 'PIC 9(8)', usage: 'Transaction timestamp' },
    ],
    logic: [
      { rule: 'Rule 1', description: 'If balance < 0, trigger Overdraft-Flag' },
      { rule: 'Rule 2', description: 'Monthly interest is calculated based on Average Daily Balance' },
    ]
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white">Reverse Engineering</h1>
          <p className="text-slate-400">Analyzing <span className="text-accent font-mono">ACCOUNT-PROC.cbl</span></p>
        </div>
        <div className="flex gap-2">
          <button className="bg-panel border border-slate-700 text-white px-4 py-2 rounded-lg text-sm hover:bg-slate-800">Export Model</button>
          <button className="bg-accent text-white px-4 py-2 rounded-lg text-sm font-bold">Run AI Analysis</button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-4 border-b border-slate-700">
        {['structure', 'variables', 'logic'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-3 px-2 text-sm font-medium capitalize transition-all ${
              activeTab === tab ? 'text-accent border-b-2 border-accent' : 'text-slate-400 hover:text-white'
            }`}
          >
            {tab.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          {activeTab === 'structure' && (
            <div className="bg-panel border border-slate-700 rounded-xl divide-y divide-slate-700">
              {mockAnalysis.structure.map((item, i) => (
                <div key={i} className="p-4 flex items-center justify-between hover:bg-slate-800/40">
                  <div className="flex items-center gap-3">
                    <Layout size={18} className="text-slate-500" />
                    <span className="text-white font-medium">{item.name}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={`text-xs px-2 py-1 rounded ${
                      item.status === 'Complete' ? 'bg-green-500/10 text-green-400' : 
                      item.status === 'Analyzing' ? 'bg-blue-500/10 text-blue-400' : 'bg-slate-700 text-slate-400'
                    }`}>{item.status}</span>
                    <ChevronRight size={16} className="text-slate-600" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'variables' && (
            <div className="bg-panel border border-slate-700 rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
                  <tr>
                    <th className="p-4">Variable Name</th>
                    <th className="p-4">COBOL Type</th>
                    <th className="p-4">AI Interpreted Usage</th>
                  </tr>
                </thead>
                <tbody className="text-slate-300 divide-y divide-slate-700">
                  {mockAnalysis.variables.map((v, i) => (
                    <tr key={i} className="hover:bg-slate-800/30">
                      <td className="p-4 font-mono text-accent">{v.name}</td>
                      <td className="p-4 font-mono">{v.type}</td>
                      <td className="p-4">{v.usage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'logic' && (
            <div className="space-y-4">
              {mockAnalysis.logic.map((l, i) => (
                <div key={i} className="bg-panel border border-slate-700 p-4 rounded-xl flex gap-4">
                  <div className="bg-accent/20 p-2 rounded-lg h-fit">
                    <ListChecks size={20} className="text-accent" />
                  </div>
                  <div>
                    <h4 className="text-white font-bold text-sm">{l.rule}</h4>
                    <p className="text-slate-400 text-sm">{l.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Side Panel: AI Insights */}
        <div className="bg-panel border border-slate-700 rounded-xl p-6 h-fit space-y-6">
          <div className="flex items-center gap-2 text-accent font-bold">
            <FileSearch size={20} />
            <h3>AI Insight</h3>
          </div>
          <div className="p-4 bg-darkbg rounded-lg border border-slate-600">
            <p className="text-xs text-slate-300 leading-relaxed">
              "This program appears to be a <span className="text-white font-bold">Batch Processing Module</span> for account updates. I detected 3 redundant loops in the Procedure Division that can be optimized during Java conversion."
            </p>
          </div>
          <div className="space-y-3">
            <p className="text-xs text-slate-500 uppercase font-bold">Suggested Action</p>
            <button className="w-full text-left text-xs p-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all">
              $\rightarrow$ Map to Domain Entity
            </button>
            <button className="w-full text-left text-xs p-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-all">
              $\rightarrow$ Extract Business Rules
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReverseEngineering;
