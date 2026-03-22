import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, RefreshCw, Activity, Info } from 'lucide-react'
import { predictionAPI, PredictionResponse } from '../services/api'
import toast from 'react-hot-toast'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine,
} from 'recharts'

function RiskMeter({ score, tier }: { score: number; tier: string }) {
  const color =
    tier === 'HIGH' ? 'var(--risk-high)' :
    tier === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'
  const pct = Math.round(score * 100)

  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{
        fontSize: 72,
        fontFamily: 'var(--font-display)',
        color,
        lineHeight: 1,
        letterSpacing: '-0.04em',
      }}>
        {pct}<span style={{ fontSize: 36 }}>%</span>
      </div>
      <div style={{ marginTop: 8 }}>
        <span className={`badge-${tier.toLowerCase()}`} style={{
          fontSize: 13, fontWeight: 700, padding: '4px 16px', borderRadius: 4,
          fontFamily: 'var(--font-mono)', letterSpacing: '0.06em',
        }}>
          {tier} RISK
        </span>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
        30-day readmission probability
      </div>
    </div>
  )
}

function FeatureChart({ features }: { features: any[] }) {
  const sorted = [...(features || [])]
    .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
    .slice(0, 10)

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={sorted} layout="vertical" barSize={12}>
        <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false}
          tickFormatter={v => v > 0 ? `+${v.toFixed(2)}` : v.toFixed(2)} />
        <YAxis type="category" dataKey="feature" width={140}
          tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false}
          tickFormatter={(v) => v.replace(/_/g, ' ')} />
        <Tooltip
          contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
          formatter={(v: number) => [`${v > 0 ? '+' : ''}${v.toFixed(3)}`, 'SHAP']}
        />
        <ReferenceLine x={0} stroke="var(--border)" strokeDasharray="3 3" />
        <Bar dataKey="shap_value" radius={[0, 3, 3, 0]}>
          {sorted.map((entry, i) => (
            <Cell key={i} fill={entry.shap_value > 0 ? 'var(--risk-high)' : 'var(--risk-low)'} opacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export default function PredictPage() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PredictionResponse | null>(null)

  // Simple form state
  const [form, setForm] = useState({
    age: 72, gender: 'M', admission_type: 'EMERGENCY',
    los_days: 4,
    icd_codes: 'I50.9, E11.65',
    creatinine: 1.8, hemoglobin: 9.2, albumin: 2.8,
    heart_rate: 98, sbp: 102, spo2: 91,
    charlson_index: 5,
  })

  // Validation state
  const [errors, setErrors] = useState<Record<string, string>>({})

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}
    
    // Age validation
    if (form.age < 0 || form.age > 120) {
      newErrors.age = 'Age must be between 0-120 years'
    }
    
    // Heart rate validation
    if (form.heart_rate < 20 || form.heart_rate > 250) {
      newErrors.heart_rate = 'Heart rate must be 20-250 bpm'
    }
    
    // Blood pressure validation
    if (form.sbp < 50 || form.sbp > 250) {
      newErrors.sbp = 'Systolic BP must be 50-250 mmHg'
    }
    
    // SpO2 validation
    if (form.spo2 < 50 || form.spo2 > 100) {
      newErrors.spo2 = 'SpO2 must be 50-100%'
    }
    
    // Lab validations
    if (form.creatinine < 0.1 || form.creatinine > 30) {
      newErrors.creatinine = 'Creatinine must be 0.1-30 mg/dL'
    }
    
    if (form.hemoglobin < 3 || form.hemoglobin > 25) {
      newErrors.hemoglobin = 'Hemoglobin must be 3-25 g/dL'
    }
    
    if (form.albumin < 1 || form.albumin > 7) {
      newErrors.albumin = 'Albumin must be 1-7 g/dL'
    }
    
    // Length of stay validation
    if (form.los_days < 0 || form.los_days > 365) {
      newErrors.los_days = 'Length of stay must be 0-365 days'
    }
    
    // Charlson index validation
    if (form.charlson_index < 0 || form.charlson_index > 33) {
      newErrors.charlson_index = 'Charlson index must be 0-33'
    }
    
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const runDemo = async () => {
    setLoading(true)
    try {
      const r = await predictionAPI.demo()
      setResult(r)
    } catch {
      toast.error('Prediction failed — is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  const runCustom = async () => {
    // Validate before submitting
    if (!validateForm()) {
      toast.error('Please fix validation errors before submitting')
      return
    }
    
    setLoading(true)
    try {
      const payload = {
        patient_data: {
          patient_id: '00000000-0000-0000-0000-000000000001',
          admit_time: new Date().toISOString(),
          admission_type: form.admission_type,
          icd_codes: form.icd_codes.split(',').map(s => s.trim()).filter(Boolean),
          procedure_codes: [],
          vitals: [{
            chart_time: new Date().toISOString(),
            heart_rate: form.heart_rate,
            systolic_bp: form.sbp,
            diastolic_bp: form.sbp * 0.65,
            respiratory_rate: 18,
            temperature: 37.4,
            spo2: form.spo2,
            gcs_total: 14,
          }],
          labs: [
            { chart_time: new Date().toISOString(), label: 'Creatinine', value: form.creatinine, unit: 'mg/dL' },
            { chart_time: new Date().toISOString(), label: 'Hemoglobin', value: form.hemoglobin, unit: 'g/dL' },
            { chart_time: new Date().toISOString(), label: 'Albumin',    value: form.albumin,    unit: 'g/dL' },
          ],
        },
        model_name: 'ensemble',
        include_shap: true,
      }
      const r = await predictionAPI.predict(payload)
      setResult(r)
      setErrors({})
    } catch (err: any) {
      const message = err.response?.data?.detail || 'Prediction failed — please check your input values'
      toast.error(message)
    } finally {
      setLoading(false)
    }
  }

  const field = (key: keyof typeof form, label: string, type = 'number', step?: number, min?: number, max?: number) => (
    <div>
      <label style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 4 }}>
        {label}
      </label>
      <input
        type={type}
        step={step}
        min={min}
        max={max}
        className="input-field"
        style={errors[key] ? { borderColor: 'var(--risk-high)', borderWidth: 2 } : {}}
        value={form[key] as string | number}
        onChange={e => {
          setForm(f => ({ ...f, [key]: type === 'number' ? +e.target.value : e.target.value }))
          // Clear error when user starts typing
          if (errors[key]) {
            setErrors(e => ({ ...e, [key]: '' }))
          }
        }}
      />
      {errors[key] && <div style={{ fontSize: 10, color: 'var(--risk-high)', marginTop: 2 }}>{errors[key]}</div>}
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1100 }}>
      <div>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: 0 }}>Risk Prediction</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '4px 0 0' }}>
          Enter patient data or run a synthetic demo prediction
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Input form */}
        <div className="card" style={{ padding: 24 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 20 }}>Patient Data</div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 14 }}>
            {field('age', 'Age', 'number', 1, 0, 120)}
            {field('charlson_index', 'Charlson Index', 'number', 1, 0, 33)}
            {field('los_days', 'LOS (days)', 'number', 0.5, 0, 365)}
            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 4 }}>
                Admission Type
              </label>
              <select className="input-field" value={form.admission_type}
                onChange={e => setForm(f => ({ ...f, admission_type: e.target.value }))}>
                {['EMERGENCY', 'ELECTIVE', 'URGENT'].map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
          </div>

          <div style={{ marginBottom: 14 }}>
            {field('icd_codes', 'ICD Codes (comma-separated)', 'text')}
          </div>

          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10, marginTop: 4 }}>
            Vitals
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 14 }}>
            {field('heart_rate', 'HR (bpm)', 'number', 1, 20, 250)}
            {field('sbp', 'SBP (mmHg)', 'number', 1, 50, 250)}
            {field('spo2', 'SpO₂ (%)', 'number', 1, 50, 100)}
          </div>

          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
            Labs
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 24 }}>
            {field('creatinine', 'Creatinine', 'number', 0.1, 0.1, 30)}
            {field('hemoglobin', 'Hemoglobin', 'number', 0.1, 3, 25)}
            {field('albumin',    'Albumin',    'number', 0.1, 1, 7)}
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn-primary" onClick={runCustom} disabled={loading}
              style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              {loading ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
              {loading ? 'Predicting...' : 'Predict Risk'}
            </button>
            <button className="btn-ghost" onClick={runDemo} disabled={loading}>
              Demo
            </button>
          </div>
        </div>

        {/* Results panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <AnimatePresence mode="wait">
            {result ? (
              <motion.div
                key="result"
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                style={{ display: 'flex', flexDirection: 'column', gap: 14 }}
              >
                {/* Score */}
                <div className="card" style={{ padding: 28 }}>
                  <RiskMeter score={result.risk_score} tier={result.risk_tier} />
                  <div style={{
                    marginTop: 16, fontSize: 12, color: 'var(--text-muted)', textAlign: 'center',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    CI: {Math.round(result.confidence_lower * 100)}% – {Math.round(result.confidence_upper * 100)}%
                    &nbsp;·&nbsp; {result.model_name} v{result.model_version}
                  </div>
                </div>

                {/* Explanation */}
                <div className="card" style={{ padding: 18 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 10, color: 'var(--accent-cyan)' }}>
                    Clinical Summary
                  </div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.65, margin: 0 }}>
                    {result.clinical_explanation}
                  </p>
                </div>

                {/* SHAP */}
                {result.top_features?.length > 0 && (
                  <div className="card" style={{ padding: 18 }}>
                    <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 14 }}>Feature Contributions (SHAP)</div>
                    <FeatureChart features={result.top_features} />
                  </div>
                )}

                {/* Actions */}
                <div className="card" style={{ padding: 18 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 10, color: 'var(--risk-medium)' }}>
                    Recommended Actions
                  </div>
                  {result.recommended_actions.map((a, i) => (
                    <div key={i} style={{ display: 'flex', gap: 8, padding: '5px 0', fontSize: 12, color: 'var(--text-secondary)', borderBottom: i < result.recommended_actions.length - 1 ? '1px solid var(--border-subtle)' : 'none' }}>
                      <span style={{ color: 'var(--accent-cyan)' }}>›</span> {a}
                    </div>
                  ))}
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="card"
                style={{ padding: 60, textAlign: 'center', color: 'var(--text-muted)' }}
              >
                <Activity size={32} style={{ margin: '0 auto 12px', opacity: 0.3 }} />
                <p style={{ fontSize: 13, margin: 0 }}>Enter patient data and click Predict Risk</p>
                <p style={{ fontSize: 12, margin: '6px 0 0', color: 'var(--text-muted)' }}>
                  Or click <strong>Demo</strong> to see a synthetic example
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
