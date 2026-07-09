import { useState } from 'react';
import PromptStudio from './PromptStudio';
import Settings from './Settings';
import { Settings as SettingsIcon, MessageSquareCode } from 'lucide-react';
import PageHeader from '../components/PageHeader';
import StatusBadge from '../components/StatusBadge';

const SystemAdmin = () => {
  const [activeView, setActiveView] = useState<'prompts' | 'settings'>('prompts');

  return (
    <div className="space-y-6">
      <PageHeader
        title="System Administration"
        description="Configure AI constitutions, global behavior, provider settings, and operational defaults."
        meta={<StatusBadge status="Healthy" />}
        action={(
          <div className="premium-tabs">
            <button
              onClick={() => setActiveView('prompts')}
              className={`premium-tab ${activeView === 'prompts' ? 'premium-tab-active' : 'premium-tab-idle'}`}
            >
              <MessageSquareCode size={15} />
              Prompt Studio
            </button>
            <button
              onClick={() => setActiveView('settings')}
              className={`premium-tab ${activeView === 'settings' ? 'premium-tab-active' : 'premium-tab-idle'}`}
            >
              <SettingsIcon size={15} />
              System Settings
            </button>
          </div>
        )}
      />

      <div>{activeView === 'prompts' ? <PromptStudio /> : <Settings />}</div>
    </div>
  );
};

export default SystemAdmin;
