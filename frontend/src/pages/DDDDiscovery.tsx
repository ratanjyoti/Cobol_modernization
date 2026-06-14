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
      <div>
        <h1 className="text-3xl font-bold text-white">DDD Discovery</h1>
        <p className="text-slate-400">Mapping COBOL paragraphs to Modern Domain Entities and Services.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: The Mapping Table */}
        <div className="lg:col-span-2 bg-panel border border-slate-700 rounded-xl overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-800 text-slate-400 uppercase text-xs">
              <tr>
                <th className="p-4">COBOL Source</th>
                <th className="p-4 text-center"><ArrowRight size={14} className="inline"/></th>
                <th className="p-4">Modern Target</th>
                <th className="p-4">Role</th>
              </tr>
            </thead>
            <tbody className="text-slate-300 divide-y divide-slate-700">
              {mappings.map((m, i) => (
                <tr key={i} className="hover:bg-slate-800/30">
                  <td className="p-4 font-mono text-slate-400">{m.cobol}</td>
                  <td className="p-4 text-center text-accent"> $\rightarrow$ </td>
                  <td className="p-4 font-mono text-blue-400">{m.modern}</td>
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

        {/* Right: Architecture Summary */}
        <div className="space-y-4">
          <div className="bg-panel border border-slate-700 rounded-xl p-6">
            <div className="flex items-center gap-2 text-white font-bold mb-4">
              <Box size={20} className="text-accent" />
              <h3>Proposed Architecture</h3>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 bg-darkbg rounded-lg border border-slate-800">
                <Layers size={16} className="text-blue-400" />
                <span className="text-xs text-slate-300">Spring Boot 3.2 (Java 21)</span>
              </div>
              <div className="flex items-center gap-3 p-3 bg-darkbg rounded-lg border border-slate-800">
                <Database size={16} className="text-blue-400" />
                <span className="text-xs text-slate-300">PostgreSQL (Relational)</span>
              </div>
              <div className="flex items-center gap-3 p-3 bg-darkbg rounded-lg border border-slate-800">
                <GitBranch size={16} className="text-blue-400" />
                <span className="text-xs text-slate-300">RESTful API Architecture</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DDDDiscovery;
