import axios from 'axios';
import type {
  InquiryCase,
  CreateCaseRequest,
  CreateCaseResponse,
  ApproveRequest,
  TechPlan,
  PartSpec,
  Quote,
  UploadedFile,
  HealthStatus,
} from '@/types';

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const http = axios.create({
  baseURL: BASE,
  timeout: 60_000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Health ───────────────────────────────────────────────────────────────────

export const getHealth = (): Promise<HealthStatus> =>
  http.get('/health').then(r => r.data);

// ─── Cases ────────────────────────────────────────────────────────────────────

export const getCases = (): Promise<InquiryCase[]> =>
  http.get('/api/v1/cases').then(r => r.data);

export const getCase = (id: string): Promise<InquiryCase> =>
  http.get(`/api/v1/cases/${id}`).then(r => r.data);

export const createCase = (body: CreateCaseRequest): Promise<CreateCaseResponse> =>
  http.post('/api/v1/cases', body).then(r => r.data);

export const approveCase = (id: string, body: ApproveRequest): Promise<{ case_id: string; approved: boolean; status: string }> =>
  http.post(`/api/v1/cases/${id}/approve`, body).then(r => r.data);

export const getCaseTechPlan = (id: string): Promise<{ case_id: string; tech_plan: TechPlan }> =>
  http.get(`/api/v1/cases/${id}/tech-plan`).then(r => r.data);

export const getSimilarCases = (id: string, limit = 5): Promise<{ case_id: string; similar_cases: InquiryCase[]; limit: number }> =>
  http.get(`/api/v1/cases/${id}/similar`, { params: { limit } }).then(r => r.data);

// ─── Files ────────────────────────────────────────────────────────────────────

export const uploadFile = (file: File, caseId?: string): Promise<UploadedFile> => {
  const fd = new FormData();
  fd.append('file', file);
  if (caseId) fd.append('case_id', caseId);
  return http.post('/api/v1/files/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};

export const analyzeFile = (fileId: string): Promise<{ file_id: string; status: string }> =>
  http.post(`/api/v1/files/analyze/${fileId}`).then(r => r.data);

export const getFileSpec = (fileId: string): Promise<{ file_id: string; spec: PartSpec }> =>
  http.get(`/api/v1/files/${fileId}/spec`).then(r => r.data);

// ─── Quotes ───────────────────────────────────────────────────────────────────

export const quickEstimate = (partSpec: PartSpec, batchSize = 1): Promise<{
  quote: Quote; tech_plan: TechPlan;
  summary: { total_cost: number; unit_cost: number; currency: string; operations: number; confidence: string };
}> =>
  http.post('/api/v1/quotes/quick-estimate', { part_spec: partSpec, batch_size: batchSize }).then(r => r.data);

export const getQuote = (quoteId: string): Promise<Quote> =>
  http.get(`/api/v1/quotes/${quoteId}`).then(r => r.data);

export const exportToERP = (quoteId: string): Promise<{ quote_id: string; erp_status: string }> =>
  http.post(`/api/v1/quotes/${quoteId}/export-erp`).then(r => r.data);
