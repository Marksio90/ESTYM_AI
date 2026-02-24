'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import {
  FolderOpen, CheckCircle2, Clock, TrendingUp,
  Plus, ArrowRight, RefreshCw, AlertCircle
} from 'lucide-react';
import { getCases } from '@/lib/api';
import { StatusBadge } from '@/components/cases/StatusBadge';
import { TopBar } from '@/components/layout/TopBar';
import { timeAgo, formatCurrency } from '@/lib/utils';
import type { CaseStatus } from '@/types';

function StatCard({ icon: Icon, label, value, color, sub }: {
  icon: React.ElementType; label: string; value: number | string;
  color: string; sub?: string;
}) {
  const bg = color.replace('text-', 'bg-').replace('-700', '-100').replace('-600', '-100');
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500">{label}</p>
          <p className={`mt-1 text-3xl font-bold ${color}`}>{value}</p>
          {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
        </div>
        <div className={`rounded-xl p-3 ${bg}`}>
          <Icon className={`h-5 w-5 ${color}`} />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { data: cases = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['cases'],
    queryFn: getCases,
    refetchInterval: 15_000,
  });

  const byStatus = (s: CaseStatus) => cases.filter(c => c.status === s).length;

  const recent = [...cases]
    .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    .slice(0, 8);

  const ALL_STATUSES: CaseStatus[] = ['NEW','ANALYZING','AWAITING_INFO','CALCULATED','REVIEW','APPROVED','EXPORTED_TO_ERP','REJECTED'];
  const STATUS_COLORS: Record<CaseStatus, string> = {
    NEW: 'bg-blue-400', ANALYZING: 'bg-amber-400', AWAITING_INFO: 'bg-orange-400',
    CALCULATED: 'bg-cyan-400', REVIEW: 'bg-purple-400', APPROVED: 'bg-green-500',
    EXPORTED_TO_ERP: 'bg-teal-500', REJECTED: 'bg-red-400',
  };

  return (
    <>
      <TopBar title="Pulpit" />
      <main className="flex-1 overflow-auto p-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-800">Przegląd platformy</h2>
            <p className="mt-0.5 text-sm text-slate-500">{cases.length} spraw łącznie</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => refetch()}
              className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
            >
              <RefreshCw className="h-4 w-4" /> Odśwież
            </button>
            <Link
              href="/cases/new"
              className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 transition-colors shadow-sm"
            >
              <Plus className="h-4 w-4" /> Nowe zapytanie
            </Link>
          </div>
        </div>

        {/* Stats */}
        <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatCard icon={FolderOpen}   label="Wszystkich spraw"  value={cases.length}  color="text-brand-700"  sub="od początku" />
          <StatCard icon={Clock}        label="Do przeglądu"      value={byStatus('REVIEW')}     color="text-purple-700" sub="czeka na operatora" />
          <StatCard icon={TrendingUp}   label="W analizie AI"     value={byStatus('ANALYZING')}  color="text-amber-700"  sub="przetwarzanie" />
          <StatCard icon={CheckCircle2} label="Zatwierdzone"      value={byStatus('APPROVED') + byStatus('EXPORTED_TO_ERP')} color="text-green-700" sub="gotowe / wyeksportowane" />
        </div>

        {/* Status bar */}
        {cases.length > 0 && (
          <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
            <p className="mb-3 text-sm font-semibold text-slate-700">Rozkład statusów</p>
            <div className="flex h-3 w-full overflow-hidden rounded-full">
              {ALL_STATUSES.map(s => {
                const pct = (byStatus(s) / cases.length) * 100;
                return pct > 0 ? (
                  <div key={s} style={{ width: `${pct}%` }} className={STATUS_COLORS[s]} />
                ) : null;
              })}
            </div>
            <div className="mt-3 flex flex-wrap gap-3">
              {ALL_STATUSES.map(s => byStatus(s) > 0 && (
                <span key={s} className="flex items-center gap-1.5 text-xs text-slate-500">
                  <StatusBadge status={s} />
                  <span>{byStatus(s)}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Recent cases */}
        <div className="rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <h3 className="text-sm font-semibold text-slate-800">Ostatnie sprawy</h3>
            <Link href="/cases" className="flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700">
              Pokaż wszystkie <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          {isLoading && (
            <div className="flex items-center justify-center py-16 text-slate-400">
              <RefreshCw className="mr-2 h-5 w-5 animate-spin" /> Ładowanie…
            </div>
          )}
          {isError && (
            <div className="flex items-center justify-center gap-2 py-16 text-red-600">
              <AlertCircle className="h-5 w-5" />
              Nie można połączyć się z API. Czy backend działa?
            </div>
          )}
          {!isLoading && !isError && recent.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <FolderOpen className="mb-3 h-10 w-10" />
              <p className="text-sm font-medium">Brak spraw</p>
              <p className="mt-1 text-xs">Utwórz pierwsze zapytanie klikając &quot;Nowe zapytanie&quot;</p>
            </div>
          )}

          {recent.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-50">
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400">Klient</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400">Status</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400 hidden md:table-cell">Pliki</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-400 hidden lg:table-cell">Aktualizacja</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {recent.map(c => (
                  <tr key={c.case_id} className="hover:bg-slate-50 transition-colors group">
                    <td className="px-5 py-3">
                      <p className="font-medium text-slate-800">{c.customer.name}</p>
                      {c.email_subject && <p className="text-xs text-slate-400 truncate max-w-xs">{c.email_subject}</p>}
                    </td>
                    <td className="px-5 py-3"><StatusBadge status={c.status} /></td>
                    <td className="px-5 py-3 text-slate-500 hidden md:table-cell">
                      {c.files.length} plik{c.files.length !== 1 ? 'ów' : ''}
                    </td>
                    <td className="px-5 py-3 text-slate-400 text-xs hidden lg:table-cell">{timeAgo(c.updated_at)}</td>
                    <td className="px-5 py-3">
                      <Link
                        href={`/cases/${c.case_id}`}
                        className="invisible group-hover:visible flex items-center gap-1 text-xs font-medium text-brand-600"
                      >
                        Otwórz <ArrowRight className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </>
  );
}
