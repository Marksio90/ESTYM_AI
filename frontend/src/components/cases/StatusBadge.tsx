import { cn } from '@/lib/utils';
import { STATUS_CONFIG, type CaseStatus } from '@/types';

export function StatusBadge({ status }: { status: CaseStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium',
        cfg.bgColor,
        cfg.color
      )}
    >
      <span
        className={cn('h-1.5 w-1.5 rounded-full', cfg.dotColor, cfg.pulse && 'animate-pulse')}
      />
      {cfg.label}
    </span>
  );
}
