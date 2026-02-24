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
  const mat = spec.materials?.[0];
  const geo = spec.geometry;
  const proc = spec.process_requirements;
  const uncertainties = spec.uncertainty ?? [];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-slate-800">{spec.part_name ?? 'Brak nazwy'}</h3>
          {spec.drawing_revision && (
            <p className="text-xs text-slate-500">Rewizja rysunku: {spec.drawing_revision}</p>
          )}
        </div>
        {spec.confidence && (
          <span className={cn('text-sm font-semibold', confidenceColor(spec.confidence))}>
            Pewność: {confidenceLabel(spec.confidence)}
          </span>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Material */}
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">
            Materiał {spec.materials && spec.materials.length > 1 ? `(${spec.materials.length} pozycji)` : ''}
          </p>
          {mat ? (
            <>
              <Row label="Standard" value={mat.standard} />
              <Row label="Gatunek" value={mat.grade} />
              <Row label="Forma" value={mat.form} />
              <Row label="Grubość" value={mat.thickness_mm != null ? `${mat.thickness_mm} mm` : undefined} />
              <Row label="Szerokość" value={mat.width_mm != null ? `${mat.width_mm} mm` : undefined} />
              <Row label="Wysokość" value={mat.height_mm != null ? `${mat.height_mm} mm` : undefined} />
              <Row label="Średnica" value={mat.diameter_mm != null ? `${mat.diameter_mm} mm` : undefined} />
              <Row label="Gr. ścianki" value={mat.wall_thickness_mm != null ? `${mat.wall_thickness_mm} mm` : undefined} />
              <Row label="Masa" value={mat.weight_kg != null ? `${mat.weight_kg} kg` : undefined} />
            </>
          ) : (
            <p className="text-xs text-slate-400">Brak danych o materiale</p>
          )}
        </div>

        {/* Geometry */}
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">Geometria</p>
          {geo ? (
            <>
              <Row label="Dług. (X)" value={geo.overall_length_mm != null ? `${geo.overall_length_mm} mm` : undefined} />
              <Row label="Szer. (Y)" value={geo.overall_width_mm != null ? `${geo.overall_width_mm} mm` : undefined} />
              <Row label="Wys. (Z)" value={geo.overall_height_mm != null ? `${geo.overall_height_mm} mm` : undefined} />
              <Row label="Masa" value={geo.weight_kg != null ? `${geo.weight_kg} kg` : undefined} />
              <Row label="Pow. powierzchni" value={geo.surface_area_m2 != null ? `${geo.surface_area_m2.toFixed(4)} m²` : undefined} />
              {geo.wire && (
                <>
                  <Row label="Dług. drutu" value={geo.wire.total_length_mm != null ? `${geo.wire.total_length_mm} mm` : undefined} />
                  <Row label="Gięcia (drut)" value={geo.wire.bend_count} />
                </>
              )}
              {geo.sheet && (
                <>
                  <Row label="Pow. blachy" value={geo.sheet.area_mm2 != null ? `${geo.sheet.area_mm2.toFixed(0)} mm²` : undefined} />
                  <Row label="Gięcia (blacha)" value={geo.sheet.bend_count} />
                  <Row label="Wycięcia" value={geo.sheet.cutout_count} />
                </>
              )}
              {geo.tube && (
                <>
                  <Row label="Dług. rury" value={geo.tube.length_mm != null ? `${geo.tube.length_mm} mm` : undefined} />
                  <Row label="Gięcia (rura)" value={geo.tube.bend_count} />
                </>
              )}
              {geo.welds && (
                <>
                  <Row label="Dług. spoin" value={geo.welds.linear_weld_length_mm != null ? `${geo.welds.linear_weld_length_mm} mm` : undefined} />
                  <Row label="Spoiny punkt." value={geo.welds.spot_weld_count} />
                </>
              )}
              {geo.holes && (
                <Row label="Otwory" value={geo.holes.count} />
              )}
            </>
          ) : (
            <p className="text-xs text-slate-400">Brak danych geometrycznych</p>
          )}
        </div>

        {/* Process */}
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">Wymagania procesowe</p>
          {proc ? (
            <>
              <Row label="Spawanie" value={proc.welding && proc.welding !== 'NONE' ? proc.welding : undefined} />
              <Row label="Pow. wykończenie" value={proc.surface_finish} />
              <Row label="Kolor RAL" value={proc.paint_color_ral} />
              {proc.tolerances_notes && proc.tolerances_notes.length > 0 && (
                <div className="py-1.5 border-b border-slate-50">
                  <p className="text-xs text-slate-500 mb-1">Tolerancje</p>
                  <ul className="space-y-0.5">
                    {proc.tolerances_notes.map((n, i) => (
                      <li key={i} className="text-xs text-slate-700">• {n}</li>
                    ))}
                  </ul>
                </div>
              )}
              {proc.special_requirements && proc.special_requirements.length > 0 && (
                <div className="py-1.5">
                  <p className="text-xs text-slate-500 mb-1">Wymagania specjalne</p>
                  <ul className="space-y-0.5">
                    {proc.special_requirements.map((r, i) => (
                      <li key={i} className="text-xs text-slate-700">• {r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <p className="text-xs text-slate-400">Brak wymagań procesowych</p>
          )}
        </div>
      </div>

      {/* Uncertainties */}
      {uncertainties.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-600" />
            <p className="text-sm font-semibold text-amber-800">Niejasności wymagające uwagi ({uncertainties.length})</p>
          </div>
          <ul className="space-y-2">
            {uncertainties.map((u, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                {u.severity && (
                  <span className={cn('mt-0.5 rounded px-1.5 py-0.5 font-medium flex-shrink-0', {
                    'bg-red-100 text-red-700':    u.severity === 'HIGH',
                    'bg-amber-100 text-amber-700': u.severity === 'MEDIUM',
                    'bg-slate-100 text-slate-700': u.severity === 'LOW',
                  })}>
                    {u.severity === 'HIGH' ? 'Wysoka' : u.severity === 'MEDIUM' ? 'Średnia' : 'Niska'}
                  </span>
                )}
                <span className="text-amber-800"><strong>{u.field}:</strong> {u.issue}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {uncertainties.length === 0 && (
        <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 rounded-xl border border-green-200 p-3">
          <CheckCircle2 className="h-4 w-4" />
          Brak niejasności — specyfikacja kompletna
        </div>
      )}
    </div>
  );
}
