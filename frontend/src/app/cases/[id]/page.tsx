'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  ArrowLeft, RefreshCw, CheckCircle2, XCircle, Send,
  FileText, Cpu, ClipboardList, DollarSign, Upload,
  AlertCircle, Loader2, Mail, Building2
} from 'lucide-react';
import { getCase, getCaseTechPlan, approveCase, exportToERP } from '@/lib/api';
import { StatusBadge } from '@/components/cases/StatusBadge';
import { WorkflowStepper } from '@/components/cases/WorkflowStepper';
import { PartSpecView } from '@/components/cases/PartSpecView';
import { TechPlanView } from '@/components/cases/TechPlanView';
import { CostBreakdownView } from '@/components/cases/CostBreakdownView';
import { FileDropzone } from '@/components/files/FileDropzone';
import { TopBar } from '@/components/layout/TopBar';
import { formatDate, timeAgo, formatBytes } from '@/lib/utils';
import { cn } from '@/lib/utils';
import type { Quote, PartSpec } from '@/types';

type Tab = 'overview' | 'files' | 'spec' | 'techplan' | 'quote';

const TABS: { key: Tab; label: string; icon: React.ElementType }[] = [
  { key: 'overview',  label: 'Przegląd',     icon: Cpu },
  { key: 'files',     label: 'Pliki',         icon: Upload },
  { key: 'spec',      label: 'Specyfikacja',  icon: FileText },
  { key: 'techplan',  label: 'Plan technol.', icon: ClipboardList },
  { key: 'quote',     label: 'Wycena',        icon: DollarSign },
];

