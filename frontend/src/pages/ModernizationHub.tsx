import { useState } from 'react';
import ModernizationPlan from './ModernizationPlan';
import CodeGeneration from './CodeGeneration';
import { LayoutTemplate, Code2 } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';

const ModernizationHub = () => {
  const [activeView, setActiveView] = useState<'plan' | 'gen'>('plan');

  return (
    <div className="space-y-6">
      <PageHeader
        title="Modernization Hub"
        description="Move from architectural blueprint to generated source code inside one modernization workspace."
        meta={<StatusBadge status="In Progress" />}
        action={(
          <div className="premium-tabs">
            <button onClick={() => setActiveView('plan')} className={`premium-tab ${activeView === 'plan' ? 'premium-tab-active' : 'premium-tab-idle'}`}>
              <LayoutTemplate size={15} /> Modern Plan
            </button>
            <button onClick={() => setActiveView('gen')} className={`premium-tab ${activeView === 'gen' ? 'premium-tab-active' : 'premium-tab-idle'}`}>
              <Code2 size={15} /> Code Generation
            </button>
          </div>
        )}
      />

      <div>{activeView === 'plan' ? <ModernizationPlan /> : <CodeGeneration />}</div>
    </div>
  );
};

export default ModernizationHub;
