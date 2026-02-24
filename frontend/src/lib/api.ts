import axios from 'axios';
import type {
  InquiryCase,
  CreateCaseRequest,
  ApproveRequest,
  TechPlan,
  PartSpec,
  Quote,
  UploadedFile,
  QuickEstimateRequest,
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

export const createCase = (body: CreateCaseRequest): Promise<InquiryCase> =>
  http.post('/api/v1/cases', body).then(r => r.data);

export const approveCase = (id: string, body: ApproveRequest): Promise<InquiryCase> =>
  http.post(`/api/v1/cases/${id}/approve`, body).then(r => r.data);

export const getCaseTechPlan = (id: string): Promise<TechPlan> =>
  http.get(`/api/v1/cases/${id}/tech-plan`).then(r => r.data);

export const getSimilarCases = (id: string): Promise<InquiryCase[]> =>
  http.get(`/api/v1/cases/${id}/similar`).then(r => r.data);

// ─── Files ────────────────────────────────────────────────────────────────────

export const uploadFile = (file: File, caseId?: string): Promise<UploadedFile> => {
  const fd = new FormData();
  fd.append('file', file);
  if (caseId) fd.append('case_id', caseId);
  return http.post('/api/v1/files/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};

export const analyzeFile = (fileId: string): Promise<{ status: string }> =>
  http.post(`/api/v1/files/analyze/${fileId}`).then(r => r.data);

export const getFileSpec = (fileId: string): Promise<PartSpec> =>
  http.get(`/api/v1/files/${fileId}/spec`).then(r => r.data);

// ─── Quotes ───────────────────────────────────────────────────────────────────

export const quickEstimate = (body: QuickEstimateRequest): Promise<Quote> =>
  http.post('/api/v1/quotes/quick-estimate', body).then(r => r.data);

export const getQuote = (quoteId: string): Promise<Quote> =>
  http.get(`/api/v1/quotes/${quoteId}`).then(r => r.data);

export const getQuoteBreakdown = (quoteId: string): Promise<Quote> =>
  http.get(`/api/v1/quotes/${quoteId}/breakdown`).then(r => r.data);

export const exportToERP = (quoteId: string): Promise<{ status: string; erp_id?: string }> =>
  http.post(`/api/v1/quotes/${quoteId}/export-erp`).then(r => r.data);
