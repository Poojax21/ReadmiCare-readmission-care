import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Types ────────────────────────────────────────────────────

export interface FeatureImportance {
  feature: string
  shap_value: number
  feature_value: number | null
  direction: 'increases_risk' | 'decreases_risk'
  percentile?: number
  label?: string
}

export interface PredictionResponse {
  prediction_id: string
  admission_id: string
  risk_score: number
  risk_tier: 'HIGH' | 'MEDIUM' | 'LOW'
  confidence_lower: number
  confidence_upper: number
  top_features: FeatureImportance[]
  clinical_explanation: string
  model_version: string
  model_name: string
  predicted_at: string
  recommended_actions: string[]
}

export interface PatientSummary {
  id: string
  mrn: string
  first_name?: string
  last_name?: string
  full_name?: string
  age: number
  gender: string
  ethnicity?: string
  date_of_birth?: string
  phone?: string
  primary_diagnosis_icd?: string
  primary_diagnosis_name?: string
  comorbidities: string[]
  insurance_type?: string
  attending_physician?: string
  ward?: string
  latest_risk_score?: number
  risk_tier?: string
}

export interface DashboardStats {
  total_active_admissions: number
  high_risk_count: number
  medium_risk_count: number
  low_risk_count: number
  avg_risk_score: number
  alerts_today: number
  model_accuracy: number
  last_updated: string
}

export interface RiskHeatmapPoint {
  patient_id: string
  mrn: string
  age: number
  risk_score: number
  risk_tier: string
  primary_diagnosis?: string
  los_days?: number
  top_risk_factor?: string
}

export interface CohortSummary {
  total_patients: number
  high_risk: number
  medium_risk: number
  low_risk: number
  avg_risk_score: number
  avg_age: number
  avg_los: number
  top_diagnoses: { code: string; count: number }[]
  readmission_rate_actual?: number
}

export interface RetrainStatus {
  task_id: string
  status: string
  progress: number
  current_step: string
  metrics?: Record<string, number>
  error?: string
}

// ── Copilot Types ────────────────────────────────────────────
export interface CopilotResponse {
  answer: string
  clinical_references: string[]
  matched_conditions: string[]
  risk_context: { score: number; tier: string; top_driver: string }
}

// ── Simulation Types ─────────────────────────────────────────
export interface InterventionImpact {
  parameter: string
  original: number
  simulated: number
  risk_contribution: number
}

export interface SimulationResult {
  patient_id: string
  original_risk: number
  simulated_risk: number
  risk_delta: number
  risk_reduction_pct: number
  intervention_impacts: InterventionImpact[]
  recommendation: string
  confidence: string
}

// ── Notes NLP Types ──────────────────────────────────────────
export interface ExtractedEntity {
  text: string
  category: string
  severity?: string
  icd_hint?: string
}

export interface RiskSignal {
  signal: string
  risk_category: string
  evidence: string
  impact: string
}

export interface NotesExtractionResult {
  entities: ExtractedEntity[]
  risk_signals: RiskSignal[]
  summary: string
  overall_risk_modifier: string
  readmission_flags_count: number
}

// ── Financial Types ──────────────────────────────────────────
export interface CostBreakdown {
  tier: string
  patient_count: number
  prevented_readmissions: number
  savings: number
  intervention_cost: number
  net_savings: number
}

export interface FinancialROI {
  total_patients_analyzed: number
  high_risk_patients: number
  medium_risk_patients: number
  low_risk_patients: number
  estimated_preventable_readmissions: number
  gross_savings: number
  total_intervention_cost: number
  net_savings: number
  cms_penalty_avoided: number
  roi_percentage: number
  cost_per_quality_adjusted_outcome: number
  tier_breakdown: CostBreakdown[]
  generated_at: string
}

// ── Trajectory Types ─────────────────────────────────────────
export interface TrajectoryPoint {
  hour_offset: number
  risk_score: number
  risk_tier: string
  timestamp: string
}

export interface TrajectoryResponse {
  patient_id: string
  current_risk: number
  current_tier: string
  trajectory: TrajectoryPoint[]
}

// ── Trend Types ──────────────────────────────────────────────
export interface TrendDay {
  day: string
  high: number
  medium: number
  low: number
}

// ── API Calls ──────────────────────────────────────────────────

export interface PatientCreate {
  mrn: string
  first_name?: string
  last_name?: string
  age: number
  gender: string
  ethnicity?: string
  date_of_birth?: string
  phone?: string
  primary_diagnosis_icd?: string
  primary_diagnosis_name?: string
  comorbidities: string[]
  insurance_type?: string
  attending_physician?: string
  ward?: string
}

export const predictionAPI = {
  demo: () => api.get<PredictionResponse>('/predict/demo').then(r => r.data),
  predict: (payload: unknown) =>
    api.post<PredictionResponse>('/predict', payload).then(r => r.data),
  batch: (ids: string[]) =>
    api.post('/predict/batch', { admission_ids: ids }).then(r => r.data),
}

export const patientsAPI = {
  list: (params?: { search?: string; risk_tier?: string; limit?: number; offset?: number }) =>
    api.get<PatientSummary[]>('/patients', { params }).then(r => r.data),
  create: (data: PatientCreate) => 
    api.post<PatientSummary>('/patients', data).then(r => r.data),
  stats: () => api.get<DashboardStats>('/patients/dashboard/stats').then(r => r.data),
  heatmap: (limit = 100) =>
    api.get<RiskHeatmapPoint[]>('/patients/heatmap', { params: { limit } }).then(r => r.data),
  get: (id: string) => api.get(`/patients/${id}`).then(r => r.data),
  trajectory: (id: string, hours = 24) =>
    api.get<TrajectoryResponse>(`/patients/${id}/trajectory`, { params: { hours } }).then(r => r.data),
  trend: () =>
    api.get<{ trend: TrendDay[] }>('/patients/dashboard/trend').then(r => r.data.trend),
}

export const cohortAPI = {
  analyze: (filters: unknown) =>
    api.post<CohortSummary>('/cohorts', filters).then(r => r.data),
}

export const retrainAPI = {
  trigger: (config: unknown) =>
    api.post<RetrainStatus>('/retrain', config).then(r => r.data),
  status: (taskId: string) =>
    api.get<RetrainStatus>(`/retrain/${taskId}`).then(r => r.data),
  list: () => api.get('/retrain').then(r => r.data),
}

export const copilotAPI = {
  query: (patientId: string, query: string) =>
    api.post<CopilotResponse>('/copilot/query', { patient_id: patientId, query }).then(r => r.data),
}

export const simulationAPI = {
  simulate: (patientId: string, overrides: Record<string, number>) =>
    api.post<SimulationResult>('/simulation/simulate', { patient_id: patientId, overrides }).then(r => r.data),
  parameters: () =>
    api.get('/simulation/parameters').then(r => r.data),
}

export const notesAPI = {
  extract: (noteText: string) =>
    api.post<NotesExtractionResult>('/notes/extract', { note_text: noteText, include_severity: true }).then(r => r.data),
}

export const financialsAPI = {
  roi: () => api.get<FinancialROI>('/financials/roi').then(r => r.data),
}

export default api
