import { formatMinutes } from '@/lib/utils';
import { OPERATION_LABELS, type TechPlan } from '@/types';
import { Clock, Wrench, Users } from 'lucide-react';

const OP_COLORS: Record<string, string> = {
  laser_cutting: 'bg-red-100 text-red-700',
  plasma_cutting: 'bg-orange-100 text-orange-700',
  bending: 'bg-blue-100 text-blue-700',
  welding: 'bg-yellow-100 text-yellow-700',
  turning: 'bg-purple-100 text-purple-700',
  milling: 'bg-pink-100 text-pink-700',
  grinding: 'bg-gray-100 text-gray-700',
  drilling: 'bg-cyan-100 text-cyan-700',
  assembly: 'bg-green-100 text-green-700',
  surface_treatment: 'bg-teal-100 text-teal-700',
  quality_control: 'bg-indigo-100 text-indigo-700',
  other: 'bg-slate-100 text-slate-700',
};

export function TechPlanView({ plan }: { plan: TechPlan }) {
  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
          <div className="rounded-lg bg-brand-100 p-2"><Clock className="h-4 w-4 text-brand-600" /></div>
          <div>
            <p className="text-xs text-slate-500">Czas łączny</p>
            <p className="text-sm font-bold text-slate-800">{formatMinutes(plan.total_time_min)}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
          <div className="rounded-lg bg-green-100 p-2"><Wrench className="h-4 w-4 text-green-600" /></div>
          <div>
            <p className="text-xs text-slate-500">Operacji</p>
            <p className="text-sm font-bold text-slate-800">{plan.operations.length}</p>
          </div>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
          <div className="rounded-lg bg-amber-100 p-2"><Users className="h-4 w-4 text-amber-600" /></div>
          <div>
            <p className="text-xs text-slate-500">Partia</p>
            <p className="text-sm font-bold text-slate-800">{plan.batch_size} szt.</p>
          </div>
        </div>
      </div>

      {/* Operations list */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">#</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">Operacja</th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">Maszyna</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">Przygotowanie</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">Na szt.</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">Pracownicy</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {plan.operations.map((op, i) => (
              <tr key={op.id} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 text-slate-400 font-mono text-xs">{i + 1}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${OP_COLORS[op.operation_type] ?? 'bg-slate-100 text-slate-700'}`}>
                      {OPERATION_LABELS[op.operation_type] ?? op.operation_type}
                    </span>
                    <span className="text-slate-700 font-medium">{op.name}</span>
                  </div>
                  {op.notes && <p className="mt-0.5 text-xs text-slate-400">{op.notes}</p>}
                </td>
                <td className="px-4 py-3 text-slate-600">{op.machine ?? '—'}</td>
                <td className="px-4 py-3 text-right text-slate-600">{formatMinutes(op.time_setup_min)}</td>
                <td className="px-4 py-3 text-right font-semibold text-slate-800">{formatMinutes(op.time_per_unit_min)}</td>
                <td className="px-4 py-3 text-right text-slate-600">{op.labor_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
