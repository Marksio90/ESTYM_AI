'use client';

import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { getHealth } from '@/lib/api';
import { TopBar } from '@/components/layout/TopBar';

export default function HealthPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30_000,
  });

  return (
    <>
      <TopBar title="Status systemu" />
      <main className="flex-1 p-6">
        <div className="mx-auto max-w-xl">
          <div className="rounded-xl border border-slate-200 bg-white p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-slate-800">Status API</h2>
              <button onClick={() => refetch()} className="text-slate-400 hover:text-slate-600 transition-colors">
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {isLoading && (
              <div className="flex items-center gap-2 text-slate-500">
                <RefreshCw className="h-4 w-4 animate-spin" /> Sprawdzanie…
              </div>
            )}

            {isError && (
              <div className="flex items-center gap-3 rounded-lg bg-red-50 border border-red-200 p-4">
                <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
                <div>
                  <p className="font-medium text-red-800">API niedostępne</p>
                  <p className="text-sm text-red-600 mt-0.5">Nie można połączyć się z backendem.</p>
                </div>
              </div>
            )}

            {data && (
              <div className="flex items-center gap-3 rounded-lg bg-green-50 border border-green-200 p-4">
                <CheckCircle2 className="h-5 w-5 text-green-500 flex-shrink-0" />
                <div>
                  <p className="font-medium text-green-800">API działa poprawnie</p>
                  <p className="text-sm text-green-600 mt-0.5">
                    {data.service} v{data.version} · status: {data.status}
                  </p>
                </div>
              </div>
            )}

            <div className="mt-6 space-y-2 text-sm">
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Backend URL</span>
                <span className="font-mono text-xs text-slate-700">
                  {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-slate-100">
                <span className="text-slate-500">Swagger UI</span>
                <a href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/docs`}
                  target="_blank" rel="noopener noreferrer"
                  className="text-brand-600 hover:underline text-xs">
                  Otwórz →
                </a>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-slate-500">MinIO Console</span>
                <a href="http://localhost:9001" target="_blank" rel="noopener noreferrer"
                  className="text-brand-600 hover:underline text-xs">
                  Otwórz →
                </a>
              </div>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
