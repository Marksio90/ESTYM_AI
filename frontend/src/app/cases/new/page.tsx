'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ArrowLeft, Loader2, CheckCircle2, Upload } from 'lucide-react';
import Link from 'next/link';
import { createCase } from '@/lib/api';
import { FileDropzone } from '@/components/files/FileDropzone';
import { TopBar } from '@/components/layout/TopBar';

const schema = z.object({
  name:    z.string().min(2, 'Podaj imię i nazwisko'),
  company: z.string().optional(),
  email:   z.string().email('Nieprawidłowy adres e-mail').optional().or(z.literal('')),
  phone:   z.string().optional(),
  notes:   z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function NewCasePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [caseId, setCaseId] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      createCase({
        customer: {
          name: data.name,
          company: data.company || undefined,
          email: data.email || undefined,
          phone: data.phone || undefined,
        },
        notes: data.notes || undefined,
      }),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ['cases'] });
      setCaseId(c.id);
    },
  });

  const onSubmit = handleSubmit(data => mutation.mutate(data));

  const handleUploaded = (fileId: string) => {
    setUploadedFiles(prev => [...prev, fileId]);
  };

  if (caseId) {
    return (
      <>
        <TopBar title="Nowa sprawa" />
        <main className="flex-1 p-6">
          <div className="mx-auto max-w-xl">
            <div className="rounded-2xl border border-green-200 bg-green-50 p-8 text-center">
              <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-green-500" />
              <h2 className="text-xl font-bold text-green-800">Sprawa utworzona!</h2>
              <p className="mt-2 text-sm text-green-700">
                {uploadedFiles.length > 0
                  ? `Przesłano ${uploadedFiles.length} plik(ów). Analiza AI rozpoczęta.`
                  : 'Możesz teraz dodać pliki i uruchomić analizę.'}
              </p>
              <div className="mt-6 flex justify-center gap-3">
                <Link
                  href={`/cases/${caseId}`}
                  className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 transition-colors"
                >
                  Otwórz sprawę
                </Link>
                <Link
                  href="/cases"
                  className="rounded-lg border border-slate-200 bg-white px-5 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  Lista spraw
                </Link>
              </div>
            </div>
          </div>
        </main>
      </>
    );
  }

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

          <h2 className="mb-6 text-xl font-bold text-slate-800">Nowe zapytanie ofertowe</h2>

          <form onSubmit={onSubmit} className="space-y-6">
            {/* Customer info */}
            <div className="rounded-xl border border-slate-200 bg-white p-6">
              <h3 className="mb-4 text-sm font-bold uppercase tracking-wide text-slate-400">Dane klienta</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">
                    Imię i nazwisko <span className="text-red-500">*</span>
                  </label>
                  <input
                    {...register('name')}
                    placeholder="Jan Kowalski"
                    className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {errors.name && <p className="mt-1 text-xs text-red-500">{errors.name.message}</p>}
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">Firma</label>
                  <input
                    {...register('company')}
                    placeholder="Kowalski sp. z o.o."
                    className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">E-mail</label>
                  <input
                    {...register('email')}
                    type="email"
                    placeholder="jan@kowalski.pl"
                    className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                  {errors.email && <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>}
                </div>

                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-700">Telefon</label>
                  <input
                    {...register('phone')}
                    placeholder="+48 600 000 000"
                    className="h-9 w-full rounded-lg border border-slate-200 px-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                  />
                </div>
              </div>

              <div className="mt-4">
                <label className="mb-1.5 block text-sm font-medium text-slate-700">Uwagi</label>
                <textarea
                  {...register('notes')}
                  rows={3}
                  placeholder="Dodatkowe informacje o zapytaniu…"
                  className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-800 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 resize-none"
                />
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 py-3 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60 transition-colors shadow-sm"
            >
              {mutation.isPending ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Tworzenie…</>
              ) : (
                <>Utwórz sprawę i przejdź do plików</>
              )}
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
