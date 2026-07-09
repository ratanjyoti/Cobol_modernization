import { CheckCircle2, Circle, Zap } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';

const ModernizationPlan = () => {
  const phases = [
    { name: 'Environment Setup', status: 'Complete', tasks: ['AI Model Config', 'Token Budgeting'] },
    { name: 'Analysis Phase', status: 'Complete', tasks: ['Chunking', 'Dependency Mapping'] },
    { name: 'Logic Extraction', status: 'In Progress', tasks: ['Business Rule Mapping', 'HITL Approval'] },
    { name: 'Code Generation', status: 'Pending', tasks: ['DTO Creation', 'Service Layer', 'Controller Implementation'] },
    { name: 'Refinement', status: 'Pending', tasks: ['Agentic Compilation', 'Unit Test Generation'] },
  ];

  const progressFor = (status: string) => {
    if (status === 'Complete') return 100;
    if (status === 'In Progress') return 54;
    return 8;
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Modernization Plan"
        description="A staged blueprint for transforming legacy COBOL into a modern application architecture."
        meta={<StatusBadge status="In Progress" />}
      />

      <SectionLabel>Blueprint Stages</SectionLabel>

      <div className="grid max-w-5xl gap-4">
        {phases.map((phase, index) => {
          const isComplete = phase.status === 'Complete';
          const isActive = phase.status === 'In Progress';
          return (
            <div key={phase.name} className="glass-card p-6">
              <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
                <div className="flex gap-4">
                  <div className={`mt-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border ${isComplete ? 'border-[var(--corporate-success)] bg-[var(--corporate-success)] text-white' : isActive ? 'border-[var(--corporate-accent)] bg-[var(--corporate-accent-soft)] text-[var(--corporate-accent)]' : 'border-[var(--corporate-border-strong)] text-[var(--corporate-muted)]'}`}>
                    {isComplete ? <CheckCircle2 size={20} /> : isActive ? <Zap size={18} /> : <Circle size={16} />}
                  </div>
                  <div>
                    <p className="label">Stage {String(index + 1).padStart(2, '0')}</p>
                    <h3 className="text-heading mt-1">{phase.name}</h3>
                    <div className="mt-4 flex flex-wrap gap-2">
                      {phase.tasks.map((task) => (
                        <span key={task} className="rounded-full border border-[var(--corporate-border)] bg-[var(--corporate-bg-soft)] px-3 py-1 text-sm font-semibold text-[var(--corporate-muted)]">{task}</span>
                      ))}
                    </div>
                  </div>
                </div>
                <StatusBadge status={phase.status} />
              </div>
              <div className="pipeline-card-progress mt-6">
                <span style={{ width: `${progressFor(phase.status)}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ModernizationPlan;
