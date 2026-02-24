// ─── Enums (matching actual backend values) ───────────────────────────────────

export type CaseStatus =
  | 'NEW'
  | 'ANALYZING'
  | 'AWAITING_INFO'
  | 'CALCULATED'
  | 'REVIEW'
  | 'APPROVED'
  | 'EXPORTED_TO_ERP'
  | 'REJECTED';

export type FileType =
  | 'pdf' | 'dxf' | 'dwg' | 'step' | 'sat'
  | 'sldprt' | 'sldasm' | 'iges' | 'stl' | 'unknown';

export type ConversionStatus = 'PENDING' | 'OK' | 'FAILED';
export type Confidence = 'LOW' | 'MEDIUM' | 'HIGH';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH';
export type MaterialForm = 'WIRE' | 'TUBE' | 'PROFILE' | 'SHEET' | 'BAR' | 'FLATBAR' | 'ANGLE' | 'OTHER';
export type ProductFamily = 'WIRE' | 'TUBE' | 'PROFILE' | 'SHEET_METAL' | 'WELDED_ASSEMBLY' | 'MIXED' | 'UNKNOWN';
export type SurfaceFinish = 'GALVANIZED' | 'PAINTED' | 'POWDER_COATED' | 'RAW' | 'OUTSOURCED' | 'UNKNOWN';
export type WeldingType = 'NONE' | 'MIG' | 'TIG' | 'SPOT' | 'ROBOTIC' | 'MIXED' | 'UNKNOWN';

export type OperationType =
  | 'CUTTING' | 'WIRE_BENDING' | 'SHEET_BENDING' | 'TUBE_BENDING'
  | 'SPOT_WELDING' | 'MIG_WELDING' | 'TIG_WELDING' | 'ROBOTIC_WELDING'
  | 'GRINDING' | 'DRILLING' | 'THREADING' | 'DEBURRING'
  | 'GALVANIZING' | 'POWDER_COATING' | 'PAINTING'
  | 'ASSEMBLY' | 'QA_INSPECTION' | 'PACKAGING' | 'DEGREASING' | 'FIXTURE_SETUP';

// ─── Customer ─────────────────────────────────────────────────────────────────

export interface CustomerInfo {
  name: string;
  email_domain?: string;
  account_id?: string;
  contact_email?: string;
}

// ─── File ─────────────────────────────────────────────────────────────────────

export interface AttachedFile {
  file_id: string;
  filename: string;
  detected_type: FileType;
  conversion_status: ConversionStatus;
  storage_key?: string;
  preview_urls?: string[];
  file_size_bytes?: number;
}

// ─── Case ─────────────────────────────────────────────────────────────────────

export interface InquiryCase {
  case_id: string;
  status: CaseStatus;
  received_at?: string;
  customer: CustomerInfo;
  email_subject?: string;
  email_body_summary?: string;
  requested_qty?: number;
  product_family_guess?: ProductFamily;
  risk_level?: RiskLevel;
  target_finish?: SurfaceFinish[];
  files: AttachedFile[];
  missing_info_questions?: string[];
  notes?: string[];
  created_at: string;
  updated_at: string;
}

// ─── Create Case (intake form) ────────────────────────────────────────────────

export interface CreateCaseRequest {
  email_subject: string;
  email_body: string;
  customer_name: string;
  customer_email: string;
  requested_qty?: number;
  notes?: string;
}

export interface CreateCaseResponse {
  case_id: string;
  status: string;
  product_family?: string;
  risk_level?: string;
  missing_info?: string[];
  messages?: Record<string, unknown>[];
}

// ─── Approve ──────────────────────────────────────────────────────────────────

export interface ApproveRequest {
  approved: boolean;
  modifications?: Record<string, unknown>[];
  notes?: string;
}

// ─── Part Spec ────────────────────────────────────────────────────────────────

export interface MaterialSpec {
  standard?: string;
  grade?: string;
  form?: MaterialForm;
  diameter_mm?: number;
  wall_thickness_mm?: number;
  thickness_mm?: number;
  width_mm?: number;
  height_mm?: number;
  weight_kg?: number;
  density_kg_m3?: number;
}

export interface WeldSpec {
  spot_weld_count?: number;
  linear_weld_length_mm?: number;
  weld_type?: WeldingType;
  weld_throat_mm?: number;
}

export interface HoleSpec {
  count?: number;
  diameters_mm?: number[];
  threaded_count?: number;
  thread_specs?: string[];
}

export interface Geometry {
  wire?: { total_length_mm?: number; bend_count?: number };
  sheet?: { area_mm2?: number; bend_count?: number; cutout_count?: number };
  tube?: { length_mm?: number; bend_count?: number };
  welds?: WeldSpec;
  holes?: HoleSpec;
  overall_length_mm?: number;
  overall_width_mm?: number;
  overall_height_mm?: number;
  weight_kg?: number;
  surface_area_m2?: number;
}

export interface ProcessRequirements {
  welding?: WeldingType;
  surface_finish?: SurfaceFinish;
  paint_color_ral?: string;
  tolerances_notes?: string[];
  special_requirements?: string[];
}

