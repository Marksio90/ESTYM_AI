import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { format, formatDistanceToNow } from 'date-fns';
import { pl } from 'date-fns/locale';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string): string {
  return format(new Date(iso), 'd MMM yyyy, HH:mm', { locale: pl });
}

export function timeAgo(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true, locale: pl });
}

export function formatCurrency(amount: number, currency = 'PLN'): string {
  return new Intl.NumberFormat('pl-PL', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function formatMinutes(min: number): string {
  if (min < 60) return `${Math.round(min)} min`;
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  return m > 0 ? `${h} h ${m} min` : `${h} h`;
}

export function confidenceLabel(c: string): string {
  return { low: 'Niska', medium: 'Średnia', high: 'Wysoka' }[c] ?? c;
}

export function confidenceColor(c: string): string {
  return { low: 'text-red-600', medium: 'text-amber-600', high: 'text-green-600' }[c] ?? 'text-gray-600';
}
