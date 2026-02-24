import { formatSeconds } from '@/lib/utils';
import { OPERATION_LABELS, type TechPlan } from '@/types';
import { Clock, Wrench, Users } from 'lucide-react';

const OP_COLORS: Record<string, string> = {
  CUTTING:         'bg-red-100 text-red-700',
  WIRE_BENDING:    'bg-blue-100 text-blue-700',
  SHEET_BENDING:   'bg-blue-100 text-blue-700',
  TUBE_BENDING:    'bg-indigo-100 text-indigo-700',
  SPOT_WELDING:    'bg-yellow-100 text-yellow-700',
  MIG_WELDING:     'bg-amber-100 text-amber-700',
  TIG_WELDING:     'bg-orange-100 text-orange-700',
  ROBOTIC_WELDING: 'bg-yellow-100 text-yellow-800',
  GRINDING:        'bg-gray-100 text-gray-700',
  DRILLING:        'bg-cyan-100 text-cyan-700',
  THREADING:       'bg-cyan-100 text-cyan-800',
  DEBURRING:       'bg-slate-100 text-slate-700',
  GALVANIZING:     'bg-teal-100 text-teal-700',
  POWDER_COATING:  'bg-purple-100 text-purple-700',
  PAINTING:        'bg-pink-100 text-pink-700',
  ASSEMBLY:        'bg-green-100 text-green-700',
  QA_INSPECTION:   'bg-indigo-100 text-indigo-700',
  PACKAGING:       'bg-slate-100 text-slate-600',
  DEGREASING:      'bg-slate-100 text-slate-700',
  FIXTURE_SETUP:   'bg-rose-100 text-rose-700',
};

export function TechPlanView({ plan }: { plan: TechPlan }) {
  const totalSec = plan.total_time_with_overhead_sec ?? plan.total_cycle_time_sec;
  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-3">
        <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4">
          <div className="rounded-lg bg-brand-100 p-2"><Clock className="h-4 w-4 text-brand-600" /></div>
          <div>
            <p className="text-xs text-slate-500">Czas łączny</p>
            <p className="text-sm font-bold text-slate-800">{formatSeconds(totalSec)}</p>
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
            <p className="text-sm font-bold text-slate-800">{plan.batch_size ?? '—'} szt.</p>
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
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">Gniazdo</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">Przygotowanie</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">Na szt.</th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">Pracownicy</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {plan.operations.map((op, i) => (
              <tr key={op.op_code} className="hover:bg-slate-50 transition-colors">
                <td className="px-4 py-3 text-slate-400 font-mono text-xs">{op.op_code || i + 1}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${OP_COLORS[op.op_type] ?? 'bg-slate-100 text-slate-700'}`}>
                      {OPERATION_LABELS[op.op_type] ?? op.op_type}
                    </span>
                    <span className="text-slate-700 font-medium">{op.op_name}</span>
                  </div>
                  {op.notes && op.notes.length > 0 && (
                    <p className="mt-0.5 text-xs text-slate-400">{op.notes.join('; ')}</p>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-600">{op.workcenter_name ?? op.workcenter ?? '—'}</td>
                <td className="px-4 py-3 text-right text-slate-600">{formatSeconds(op.setup_time_sec)}</td>
                <td className="px-4 py-3 text-right font-semibold text-slate-800">{formatSeconds(op.cycle_time_sec)}</td>
                <td className="px-4 py-3 text-right text-slate-600">{op.operator_count ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Operator notes */}
      {plan.notes_for_operator && plan.notes_for_operator.length > 0 && (
        <div className="rounded-xl border border-blue-100 bg-blue-50 p-4">
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-blue-700">Uwagi dla operatora</p>
          <ul className="space-y-1">
            {plan.notes_for_operator.map((n, i) => (
              <li key={i} className="text-xs text-blue-800">• {n}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
