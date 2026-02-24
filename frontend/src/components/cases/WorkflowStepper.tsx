import { cn } from '@/lib/utils';
import { CheckCircle2, Circle, Clock, AlertCircle, Loader2 } from 'lucide-react';
import type { CaseStatus } from '@/types';

interface Step {
  key: CaseStatus | string;
  label: string;
  description: string;
}

const STEPS: Step[] = [
  { key: 'new',       label: 'Przyjęto',        description: 'Zapytanie zarejestrowane' },
  { key: 'analyzing', label: 'Analiza AI',       description: 'Przetwarzanie rysunków i plików' },
  { key: 'reviewing', label: 'Przegląd',         description: 'Weryfikacja przez operatora' },
  { key: 'approved',  label: 'Zatwierdzone',     description: 'Wycena zaakceptowana' },
  { key: 'exported',  label: 'ERP',              description: 'Wyeksportowane do systemu ERP' },
];

const ORDER: Record<string, number> = {
  new: 0, analyzing: 1, reviewing: 2, approved: 3, exported: 4, failed: 5,
};

function StepIcon({ state }: { state: 'done' | 'active' | 'pending' | 'error' }) {
  if (state === 'done')    return <CheckCircle2 className="h-5 w-5 text-green-500" />;
  if (state === 'active')  return <Loader2      className="h-5 w-5 text-brand-500 animate-spin" />;
  if (state === 'error')   return <AlertCircle  className="h-5 w-5 text-red-500" />;
  return <Circle className="h-5 w-5 text-slate-300" />;
}

export function WorkflowStepper({ status }: { status: CaseStatus }) {
  const currentIdx = ORDER[status] ?? 0;
  const isFailed = status === 'failed';

  return (
    <div className="flex items-start gap-0">
      {STEPS.map((step, idx) => {
        const stepIdx = ORDER[step.key] ?? idx;
        const state = isFailed && stepIdx === currentIdx
          ? 'error'
          : stepIdx < currentIdx ? 'done'
          : stepIdx === currentIdx ? 'active'
          : 'pending';
        const isLast = idx === STEPS.length - 1;

        return (
          <div key={step.key} className="flex flex-1 flex-col items-center">
            <div className="flex w-full items-center">
              {/* Connector left */}
              <div className={cn('h-0.5 flex-1', idx === 0 ? 'invisible' : state === 'done' || (stepIdx <= currentIdx && state !== 'pending') ? 'bg-green-400' : 'bg-slate-200')} />
              {/* Icon */}
              <StepIcon state={state} />
              {/* Connector right */}
              <div className={cn('h-0.5 flex-1', isLast ? 'invisible' : state === 'done' ? 'bg-green-400' : 'bg-slate-200')} />
            </div>
            <div className="mt-2 text-center">
              <p className={cn('text-xs font-semibold', state === 'done' ? 'text-green-700' : state === 'active' ? 'text-brand-700' : state === 'error' ? 'text-red-700' : 'text-slate-400')}>
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