export interface UncertaintyItem {
  field: string;
  issue: string;
  severity?: RiskLevel;
}

export interface PartSpec {
  part_id?: string;
  part_name?: string;
  source_file_id?: string;
  materials?: MaterialSpec[];
  geometry?: Geometry;
  process_requirements?: ProcessRequirements;
  bom?: { part_name?: string; quantity?: number; material?: string }[];
  quantity?: number;
  drawing_revision?: string;
  drawing_notes?: string[];
  uncertainty?: UncertaintyItem[];
  confidence?: Confidence;
}

// ─── Tech Plan ────────────────────────────────────────────────────────────────

export interface Operation {
  op_code: string;
  op_name: string;
  op_type: OperationType;
  workcenter?: string;
  workcenter_name?: string;
  cycle_time_sec?: number;
  setup_time_sec?: number;
  handling_time_sec?: number;
  multiplier?: number;
  requires_fixture?: boolean;
  operator_count?: number;
  skill_level?: string;
  qa_check_required?: boolean;
  inputs?: string[];
  outputs?: string[];
  notes?: string[];
}

export interface TechPlan {
  plan_id?: string;
  operations: Operation[];
  precedence_edges?: { from_op_code: string; to_op_code: string; relation: string }[];
  batch_size?: number;
  total_setup_time_sec?: number;
  total_cycle_time_sec?: number;
  total_time_with_overhead_sec?: number;
  notes_for_operator?: string[];
}

// ─── Quote ────────────────────────────────────────────────────────────────────

export interface CostBreakdownItem {
  category: string;
  description: string;
  quantity?: number;
  unit?: string;
  unit_cost?: number;
  total_cost: number;
  notes?: string;
}

export interface Quote {
  quote_id: string;
  case_id?: string;
  material_cost?: number;
  labor_cost?: number;
  machine_cost?: number;
  fixture_cost?: number;
  coating_cost?: number;
  overhead_cost?: number;
  total_cost: number;
  unit_cost?: number;
  quantity?: number;
  currency: string;
  breakdown: CostBreakdownItem[];
  similar_cases?: { case_id: string; similarity_score?: number; total_cost?: number }[];
  confidence: Confidence;
  assumptions?: string[];
  risk_notes?: string[];
  created_at?: string;
  approved_by?: string;
  approved_at?: string;
}

// ─── Upload ───────────────────────────────────────────────────────────────────

export interface UploadedFile {
  file_id: string;
  filename: string;
  detected_type: FileType;
  needs_conversion: boolean;
  status: string;
}

// ─── Health ───────────────────────────────────────────────────────────────────

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
  NEW:             { label: 'Nowe',            color: 'text-blue-700',   bgColor: 'bg-blue-50',   dotColor: 'bg-blue-500' },
  ANALYZING:       { label: 'Analiza AI',      color: 'text-amber-700',  bgColor: 'bg-amber-50',  dotColor: 'bg-amber-500', pulse: true },
  AWAITING_INFO:   { label: 'Brak danych',     color: 'text-orange-700', bgColor: 'bg-orange-50', dotColor: 'bg-orange-500' },
  CALCULATED:      { label: 'Wyliczone',       color: 'text-cyan-700',   bgColor: 'bg-cyan-50',   dotColor: 'bg-cyan-500' },
  REVIEW:          { label: 'Przegląd',        color: 'text-purple-700', bgColor: 'bg-purple-50', dotColor: 'bg-purple-500' },
  APPROVED:        { label: 'Zatwierdzone',    color: 'text-green-700',  bgColor: 'bg-green-50',  dotColor: 'bg-green-500' },
  EXPORTED_TO_ERP: { label: 'Wyeksportowane', color: 'text-teal-700',   bgColor: 'bg-teal-50',   dotColor: 'bg-teal-500' },
  REJECTED:        { label: 'Odrzucone',       color: 'text-red-700',    bgColor: 'bg-red-50',    dotColor: 'bg-red-500' },
};

export const OPERATION_LABELS: Record<string, string> = {
  CUTTING:         'Cięcie',
  WIRE_BENDING:    'Gięcie drutu',
  SHEET_BENDING:   'Gięcie blachy',
  TUBE_BENDING:    'Gięcie rury',
  SPOT_WELDING:    'Spawanie punkt.',
  MIG_WELDING:     'Spawanie MIG',
  TIG_WELDING:     'Spawanie TIG',
  ROBOTIC_WELDING: 'Spawanie robotyczne',
  GRINDING:        'Szlifowanie',
  DRILLING:        'Wiercenie',
  THREADING:       'Gwintowanie',
  DEBURRING:       'Gratowanie',
  GALVANIZING:     'Cynkowanie',
  POWDER_COATING:  'Malowanie proszkowe',
  PAINTING:        'Malowanie',
  ASSEMBLY:        'Montaż',
  QA_INSPECTION:   'Kontrola jakości',
  PACKAGING:       'Pakowanie',
  DEGREASING:      'Odtłuszczanie',
  FIXTURE_SETUP:   'Przyrząd montażowy',
};
