interface StatusBadgeProps {
  status: string;
  pulse?: boolean;
  className?: string;
}

const toneMap: Record<string, string> = {
  Verified: 'success',
  Healthy: 'success',
  Complete: 'success',
  Completed: 'success',
  Running: 'active',
  'In Progress': 'active',
  'AI-Generated': 'active',
  Review: 'warning',
  Modified: 'warning',
  Action: 'danger',
  Pending: 'neutral',
  CONFIGURING: 'active',
};

const pulseStatuses = new Set(['Running', 'In Progress', 'AI-Generated', 'CONFIGURING']);

const StatusBadge = ({ status, pulse, className = '' }: StatusBadgeProps) => {
  const tone = toneMap[status] || toneMap[status?.toUpperCase?.()] || 'neutral';
  const shouldPulse = pulse ?? pulseStatuses.has(status);

  return (
    <span className={`status-badge status-badge-${tone} ${className}`}>
      <span className={shouldPulse ? 'status-dot status-dot-pulse' : 'status-dot'} />
      {status}
    </span>
  );
};

export default StatusBadge;
