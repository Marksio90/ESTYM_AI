'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  FolderOpen,
  Plus,
  FileText,
  Settings,
  Activity,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV = [
  { href: '/',           icon: LayoutDashboard, label: 'Pulpit' },
  { href: '/cases',      icon: FolderOpen,       label: 'Sprawy' },
  { href: '/cases/new',  icon: Plus,             label: 'Nowa sprawa' },
];

const BOTTOM_NAV = [
  { href: '/health',    icon: Activity, label: 'Status systemu' },
  { href: '/settings',  icon: Settings, label: 'Ustawienia' },
];

export function Sidebar() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' : pathname.startsWith(href);

  return (
    <aside className="fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col bg-brand-950 text-white">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-brand-800">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-500">
          <Zap className="h-5 w-5 text-white" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-wide text-white">ESTYM AI</p>
          <p className="text-xs text-brand-300">Wyceny stalowych</p>
        </div>
      </div>

      {/* Main nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 scrollbar-thin">
        <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-widest text-brand-400">
          Menu
        </p>
        <ul className="space-y-0.5">
          {NAV.map(({ href, icon: Icon, label }) => (
            <li key={href}>
              <Link
                href={href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive(href)
                    ? 'bg-brand-700 text-white'
                    : 'text-brand-300 hover:bg-brand-800 hover:text-white'
                )}
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                {label}
              </Link>
            </li>
          ))}
        </ul>

        <p className="mb-2 mt-6 px-3 text-[11px] font-semibold uppercase tracking-widest text-brand-400">
          Dokumenty
        </p>
        <ul className="space-y-0.5">
          <li>
            <Link
              href="/docs"
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-brand-300 hover:bg-brand-800 hover:text-white transition-colors"
              target="_blank"
              rel="noopener noreferrer"
            >
              <FileText className="h-4 w-4 flex-shrink-0" />
              API Docs
            </Link>
          </li>
        </ul>
      </nav>

      {/* Bottom nav */}
      <div className="border-t border-brand-800 px-3 py-3">
        <ul className="space-y-0.5">
          {BOTTOM_NAV.map(({ href, icon: Icon, label }) => (
            <li key={href}>
              <Link
                href={href}
                className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-brand-300 hover:bg-brand-800 hover:text-white transition-colors"
              >
                <Icon className="h-4 w-4 flex-shrink-0" />
                {label}
              </Link>
            </li>
          ))}
        </ul>
        <div className="mt-3 rounded-lg bg-brand-900 px-3 py-2.5">
          <p className="text-xs text-brand-400">v0.1.0 · development</p>
        </div>
      </div>
    </aside>
  );
}
