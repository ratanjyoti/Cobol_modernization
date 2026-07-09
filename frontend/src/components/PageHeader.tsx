import type { ReactNode } from 'react';

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  meta?: ReactNode;
}

const PageHeader = ({ eyebrow = 'Modernization Pipeline', title, description, action, meta }: PageHeaderProps) => (
  <header className="premium-page-header">
    <div className="min-w-0">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span className="label">{eyebrow}</span>
        <span className="text-[var(--corporate-faint)]">/</span>
        <span className="label text-[var(--corporate-accent)]">{title}</span>
        {meta && <span className="ml-2">{meta}</span>}
      </div>
      <h1 className="text-page-title">{title}</h1>
      {description && <p className="text-body-sm mt-2 max-w-3xl">{description}</p>}
    </div>
    {action && <div className="shrink-0">{action}</div>}
  </header>
);

export default PageHeader;
