import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';
import { Sidebar } from '@/components/layout/Sidebar';

export const metadata: Metadata = {
  title: 'ESTYM AI — Wyceny stalowych',
  description: 'Platforma AI do automatycznej wyceny produktów stalowych',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pl">
      <body>
        <Providers>
          <div className="flex min-h-screen">
            <Sidebar />
            <div className="flex flex-1 flex-col pl-[260px]">
              {children}
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
