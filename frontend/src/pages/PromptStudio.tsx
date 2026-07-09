import { useState } from 'react';
import { Save, Play, FileText, AlertTriangle } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';

const PromptStudio = () => {
  const [prompts, setPrompts] = useState({
    conversion:
      'Convert the following COBOL code to Java 21. Use Spring Boot 3 annotations. Ensure BigDecimals are used for financial calculations. Follow DDD principles.',
    refinement:
      'Analyze the generated Java code for performance bottlenecks. Suggest optimizations for loop structures and database queries.',
    extraction:
      'Extract business rules from the COBOL Procedure Division. Format as: Rule ID | Rule Name | Functional Requirement.',
  });

  const handleSave = () => {
    alert('Constitution.yaml updated successfully!');
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Prompt Studio"
        description="Fine-tune the AI behavior by editing the system constitutions used across modernization agents."
        action={(
          <button onClick={handleSave} className="btn-glow">
            <Save size={18} />
            Save Constitution
          </button>
        )}
        meta={<StatusBadge status="Modified" pulse={false} />}
      />

      <SectionLabel>Prompt Constitution</SectionLabel>

      <div className="grid grid-cols-1 gap-5">
        {Object.entries(prompts).map(([key, value]) => (
          <section key={key} className="glass-card p-6 space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-[var(--corporate-accent-soft)] p-2 text-[var(--corporate-accent)]">
                  <FileText size={18} />
                </div>
                <div>
                  <h3 className="text-heading capitalize">{key.replace('_', ' ')} Prompt</h3>
                  <p className="text-body-sm">Agent instruction surface for this modernization stage.</p>
                </div>
              </div>
              <button className="btn-secondary flex items-center gap-2 px-3 py-2">
                <Play size={14} />
                Test Prompt
              </button>
            </div>

            <textarea
              value={value}
              onChange={(event) => setPrompts({ ...prompts, [key]: event.target.value })}
              className="h-40 w-full resize-none rounded-lg border border-[var(--corporate-border)] bg-[var(--terminal-bg)] p-4 font-mono text-sm text-[var(--terminal-text)] outline-none transition-all focus:ring-2 focus:ring-[var(--corporate-accent)]"
            />

            <div className="flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-[var(--corporate-warning)]">
              <AlertTriangle size={14} />
              <span>Changes affect current and future migration pipeline executions.</span>
            </div>
          </section>
        ))}
      </div>
    </div>
  );
};

export default PromptStudio;
