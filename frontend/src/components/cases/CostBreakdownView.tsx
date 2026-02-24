'use client';

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { formatCurrency, confidenceLabel, confidenceColor } from '@/lib/utils';
import type { Quote } from '@/types';
import { cn } from '@/lib/utils';

const COLORS = ['#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4', '#f97316'];

export function CostBreakdownView({ quote }: { quote: Quote }) {
  const chartData = quote.cost_breakdown.map(item => ({
    name: item.label,
    value: item.amount,
  }));

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div className="rounded-xl bg-brand-50 p-4">
          <p className="text-xs text-brand-600 font-medium">Łączna wycena</p>
          <p className="mt-1 text-2xl font-bold text-brand-700">
            {formatCurrency(quote.total_cost, quote.currency)}
          </p>
        </div>
        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-xs text-slate-500 font-medium">Marża</p>
          <p className="mt-1 text-2xl font-bold text-slate-700">{quote.margin_percent}%</p>
        </div>
        <div className="rounded-xl bg-slate-50 p-4">
          <p className="text-xs text-slate-500 font-medium">Pewność AI</p>
          <p className={cn('mt-1 text-2xl font-bold', confidenceColor(quote.confidence))}>
            {confidenceLabel(quote.confidence)}
          </p>
        </div>
        {quote.valid_until && (
          <div className="rounded-xl bg-slate-50 p-4">
            <p className="text-xs text-slate-500 font-medium">Ważna do</p>
            <p className="mt-1 text-sm font-semibold text-slate-700">
              {new Date(quote.valid_until).toLocaleDateString('pl-PL')}
            </p>
          </div>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Chart */}
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Rozkład kosztów</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={chartData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value">
                {chartData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => formatCurrency(v, quote.currency)} />
              <Legend formatter={(v) => <span className="text-xs text-slate-600">{v}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Table */}
        <div className="rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">Pozycja</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">Kwota</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500">%</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {quote.cost_breakdown.map((item, i) => (
                <tr key={i} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                      <span className="text-slate-700 font-medium">{item.label}</span>
                    </div>
                    {item.note && <p className="mt-0.5 text-xs text-slate-400 pl-4">{item.note}</p>}
                  </td>
                  <td className="px-4 py-3 text-right font-semibold text-slate-800">
                    {formatCurrency(item.amount, item.currency)}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-500">
                    {((item.amount / quote.total_cost) * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t-2 border-slate-200 bg-slate-50">
                <td className="px-4 py-3 font-bold text-slate-800">Razem</td>
                <td className="px-4 py-3 text-right font-bold text-brand-700">
                  {formatCurrency(quote.total_cost, quote.currency)}
                </td>
                <td className="px-4 py-3 text-right font-bold text-slate-500">100%</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}
