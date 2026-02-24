import { cn } from '@/lib/utils';
import { CheckCircle2, Circle, AlertCircle, Loader2 } from 'lucide-react';
import type { CaseStatus } from '@/types';

interface Step { idx: number; label: string; description: string }

const STEPS: Step[] = [
  { idx: 0, label: 'Przyjęto',     description: 'Zapytanie zarejestrowane' },
  { idx: 1, label: 'Analiza AI',   description: 'Przetwarzanie rysunków' },
  { idx: 2, label: 'Kalkulacja',   description: 'Wycena wygenerowana' },
  { idx: 3, label: 'Przegląd',     description: 'Weryfikacja operatora' },
  { idx: 4, label: 'Finalizacja',  description: 'Zatwierdzono / ERP' },
];

const STATUS_IDX: Partial<Record<CaseStatus, number>> = {
  NEW: 0, ANALYZING: 1, AWAITING_INFO: 2, CALCULATED: 2,
  REVIEW: 3, APPROVED: 4, EXPORTED_TO_ERP: 4,
};

function StepIcon({ state }: { state: 'done' | 'active' | 'pending' | 'error' }) {
  if (state === 'done')   return <CheckCircle2 className="h-5 w-5 text-green-500" />;
  if (state === 'active') return <Loader2      className="h-5 w-5 text-brand-500 animate-spin" />;
  if (state === 'error')  return <AlertCircle  className="h-5 w-5 text-red-500" />;
  return <Circle className="h-5 w-5 text-slate-300" />;
}

export function WorkflowStepper({ status }: { status: CaseStatus }) {
  const currentIdx = STATUS_IDX[status] ?? 0;
  const isRejected = status === 'REJECTED';

  return (
    <div className="flex items-start gap-0">
      {STEPS.map((step, i) => {
        const state = isRejected && step.idx === currentIdx
          ? 'error'
          : step.idx < currentIdx ? 'done'
          : step.idx === currentIdx ? 'active'
          : 'pending';
        const isLast = i === STEPS.length - 1;

        return (
          <div key={step.idx} className="flex flex-1 flex-col items-center">
            <div className="flex w-full items-center">
              <div className={cn('h-0.5 flex-1', i === 0 ? 'invisible' : step.idx <= currentIdx ? 'bg-green-400' : 'bg-slate-200')} />
              <StepIcon state={state} />
              <div className={cn('h-0.5 flex-1', isLast ? 'invisible' : step.idx < currentIdx ? 'bg-green-400' : 'bg-slate-200')} />
            </div>
            <div className="mt-2 text-center">
              <p className={cn('text-xs font-semibold',
                state === 'done'   ? 'text-green-700'  :
                state === 'active' ? 'text-brand-700'  :
                state === 'error'  ? 'text-red-700'    : 'text-slate-400'
              )}>
                {step.label}
              </p>
              <p className="mt-0.5 text-[10px] text-slate-400 hidden sm:block">{step.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
