import { GitBranch, ArrowRight, Box, Database, Layers } from 'lucide-react';

const DDDDiscovery = () => {
  const mappings = [
    { cobol: 'ACCOUNT-PROC.cbl', modern: 'AccountService.java', type: 'Service', logic: 'Handles core balance updates' },
    { cobol: 'CUST-DB-RECORD', modern: 'CustomerEntity.java', type: 'Entity', logic: 'Maps to PostgreSQL Customer Table' },
    { cobol: 'REPORT-GEN.cbl', modern: 'ReportingController.java', type: 'API Controller', logic: 'Exposes Monthly statements via REST' },
    { cobol: 'WS-TRAN-LOG', modern: 'TransactionRepository.java', type: 'Repository', logic: 'Handles I/O for transaction history' },
  ];

  return (
    <div className="space-y-6">
      {/* 1. Proposed Architecture - Now at the top and compact */}
      <div className="bg-slate-900/50 border border-slate-700 rounded-2xl p-4">
        <div className="flex items-center gap-2 text-white font-bold mb-3">
          <Box size={18} className="text-indigo-400" />
          <h3 className="text-sm">Proposed Architecture</h3>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="flex items-center gap-2 p-2 bg-slate-950 rounded-lg border border-slate-800">
            <Layers size={14} className="text-blue-400" />
            <span className="text-[10px] text-slate-300">Spring Boot 3.2</span>
          </div>
          <div className="flex items-center gap-2 p-2 bg-slate-950 rounded-lg border border-slate-800">
            <Database size={14} className="text-blue-400" />
            <span className="text-[10px] text-slate-300">PostgreSQL</span>
          </div>
          <div className="flex items-center gap-2 p-2 bg-slate-950 rounded-lg border border-slate-800">
            <GitBranch size={14} className="text-blue-400" />
            <span className="text-[10px] text-slate-300">REST API</span>
          </div>
        </div>
      </div>

      {/* 2. Mapping Table - Now full width of the 60% box */}
      <div className="bg-panel border border-slate-700 rounded-xl overflow-hidden">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
            <tr className="border-b border-slate-700">
              <th className="p-4">COBOL Source</th>
              <th className="p-4 text-center">$\rightarrow$</th>
              <th className="p-4">Modern Target</th>
              <th className="p-4">Role</th>
            </tr>
          </thead>
          <tbody className="text-slate-300 divide-y divide-slate-700">
            {mappings.map((m, i) => (
              <tr key={i} className="hover:bg-slate-800/30 transition-colors">
                <td className="p-4 font-mono text-slate-400 text-xs">{m.cobol}</td>
                <td className="p-4 text-center text-indigo-400">$\rightarrow$</td>
                <td className="p-4 font-mono text-blue-400 text-xs">{m.modern}</td>
                <td className="p-4">
                  <span className="bg-slate-700 text-slate-300 px-2 py-1 rounded text-[10px] uppercase font-bold">
                    {m.type}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DDDDiscovery;