'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Plus, Search, Filter, FolderOpen, ArrowRight, RefreshCw, AlertCircle } from 'lucide-react';
import { getCases } from '@/lib/api';
import { StatusBadge } from '@/components/cases/StatusBadge';
import { TopBar } from '@/components/layout/TopBar';
import { timeAgo, formatDate } from '@/lib/utils';
import type { CaseStatus } from '@/types';

const ALL_STATUSES: CaseStatus[] = ['new', 'analyzing', 'reviewing', 'approved', 'exported', 'failed'];
const STATUS_LABELS: Record<CaseStatus, string> = {
  new: 'Nowe', analyzing: 'Analiza', reviewing: 'Przegląd',
  approved: 'Zatwierdzone', exported: 'ERP', failed: 'Błąd',
};

export default function CasesPage() {
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<CaseStatus | 'all'>('all');

  const { data: cases = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['cases'],
    queryFn: getCases,
    refetchInterval: 15_000,
  });

  const filtered = cases.filter(c => {
    const matchStatus = filterStatus === 'all' || c.status === filterStatus;
    const q = search.toLowerCase();
    const matchSearch = !q
      || c.customer.name.toLowerCase().includes(q)
      || (c.customer.company ?? '').toLowerCase().includes(q)
      || (c.customer.email ?? '').toLowerCase().includes(q)
      || c.id.includes(q);
    return matchStatus && matchSearch;
  });

  const sorted = [...filtered].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  );

  return (
    <>
      <TopBar title="Sprawy" />
      <main className="flex-1 overflow-auto p-6">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-800">Wszystkie sprawy</h2>
            <p className="mt-0.5 text-sm text-slate-500">
              {filtered.length} z {cases.length} spraw
            </p>
          </div>
          <Link
            href="/cases/new"
            className="flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700 transition-colors shadow-sm"
          >
            <Plus className="h-4 w-4" />
            Nowa sprawa
          </Link>
        </div>

        {/* Filters */}
        <div className="mb-4 flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Szukaj po kliencie, firmie, e-mail, ID…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="h-9 w-full rounded-lg border border-slate-200 bg-white pl-9 pr-3 text-sm text-slate-700 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-slate-400" />
            <select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value as CaseStatus | 'all')}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            >
              <option value="all">Wszystkie statusy</option>
              {ALL_STATUSES.map(s => (
                <option key={s} value={s}>{STATUS_LABELS[s]}</option>
              ))}
            </select>
            <button
              onClick={() => refetch()}
              className="flex h-9 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Odśwież
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
          {isLoading && (
            <div className="flex items-center justify-center py-20 text-slate-400">
              <RefreshCw className="mr-2 h-5 w-5 animate-spin" /> Ładowanie…
            </div>
          )}

          {isError && (
            <div className="flex flex-col items-center justify-center gap-2 py-20 text-red-600">
              <AlertCircle className="h-6 w-6" />
              <p className="text-sm font-medium">Błąd połączenia z API</p>
              <p className="text-xs text-slate-400">Upewnij się, że backend jest uruchomiony</p>
            </div>
          )}

          {!isLoading && !isError && sorted.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <FolderOpen className="mb-3 h-10 w-10" />
              <p className="text-sm font-medium">Brak spraw</p>
              <p className="mt-1 text-xs">
                {search || filterStatus !== 'all' ? 'Zmień filtry' : 'Utwórz pierwsze zapytanie'}
              </p>
            </div>
          )}

          {sorted.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500">Klient / Firma</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500">Status</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 hidden md:table-cell">Pliki</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 hidden lg:table-cell">Utworzono</th>
                  <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 hidden xl:table-cell">Aktualizacja</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {sorted.map(c => (
                  <tr key={c.id} className="hover:bg-slate-50 transition-colors group">
                    <td className="px-5 py-3.5">
                      <p className="font-semibold text-slate-800">{c.customer.name}</p>
                      <p className="text-xs text-slate-400">
                        {c.customer.company && <span>{c.customer.company} · </span>}
                        {c.customer.email}
                      </p>
                    </td>
                    <td className="px-5 py-3.5"><StatusBadge status={c.status} /></td>
                    <td className="px-5 py-3.5 text-slate-500 hidden md:table-cell">
                      {c.files.length} plik{c.files.length !== 1 ? 'ów' : ''}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-400 hidden lg:table-cell">
                      {formatDate(c.created_at)}
                    </td>
                    <td className="px-5 py-3.5 text-xs text-slate-400 hidden xl:table-cell">
                      {timeAgo(c.updated_at)}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link
                        href={`/cases/${c.id}`}
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:border-brand-300 hover:text-brand-600 transition-colors"
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
