'use client';

import { Bell, Search } from 'lucide-react';

export function TopBar({ title }: { title?: string }) {
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
      <h1 className="text-base font-semibold text-slate-800">{title ?? 'ESTYM AI'}</h1>
      <div className="flex items-center gap-3">
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Szukaj spraw..."
            className="h-8 w-56 rounded-lg border border-slate-200 bg-slate-50 pl-9 pr-3 text-sm text-slate-700 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>
        <button className="relative rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-brand-500" />
        </button>
      </div>
    </header>
  );
}
