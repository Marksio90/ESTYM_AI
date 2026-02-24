'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ArrowLeft, Loader2, CheckCircle2, AlertTriangle, FileText } from 'lucide-react';
import Link from 'next/link';
import { createCase } from '@/lib/api';
import { FileDropzone } from '@/components/files/FileDropzone';
import { TopBar } from '@/components/layout/TopBar';
import type { CreateCaseResponse } from '@/types';

const schema = z.object({
  customer_name:  z.string().min(2, 'Podaj imię i nazwisko lub nazwę firmy'),
  customer_email: z.string().email('Nieprawidłowy adres e-mail'),
  email_subject:  z.string().min(3, 'Podaj temat zapytania'),
  email_body:     z.string().min(10, 'Opisz zapytanie (min. 10 znaków)'),
  requested_qty:  z.coerce.number().int().min(1).optional().or(z.literal('')),
  notes:          z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function NewCasePage() {
  const qc = useQueryClient();
  const [result, setResult] = useState<CreateCaseResponse | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      createCase({
        customer_name:  data.customer_name,
        customer_email: data.customer_email,
        email_subject:  data.email_subject,
        email_body:     data.email_body,
        requested_qty:  data.requested_qty ? Number(data.requested_qty) : undefined,
        notes:          data.notes || undefined,
      }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['cases'] });
      setResult(res);
    },
  });

  const onSubmit = handleSubmit(data => mutation.mutate(data));

  // ── Success screen ─────────────────────────────────────────────────────────
  if (result) {
    return (
      <>
        <TopBar title="Nowa sprawa" />
        <main className="flex-1 p-6">
          <div className="mx-auto max-w-2xl space-y-4">
            {/* Success banner */}
            <div className="rounded-2xl border border-green-200 bg-green-50 p-6">
              <div className="flex items-start gap-4">
                <CheckCircle2 className="h-8 w-8 text-green-500 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <h2 className="text-lg font-bold text-green-800">Sprawa utworzona!</h2>
                  <p className="mt-1 text-sm text-green-700">
                    ID: <span className="font-mono font-semibold">{result.case_id}</span>
                  </p>
                  {result.product_family && (
                    <p className="mt-0.5 text-sm text-green-700">
                      Rodzina produktu: <strong>{result.product_family}</strong>
                      {result.risk_level && <span> · Ryzyko: <strong>{result.risk_level}</strong></span>}
                    </p>
                  )}
                </div>
              </div>

              {/* Missing info questions */}
              {result.missing_info && result.missing_info.length > 0 && (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <p className="text-sm font-semibold text-amber-800">
                      AI wykryło brakujące informacje ({result.missing_info.length}):
                    </p>
                  </div>
                  <ul className="space-y-1">
                    {result.missing_info.map((q, i) => (
                      <li key={i} className="text-sm text-amber-700 flex items-start gap-1.5">
                        <span className="mt-1 h-1.5 w-1.5 rounded-full bg-amber-500 flex-shrink-0" />
                        {q}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* File upload */}
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <h3 className="mb-1 text-sm font-bold text-slate-700">Dodaj pliki CAD / PDF</h3>
              <p className="mb-4 text-xs text-slate-400">
                Przeciągnij rysunki techniczne (DXF, STEP, PDF) — AI przetworzy je automatycznie.
              </p>
              <FileDropzone
                caseId={result.case_id}
                onUploaded={(fileId) => setUploadedFiles(prev => [...prev, fileId])}
              />
              {uploadedFiles.length > 0 && (
                <p className="mt-3 text-xs text-green-600 font-medium">
                  ✓ Przesłano {uploadedFiles.length} plik(ów) — analiza AI rozpoczęta
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <Link
                href={`/cases/${result.case_id}`}
                className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-brand-600 py-3 text-sm font-semibold text-white hover:bg-brand-700 transition-colors shadow-sm"
              >
                <FileText className="h-4 w-4" />
                Otwórz sprawę
              </Link>
              <Link
                href="/cases"
                className="flex-1 flex items-center justify-center rounded-xl border border-slate-200 py-3 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
              >
                Lista spraw
              </Link>
            </div>
          </div>
        </main>
      </>
    );
  }

  // ── Form ───────────────────────────────────────────────────────────────────
  return (
    <>
      <TopBar title="Nowa sprawa" />
      <main className="flex-1 overflow-auto p-6">
        <div className="mx-auto max-w-2xl">
          <Link
            href="/cases"
            className="mb-6 inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" /> Wróć do listy
          </Link>

          <h2 className="mb-1 text-xl font-bold text-slate-800">Nowe zapytanie ofertowe</h2>
          <p className="mb-6 text-sm text-slate-500">
            Wprowadź dane klienta i treść zapytania. AI automatycznie sklasyfikuje produkt i wykryje brakujące informacje.
          </p>

          <form onSubmit={onSubmit} className="space-y-5">
            {/* Customer */}
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-slate-400">Dane klienta</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">
                    Klient / Firma <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('customer_name')}
                    placeholder="Jan Kowalski / Kowalski sp. z o.o."
                    className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {errors.customer_name && <p className="mt-1 text-xs text-red-500">{errors.customer_name.message}</p>}
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">
                    E-mail klienta <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('customer_email')}
                    type="email"
                    placeholder="jan@kowalski.pl"
                    className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {errors.customer_email && <p className="mt-1 text-xs text-red-500">{errors.customer_email.message}</p>}
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">
                    Ilość (szt.)
                  </label>
                  <input
                    {...register('requested_qty')}
                    type="number"
                    min={1}
                    placeholder="np. 100"
                    className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              </div>
            </div>

            {/* Email content */}
            <div className="rounded-xl border border-slate-200 bg-white p-5">
              <h3 className="mb-4 text-xs font-bold uppercase tracking-widest text-slate-400">Treść zapytania</h3>
              <div className="space-y-4">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">
                    Temat <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('email_subject')}
                    placeholder="Zapytanie ofertowe — wspornik stalowy S235"
                    className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {errors.email_subject && <p className="mt-1 text-xs text-red-500">{errors.email_subject.message}</p>}
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">
                    Treść zapytania <span className="text-red-500">*</span>
                  </label>
                  <textarea
                    {...register('email_body')}
                    rows={5}
                    placeholder="Dzień dobry,&#10;Proszę o wycenę 100 szt. wspornika stalowego wg. załączonego rysunku.&#10;Materiał: S235, grubość 3mm, cynkowanie ogniowe.&#10;Termin realizacji: 4 tygodnie."
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
                  />
                  {errors.email_body && <p className="mt-1 text-xs text-red-500">{errors.email_body.message}</p>}
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">Dodatkowe uwagi</label>
                  <textarea
                    {...register('notes')}
                    rows={2}
                    placeholder="Uwagi wewnętrzne dla operatora…"
                    className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 py-3.5 text-sm font-bold text-white hover:bg-brand-700 disabled:opacity-60 transition-colors shadow-sm"
            >
              {mutation.isPending
                ? <><Loader2 className="h-4 w-4 animate-spin" /> Przetwarzanie przez AI…</>
                : 'Utwórz sprawę i uruchom AI'}
            </button>

            {mutation.isError && (
              <p className="text-center text-sm text-red-600">
                Błąd: {(mutation.error as Error).message}
              </p>
            )}
          </form>
        </div>
      </main>
    </>
  );
}
