import { cn, confidenceLabel, confidenceColor } from '@/lib/utils';
import type { PartSpec } from '@/types';
import { AlertTriangle, CheckCircle2 } from 'lucide-react';

function Row({ label, value }: { label: string; value?: string | number | boolean | null }) {
  if (value === undefined || value === null || value === '') return null;
  return (
    <div className="flex justify-between py-1.5 border-b border-slate-50 last:border-0">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-xs font-medium text-slate-800">{String(value)}</span>
    </div>
  );
}

export function PartSpecView({ spec }: { spec: PartSpec }) {
  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-800">{spec.part_name ?? 'Brak nazwy'}</h3>
          {spec.drawing_number && <p className="text-xs text-slate-500">Rysunek: {spec.drawing_number} {spec.revision ? `Rev. ${spec.revision}` : ''}</p>}
        </div>
        <span className={cn('text-sm font-semibold', confidenceColor(spec.confidence))}>
          Pewność: {confidenceLabel(spec.confidence)}
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Material */}
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">Materiał</p>
          <Row label="Gatunek" value={spec.material.grade} />
          <Row label="Forma" value={spec.material.form} />
          <Row label="Grubość" value={spec.material.thickness_mm != null ? `${spec.material.thickness_mm} mm` : undefined} />
          <Row label="Szerokość" value={spec.material.width_mm != null ? `${spec.material.width_mm} mm` : undefined} />
          <Row label="Długość" value={spec.material.length_mm != null ? `${spec.material.length_mm} mm` : undefined} />
          <Row label="Średnica" value={spec.material.diameter_mm != null ? `${spec.material.diameter_mm} mm` : undefined} />
          <Row label="Masa" value={spec.material.weight_kg != null ? `${spec.material.weight_kg} kg` : undefined} />
        </div>

        {/* Geometry */}
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">Geometria</p>
          <Row label="Pow. powierzchni" value={spec.geometry.surface_area_mm2 != null ? `${spec.geometry.surface_area_mm2.toFixed(0)} mm²` : undefined} />
          <Row label="Objętość" value={spec.geometry.volume_mm3 != null ? `${spec.geometry.volume_mm3.toFixed(0)} mm³` : undefined} />
          <Row label="Dług. cięcia" value={spec.geometry.cut_length_mm != null ? `${spec.geometry.cut_length_mm.toFixed(0)} mm` : undefined} />
          <Row label="Dług. spoin" value={spec.geometry.weld_length_mm != null ? `${spec.geometry.weld_length_mm.toFixed(0)} mm` : undefined} />
          <Row label="Otwory" value={spec.geometry.hole_count} />
          <Row label="Gięcia" value={spec.geometry.bend_count} />
        </div>

        {/* Process */}
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">Wymagania</p>
          <Row label="Spawanie" value={spec.process.welding_required ? `Tak (${spec.process.welding_type ?? 'brak typu'})` : 'Nie'} />
          <Row label="Tolerancja" value={spec.process.tolerance_class} />
          <Row label="Pow. wykończenie" value={spec.process.surface_finish} />
          <Row label="Obróbka cieplna" value={spec.process.heat_treatment} />
          <Row label="Malowanie" value={spec.process.painting_required != null ? (spec.process.painting_required ? 'Tak' : 'Nie') : undefined} />
          <Row label="Certyfikat" value={spec.process.certification_required != null ? (spec.process.certification_required ? 'Tak' : 'Nie') : undefined} />
        </div>
      </div>

      {/* Uncertainties */}
      {spec.uncertainties.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <p className="text-sm font-semibold text-amber-800">Niejasności wymagające uwagi ({spec.uncertainties.length})</p>
          </div>
          <ul className="space-y-2">
            {spec.uncertainties.map((u, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <span className={cn('mt-0.5 rounded px-1.5 py-0.5 font-medium', {
                  'bg-red-100 text-red-700': u.severity === 'critical' || u.severity === 'high',
                  'bg-amber-100 text-amber-700': u.severity === 'medium',
                  'bg-slate-100 text-slate-700': u.severity === 'low',
                })}>
                  {u.severity}
                </span>
                <span className="text-amber-800"><strong>{u.field}:</strong> {u.issue}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {spec.uncertainties.length === 0 && (
        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 rounded-xl border border-green-200 p-3">
          <CheckCircle2 className="h-4 w-4" />
          Brak niejasności — specyfikacja kompletna
        </div>
      )}
    </div>
  );
}
