// ─── Enums ────────────────────────────────────────────────────────────────────

export type CaseStatus =
  | 'new'
  | 'analyzing'
  | 'reviewing'
  | 'approved'
  | 'exported'
  | 'failed';

export type FileType = 'dxf' | 'pdf' | 'step' | 'iges' | 'stl' | 'unknown';
export type ConversionStatus = 'pending' | 'processing' | 'done' | 'failed';
export type Confidence = 'low' | 'medium' | 'high';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type MaterialForm = 'sheet' | 'tube' | 'bar' | 'wire' | 'profile' | 'casting' | 'unknown';
export type OperationType =
  | 'laser_cutting'
  | 'plasma_cutting'
  | 'bending'
  | 'welding'
  | 'turning'
  | 'milling'
  | 'grinding'
  | 'drilling'
  | 'assembly'
  | 'surface_treatment'
  | 'quality_control'
  | 'other';

// ─── Customer ─────────────────────────────────────────────────────────────────

export interface CustomerInfo {
  name: string;
  email?: string;
  phone?: string;
  company?: string;
  notes?: string;
}

// ─── File ─────────────────────────────────────────────────────────────────────

export interface AttachedFile {
  id: string;
  filename: string;
  file_type: FileType;
  size_bytes?: number;
  conversion_status: ConversionStatus;
  minio_key?: string;
  uploaded_at: string;
}

// ─── Case ─────────────────────────────────────────────────────────────────────

export interface InquiryCase {
  id: string;
  status: CaseStatus;
  customer: CustomerInfo;
  files: AttachedFile[];
  created_at: string;
  updated_at: string;
  notes?: string;
  workflow_state?: Record<string, unknown>;
}

// ─── Part Spec ────────────────────────────────────────────────────────────────

export interface MaterialSpec {
  grade?: string;
  form?: MaterialForm;
  thickness_mm?: number;
  width_mm?: number;
  length_mm?: number;
  diameter_mm?: number;
  density_kg_m3?: number;
  weight_kg?: number;
}

export interface Geometry {
  bounding_box_mm?: [number, number, number];
  surface_area_mm2?: number;
  volume_mm3?: number;
  weld_length_mm?: number;
  hole_count?: number;
  bend_count?: number;
  cut_length_mm?: number;
}

export interface ProcessRequirements {
  welding_required?: boolean;
  welding_type?: string;
  surface_finish?: string;
  tolerance_class?: string;
  heat_treatment?: string;
  painting_required?: boolean;
  certification_required?: boolean;
}

export interface BOMItem {
  position: number;
  name: string;
  quantity: number;
  material?: string;
  dimensions?: string;
  notes?: string;
}

export interface UncertaintyItem {
  field: string;
  issue: string;
  severity: RiskLevel;
}

export interface PartSpec {
  part_name?: string;
  drawing_number?: string;
  revision?: string;
  quantity: number;
  material: MaterialSpec;
  geometry: Geometry;
  process: ProcessRequirements;
  bom: BOMItem[];
  uncertainties: UncertaintyItem[];
  confidence: Confidence;
  raw_text_notes?: string;
}

// ─── Tech Plan ────────────────────────────────────────────────────────────────

export interface Operation {
  id: string;
  name: string;
  operation_type: OperationType;
  machine?: string;
  time_setup_min: number;
  time_per_unit_min: number;
  labor_count: number;
  notes?: string;
}

export interface PrecedenceEdge {
  from_op: string;
  to_op: string;
  relation: string;
}

export interface TechPlan {
  operations: Operation[];
  precedence: PrecedenceEdge[];
  total_time_min: number;
  batch_size: number;
  notes?: string;
}

// ─── Quote ────────────────────────────────────────────────────────────────────

export interface CostBreakdownItem {
  category: string;
  label: string;
  amount: number;
  currency: string;
  note?: string;
}

export interface SimilarCaseReference {
  case_id: string;
  similarity_score: number;
  total_cost: number;
  currency: string;
  created_at: string;
}

export interface Quote {
  id: string;
  case_id: string;
  total_cost: number;
  currency: string;
  cost_breakdown: CostBreakdownItem[];
  margin_percent: number;
  confidence: Confidence;
  valid_until?: string;
  similar_cases: SimilarCaseReference[];
  approved_by?: string;
  approved_at?: string;
  notes?: string;
  created_at: string;
}

// ─── API request / response types ─────────────────────────────────────────────

export interface CreateCaseRequest {
  customer: CustomerInfo;
  notes?: string;
}

export interface ApproveRequest {
  approved: boolean;
  adjustments?: Record<string, unknown>;
  notes?: string;
}

export interface UploadedFile {
  file_id: string;
  filename: string;
  file_type: FileType;
  size_bytes: number;
  status: string;
}

export interface QuickEstimateRequest {
  part_spec: PartSpec;
  quantity?: number;
}

export interface HealthStatus {
  status: string;
  service: string;
  version: string;
}

// ─── UI helpers ───────────────────────────────────────────────────────────────

export interface StatusConfig {
  label: string;
  color: string;
  bgColor: string;
  dotColor: string;
  pulse?: boolean;
}

export const STATUS_CONFIG: Record<CaseStatus, StatusConfig> = {
  new:       { label: 'Nowe',          color: 'text-blue-700',   bgColor: 'bg-blue-50',   dotColor: 'bg-blue-500' },
  analyzing: { label: 'Analiza',       color: 'text-amber-700',  bgColor: 'bg-amber-50',  dotColor: 'bg-amber-500', pulse: true },
  reviewing: { label: 'Przegląd',      color: 'text-purple-700', bgColor: 'bg-purple-50', dotColor: 'bg-purple-500' },
  approved:  { label: 'Zatwierdzone',  color: 'text-green-700',  bgColor: 'bg-green-50',  dotColor: 'bg-green-500' },
  exported:  { label: 'Wyeksportowane',color: 'text-teal-700',   bgColor: 'bg-teal-50',   dotColor: 'bg-teal-500' },
  failed:    { label: 'Błąd',          color: 'text-red-700',    bgColor: 'bg-red-50',    dotColor: 'bg-red-500' },
};

export const OPERATION_LABELS: Record<OperationType, string> = {
  laser_cutting:    'Cięcie laserowe',
  plasma_cutting:   'Cięcie plazmowe',
  bending:          'Gięcie',
  welding:          'Spawanie',
  turning:          'Toczenie',
  milling:          'Frezowanie',
  grinding:         'Szlifowanie',
  drilling:         'Wiercenie',
  assembly:         'Montaż',
  surface_treatment:'Obróbka powierzchni',
  quality_control:  'Kontrola jakości',
  other:            'Inne',
};
