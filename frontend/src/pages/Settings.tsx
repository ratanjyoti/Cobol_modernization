import { Settings as SettingsIcon, Key, Cpu, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import PageHeader from '../components/PageHeader';
import SectionLabel from '../components/SectionLabel';
import StatusBadge from '../components/StatusBadge';
import ConfigPanel from '../components/ConfigPanel';

const Settings = () => {
  const clearConfig = () => {
    if (window.confirm('Are you sure you want to clear all AI configurations?')) {
      localStorage.removeItem('ai_config');
      window.dispatchEvent(new Event('ai-config-updated'));
      toast.success('Configuration cleared!');
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="AI Configuration"
        description="Manage provider mode, API keys, local endpoint, model selection, and operational defaults."
        meta={<StatusBadge status={localStorage.getItem('ai_config') ? 'Healthy' : 'Pending'} />}
      />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="glass-card p-3 space-y-2">
          <button className="flex w-full items-center gap-3 rounded-lg bg-[var(--corporate-accent)] p-4 font-bold text-white">
            <Cpu size={18} /> AI Configuration
          </button>
          <button className="flex w-full items-center gap-3 rounded-lg p-4 text-left font-medium text-[var(--corporate-muted)] transition-all hover:bg-[var(--corporate-accent-soft)] hover:text-[var(--corporate-accent)]">
            <Key size={18} /> API Management
          </button>
          <button className="flex w-full items-center gap-3 rounded-lg p-4 text-left font-medium text-[var(--corporate-muted)] transition-all hover:bg-[var(--corporate-accent-soft)] hover:text-[var(--corporate-accent)]">
            <SettingsIcon size={18} /> General Preferences
          </button>
        </aside>

        <section className="space-y-8">
          <div className="glass-card p-8 space-y-6">
            <div>
              <SectionLabel>Shared AI Configuration</SectionLabel>
              <div className="mt-4 flex items-center gap-3">
                <div className="rounded-lg bg-[var(--corporate-accent-soft)] p-2 text-[var(--corporate-accent)]"><Cpu size={20} /></div>
                <h3 className="text-heading">Provider and Model Settings</h3>
              </div>
              <p className="text-body-sm mt-3 max-w-2xl">
                This is the same configuration used on the Dashboard. Changes saved here are available immediately for new runs and dashboard project creation.
              </p>
            </div>

            <ConfigPanel runId={localStorage.getItem('active_run_id')} />
          </div>

          <div className="glass-card p-8">
            <SectionLabel>Danger Zone</SectionLabel>
            <button onClick={clearConfig} className="mt-4 flex items-center gap-2 font-bold text-[var(--corporate-danger)] transition-colors hover:opacity-80">
              <AlertTriangle size={16} /> Reset all AI settings to default
            </button>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Settings;
