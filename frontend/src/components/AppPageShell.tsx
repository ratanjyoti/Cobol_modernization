import type { ReactNode } from 'react';
import { Info } from 'lucide-react';

type AppPageShellProps = {
  header: ReactNode;
  explorer: ReactNode;
  inspector?: ReactNode;
  footer?: ReactNode;
  inspectorWidth?: 'sm' | 'md' | 'lg';
};

export const AppPageShell = ({ header, explorer, inspector, footer, inspectorWidth = 'md' }: AppPageShellProps) => {
  const widthClass = inspectorWidth === 'lg' ? 'xl:grid-cols-[minmax(0,1.6fr)_minmax(360px,0.8fr)]' : inspectorWidth === 'sm' ? 'xl:grid-cols-[minmax(0,1.8fr)_minmax(300px,0.55fr)]' : 'xl:grid-cols-[minmax(0,1.7fr)_minmax(340px,0.7fr)]';

  return (
    <div className="enterprise-page">
      <div className="enterprise-page-header">{header}</div>
      <div className={`enterprise-split-pane ${widthClass}`}>
        <section className="enterprise-explorer-panel">{explorer}</section>
        {inspector && <aside className="enterprise-inspector-panel">{inspector}</aside>}
      </div>
      {footer && <div className="enterprise-action-bar">{footer}</div>}
    </div>
  );
};

type EmptyInspectorProps = {
  title?: string;
  description?: string;
};

export const EmptyInspector = ({ title = 'Select an item', description = 'Choose an item from the explorer to view detailed analysis.' }: EmptyInspectorProps) => (
  <div className="enterprise-empty-state">
    <Info size={42} />
    <p>{title}</p>
    <small>{description}</small>
  </div>
);