const FILE_TYPE_COLORS: Record<string, string> = {
  pdf: 'bg-red-100 text-red-700', dxf: 'bg-blue-100 text-blue-700',
  dwg: 'bg-blue-100 text-blue-700', step: 'bg-green-100 text-green-700',
  iges: 'bg-purple-100 text-purple-700', stl: 'bg-orange-100 text-orange-700',
  unknown: 'bg-slate-100 text-slate-700',
};

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('overview');
  const [approveNotes, setApproveNotes] = useState('');
  const [showApproveModal, setShowApproveModal] = useState(false);

  const { data: c, isLoading, isError, refetch } = useQuery({
    queryKey: ['case', id],
    queryFn: () => getCase(id),
    refetchInterval: (q) => q.state.data?.status === 'ANALYZING' ? 5000 : 30_000,
  });

  const { data: techPlanData } = useQuery({
    queryKey: ['techplan', id],
    queryFn: () => getCaseTechPlan(id),
    enabled: !!c && ['REVIEW', 'APPROVED', 'EXPORTED_TO_ERP'].includes(c.status),
    retry: false,
  });

  const approveMutation = useMutation({
    mutationFn: (approved: boolean) =>
      approveCase(id, { approved, notes: approveNotes || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['case', id] });
      qc.invalidateQueries({ queryKey: ['cases'] });
      setShowApproveModal(false);
    },
  });

  const exportMutation = useMutation({
    mutationFn: () => exportToERP(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['case', id] }),
  });

  if (isLoading) {
    return (
      <>
        <TopBar title="Ładowanie…" />
        <main className="flex flex-1 items-center justify-center py-32 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin" />
        </main>
      </>
    );
  }

  if (isError || !c) {
    return (
      <>
        <TopBar title="Błąd" />
        <main className="flex flex-1 flex-col items-center justify-center gap-3 py-32 text-red-600">
          <AlertCircle className="h-10 w-10" />
          <p className="font-medium">Nie znaleziono sprawy</p>
          <Link href="/cases" className="text-sm text-brand-600 hover:underline">← Wróć do listy</Link>
        </main>
      </>
    );
  }

  const techPlan = techPlanData?.tech_plan;
  // Extract parts from workflow state if available
  const workflowState = c as unknown as Record<string, unknown>;
  const spec = (workflowState?.part_specs as PartSpec[] | undefined)?.[0];
  const quote = (workflowState?.quotes as Quote[] | undefined)?.[0];

  return (
    <>
      <TopBar title={`Sprawa — ${c.customer.name}`} />
      <main className="flex-1 overflow-auto">
        {/* Header */}
        <div className="border-b border-slate-200 bg-white px-6 py-4">
          <div className="mb-3 flex items-center gap-3">
            <Link href="/cases" className="text-slate-500 hover:text-slate-700 transition-colors">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <h2 className="text-lg font-bold text-slate-800">{c.customer.name}</h2>
            <StatusBadge status={c.status} />
            {c.risk_level && (
              <span className={cn('text-xs font-medium px-2 py-0.5 rounded-full', {
                'bg-red-100 text-red-700': c.risk_level === 'HIGH',
                'bg-amber-100 text-amber-700': c.risk_level === 'MEDIUM',
                'bg-green-100 text-green-700': c.risk_level === 'LOW',
              })}>
                Ryzyko: {c.risk_level === 'HIGH' ? 'Wysokie' : c.risk_level === 'MEDIUM' ? 'Średnie' : 'Niskie'}
              </span>
            )}
            <button onClick={() => refetch()} className="ml-auto text-slate-400 hover:text-slate-600 transition-colors">
              <RefreshCw className={cn('h-4 w-4', c.status === 'ANALYZING' && 'animate-spin')} />
            </button>
          </div>

          <div className="mb-4 rounded-xl bg-slate-50 px-4 py-4">
            <WorkflowStepper status={c.status} />
          </div>

          {/* Missing info alert */}
          {c.missing_info_questions && c.missing_info_questions.length > 0 && (
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
              <p className="text-xs font-semibold text-amber-800 mb-1.5">
                AI potrzebuje dodatkowych informacji ({c.missing_info_questions.length}):
              </p>
              <ul className="space-y-0.5">
                {c.missing_info_questions.map((q, i) => (
                  <li key={i} className="text-xs text-amber-700">• {q}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2">
            {c.status === 'REVIEW' && (
              <>
                <button
                  onClick={() => setShowApproveModal(true)}
                  className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 transition-colors"
                >
                  <CheckCircle2 className="h-4 w-4" /> Zatwierdź wycenę
                </button>
                <button
                  onClick={() => approveMutation.mutate(false)}
                  disabled={approveMutation.isPending}
                  className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 hover:bg-red-100 transition-colors"
                >
                  <XCircle className="h-4 w-4" /> Odrzuć
                </button>
              </>
            )}
            {c.status === 'APPROVED' && (
              <button
                onClick={() => exportMutation.mutate()}
                disabled={exportMutation.isPending}
                className="flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700 transition-colors"
              >
                {exportMutation.isPending
                  ? <Loader2 className="h-4 w-4 animate-spin" />
                  : <Send className="h-4 w-4" />}
                Eksportuj do ERP
              </button>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="border-b border-slate-200 bg-white px-6">
          <div className="flex">
            {TABS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={cn(
                  'flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors',
                  tab === key
                    ? 'border-brand-600 text-brand-700'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content */}
        <div className="p-6">
          {tab === 'overview' && (
            <div className="grid gap-4 lg:grid-cols-3">
              {/* Customer */}
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <h3 className="mb-4 text-xs font-bold uppercase tracking-wide text-slate-400">Klient</h3>
                <div className="space-y-3">
                  <div className="flex items-start gap-2 text-sm">
                    <Building2 className="h-4 w-4 text-slate-400 mt-0.5" />
                    <span className="font-medium text-slate-800">{c.customer.name}</span>
                  </div>
                  {c.customer.contact_email && (
                    <div className="flex items-center gap-2 text-sm">
                      <Mail className="h-4 w-4 text-slate-400" />
                      <a href={`mailto:${c.customer.contact_email}`} className="text-brand-600 hover:underline text-xs">{c.customer.contact_email}</a>
                    </div>
                  )}
                  {c.email_subject && (
                    <div className="rounded-lg bg-slate-50 p-3">
                      <p className="text-xs text-slate-500 font-medium mb-1">Temat</p>
                      <p className="text-sm text-slate-700">{c.email_subject}</p>
                    </div>
                  )}
                  {c.requested_qty && (
                    <p className="text-sm text-slate-600">
                      Ilość: <strong>{c.requested_qty} szt.</strong>
                    </p>
                  )}
                  {c.product_family_guess && (
                    <p className="text-sm text-slate-600">
                      Rodzina: <strong>{c.product_family_guess}</strong>
                    </p>
                  )}
                </div>
              </div>

              {/* Timeline */}
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <h3 className="mb-4 text-xs font-bold uppercase tracking-wide text-slate-400">Oś czasu</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Utworzono</span>
                    <span className="font-medium text-slate-700">{formatDate(c.created_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Aktualizacja</span>
                    <span className="font-medium text-slate-700">{timeAgo(c.updated_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">ID</span>
                    <span className="font-mono text-xs text-slate-400">{c.case_id.slice(0, 12)}…</span>
                  </div>
                </div>
              </div>

              {/* Files summary */}
              <div className="rounded-xl border border-slate-200 bg-white p-5">
                <h3 className="mb-4 text-xs font-bold uppercase tracking-wide text-slate-400">Pliki ({c.files.length})</h3>
                {c.files.length === 0 ? (
                  <p className="text-sm text-slate-400">Brak plików</p>
                ) : (
                  <ul className="space-y-2">
                    {c.files.slice(0, 5).map(f => (
                      <li key={f.file_id} className="flex items-center gap-2 text-xs">
                        <span className={`rounded px-1.5 py-0.5 font-medium uppercase ${FILE_TYPE_COLORS[f.detected_type] ?? 'bg-slate-100 text-slate-700'}`}>
                          {f.detected_type}
                        </span>
                        <span className="truncate text-slate-700">{f.filename}</span>
                        {f.file_size_bytes && <span className="ml-auto text-slate-400">{formatBytes(f.file_size_bytes)}</span>}
                      </li>
                    ))}
                    {c.files.length > 5 && (
                      <li className="text-xs text-slate-400">+ {c.files.length - 5} więcej…</li>
                    )}
                  </ul>
                )}
              </div>
            </div>
          )}

          {tab === 'files' && (
            <div className="max-w-2xl space-y-4">
              <FileDropzone caseId={c.case_id} onUploaded={() => refetch()} />
              {c.files.length > 0 && (
                <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-100 bg-slate-50">
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">Plik</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">Typ</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">Rozmiar</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {c.files.map(f => (
                        <tr key={f.file_id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-medium text-slate-800 truncate max-w-xs">{f.filename}</td>
                          <td className="px-4 py-3">
                            <span className={`rounded px-1.5 py-0.5 text-xs font-medium uppercase ${FILE_TYPE_COLORS[f.detected_type] ?? 'bg-slate-100 text-slate-700'}`}>
                              {f.detected_type}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-500 text-xs">
                            {f.file_size_bytes ? formatBytes(f.file_size_bytes) : '—'}
                          </td>
                          <td className="px-4 py-3 text-xs">
                            <span className={cn('rounded-full px-2 py-0.5 font-medium', {
                              'bg-green-100 text-green-700': f.conversion_status === 'OK',
                              'bg-amber-100 text-amber-700': f.conversion_status === 'PENDING',
                              'bg-red-100 text-red-700':    f.conversion_status === 'FAILED',
                            })}>
                              {f.conversion_status === 'OK' ? 'Gotowy' : f.conversion_status === 'PENDING' ? 'W kolejce' : 'Błąd'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {tab === 'spec' && (
            spec
              ? <PartSpecView spec={spec} />
              : <EmptyTab icon={FileText} message="Specyfikacja zostanie wygenerowana po zakończeniu analizy AI." />
          )}

          {tab === 'techplan' && (
            techPlan
              ? <TechPlanView plan={techPlan} />
              : <EmptyTab icon={ClipboardList} message="Plan technologiczny zostanie wygenerowany po analizie." />
          )}

          {tab === 'quote' && (
            quote
              ? <CostBreakdownView quote={quote} />
              : <EmptyTab icon={DollarSign} message="Wycena zostanie wygenerowana po ukończeniu analizy i planu technologicznego." />
          )}
        </div>
      </main>

      {/* Approve modal */}
      {showApproveModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-2xl mx-4">
            <h3 className="text-lg font-bold text-slate-800">Zatwierdź wycenę</h3>
            <p className="mt-1 text-sm text-slate-500">Opcjonalnie dodaj uwagi przed zatwierdzeniem.</p>
            <textarea
              value={approveNotes}
              onChange={e => setApproveNotes(e.target.value)}
              rows={3}
              placeholder="Uwagi do zatwierdzenia…"
              className="mt-4 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
            />
            <div className="mt-4 flex gap-3">
              <button
                onClick={() => approveMutation.mutate(true)}
                disabled={approveMutation.isPending}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-green-600 py-2.5 text-sm font-semibold text-white hover:bg-green-700 transition-colors"
              >
                {approveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                Zatwierdź
              </button>
              <button
                onClick={() => setShowApproveModal(false)}
                className="flex-1 rounded-lg border border-slate-200 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Anuluj
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function EmptyTab({ icon: Icon, message }: { icon: React.ElementType; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 py-20 text-center">
      <Icon className="mb-3 h-10 w-10 text-slate-300" />
      <p className="text-sm font-medium text-slate-500">{message}</p>
    </div>
  );
}
