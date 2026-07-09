import { useState } from 'react';
import { Download, Copy, CheckCircle2, ChevronRight, Search, RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';
import PageHeader from '../components/PageHeader';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';

const artifacts = [
  { id: '1', name: 'AccountService.java', type: 'Service', readiness: 92, status: 'Verified' },
  { id: '2', name: 'CustomerEntity.java', type: 'Entity', readiness: 88, status: 'Verified' },
  { id: '3', name: 'AccountRepository.java', type: 'Repository', readiness: 76, status: 'Review' },
  { id: '4', name: 'TransactionDTO.java', type: 'DTO', readiness: 61, status: 'Review' },
];

const CodeGeneration = () => {
  const [selectedId, setSelectedId] = useState('1');
  const selected = artifacts.find((artifact) => artifact.id === selectedId) || artifacts[0];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Code Generation"
        description="Review AI generated artifacts, inspect readiness, and export the modernized implementation package."
        action={(
          <button className="btn-glow">
            <Download size={18} />
            Export Project
          </button>
        )}
        meta={<StatusBadge status="AI-Generated" />}
      />

      <div className="grid gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="glass-card p-5 space-y-5">
          <div className="flex items-center justify-between gap-3">
            <SectionLabel className="flex-1">Artifacts</SectionLabel>
            <button className="btn-secondary flex items-center gap-2 px-3 py-2 text-sm">
              <RefreshCw size={15} />
              Regenerate
            </button>
          </div>

          <label className="relative block">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--corporate-muted)]" size={16} />
            <input
              type="text"
              placeholder="Find artifact..."
              className="w-full rounded-lg border border-[var(--corporate-border)] bg-[var(--corporate-bg-soft)] py-3 pl-10 pr-4 text-sm outline-none focus:ring-2 focus:ring-[var(--corporate-accent)]"
            />
          </label>

          <div className="space-y-3">
            {artifacts.map((item) => (
              <motion.button
                key={item.id}
                type="button"
                onClick={() => setSelectedId(item.id)}
                className={`glass-card w-full p-4 text-left transition-all ${selectedId === item.id ? 'ring-2 ring-[var(--corporate-accent)]' : ''}`}
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-card-title truncate">{item.name}</p>
                    <p className="label mt-1">{item.type}</p>
                  </div>
                  <StatusBadge status={item.status} />
                </div>
                <div className="flex items-center justify-between text-body-sm">
                  <span>Readiness</span>
                  <span className="font-mono font-bold text-[var(--corporate-text)]">{item.readiness}%</span>
                </div>
                <div className="pipeline-card-progress mt-3">
                  <span style={{ width: `${item.readiness}%` }} />
                </div>
              </motion.button>
            ))}
          </div>
        </aside>

        <main className="min-w-0 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-body-sm">
              <span>Artifacts</span>
              <ChevronRight size={14} />
              <span className="font-bold text-[var(--corporate-text)]">{selected.name}</span>
            </div>
            <StatusBadge status={selected.status} />
          </div>

          <section className="glass-card p-6 space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <SectionLabel>Selected Artifact</SectionLabel>
                <h2 className="text-heading mt-3">{selected.name}</h2>
                <p className="text-body-sm mt-1">Modernized Java 21 implementation with validation context and generated service contracts.</p>
              </div>
              <button className="btn-secondary flex items-center gap-2 px-3 py-2">
                <Copy size={15} />
                Copy
              </button>
            </div>

            <div className="kpi-bento">
              <div className="glass-card kpi-featured p-5 flex flex-col justify-between">
                <div>
                  <p className="label">Coverage</p>
                  <p className="text-display mt-2">{selected.readiness}%</p>
                  <p className="text-body-sm mt-2">Generated implementation coverage across extracted business logic.</p>
                </div>
                <div className="pipeline-card-progress mt-6">
                  <span style={{ width: `${selected.readiness}%` }} />
                </div>
              </div>
              <div className="glass-card p-5">
                <p className="label">Complexity</p>
                <p className="text-heading mt-2">Medium</p>
                <p className="text-body-sm mt-2">Manual review recommended for repository boundaries.</p>
              </div>
              <div className="glass-card p-5">
                <p className="label">Verification</p>
                <p className="mt-2 flex items-center gap-2 font-bold text-[var(--corporate-success)]"><CheckCircle2 size={18} /> Passed</p>
              </div>
              <div className="glass-card p-5">
                <p className="label">Framework</p>
                <p className="text-heading mt-2">Spring Boot</p>
              </div>
              <div className="glass-card p-5">
                <p className="label">Language</p>
                <p className="text-heading mt-2">Java 21</p>
              </div>
            </div>

            <div className="rounded-lg border border-[var(--corporate-border-strong)] bg-[var(--terminal-bg)] p-5 font-mono text-sm text-[var(--terminal-text)] overflow-auto">
              <pre>{`public class ${selected.name.replace('.java', '')} {\n  @Service\n  public void process() {\n    // AI modernized logic\n    if (balance < 0) applyPenalty();\n  }\n}`}</pre>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
};

export default CodeGeneration;
