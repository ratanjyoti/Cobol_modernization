import type { ReactNode } from 'react';

interface SectionLabelProps {
  children: ReactNode;
  className?: string;
}

const SectionLabel = ({ children, className = '' }: SectionLabelProps) => (
  <div className={`premium-section-label ${className}`}>
    <span className="premium-section-dot" />
    <span className="label whitespace-nowrap">{children}</span>
    <span className="premium-section-line" />
  </div>
);

export default SectionLabel;
