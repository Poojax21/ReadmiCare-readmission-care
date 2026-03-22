import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { SlidersHorizontal, TrendingDown, TrendingUp, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'
import { simulationAPI, SimulationResult, InterventionImpact } from '../../services/api'

interface SimParam {
  name: string
  label: string
  unit: string
  min: number
  max: number
  step: number
  default: number
}

const SIMULATION_PARAMS: SimParam[] = [
  { name: 'follow_up_days', label: 'Follow-up', unit: 'days', min: 1, max: 30, step: 1, default: 14 },
  { name: 'creatinine_max', label: 'Creatinine', unit: 'mg/dL', min: 0.5, max: 5.0, step: 0.1, default: 1.5 },
  { name: 'albumin_min', label: 'Albumin', unit: 'g/dL', min: 1.5, max: 5.0, step: 0.1, default: 3.0 },
  { name: 'hemoglobin_min', label: 'Hemoglobin', unit: 'g/dL', min: 6.0, max: 18.0, step: 0.1, default: 10.5 },
  { name: 'spo2_min', label: 'SpO₂', unit: '%', min: 80, max: 100, step: 1, default: 94 },
  { name: 'heart_rate_mean', label: 'Heart Rate', unit: 'bpm', min: 50, max: 140, step: 1, default: 85 },
]

export default function WhatIfSliders({ initialRisk, patientId }: { initialRisk: number; patientId?: string }) {
  const [values, setValues] = useState<Record<string, number>>(
    Object.fromEntries(SIMULATION_PARAMS.map(p => [p.name, p.default]))
  )
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [dirty, setDirty] = useState(false)

  const handleChange = (name: string, val: number) => {
    setValues(prev => ({ ...prev, [name]: val }))
    setDirty(true)
  }

  const runSimulation = async () => {
    if (!patientId) return
    setLoading(true)
    try {
      const response = await simulationAPI.simulate(patientId, values)
      setResult(response)
      setDirty(false)
    } catch {
      // Fallback: local estimation if backend is unreachable
      const delta = Object.entries(values).reduce((sum, [key, val]) => {
        const param = SIMULATION_PARAMS.find(p => p.name === key)
        if (!param) return sum
        const change = val - param.default
        const weight = key.includes('follow') ? -0.018 : key.includes('creatinine') ? 0.045 : 0.005
        return sum + weight * change
      }, 0)
      setResult({
        patient_id: patientId,
        original_risk: initialRisk,
        simulated_risk: Math.max(0.01, Math.min(0.99, initialRisk + delta)),
        risk_delta: delta,
        risk_reduction_pct: -delta / initialRisk * 100,
        intervention_impacts: [],
        recommendation: 'Estimated locally — connect backend for full analysis.',
        confidence: 'LOW',
      })
      setDirty(false)
    } finally {
      setLoading(false)
    }
  }

  const simRisk = result?.simulated_risk ?? initialRisk
  const delta = result ? result.risk_delta : 0
  const improved = delta < -0.005

  return (
    <div className="card" style={{ padding: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
        <div style={{
          width: 28, height: 28, borderRadius: 6,
          background: 'linear-gradient(135deg, rgba(255,140,0,0.15), rgba(239,70,35,0.15))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <SlidersHorizontal size={14} color="var(--risk-medium)" />
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700 }}>What-If Simulation</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Counterfactual analysis
          </div>
        </div>
      </div>

      {/* Sliders */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 14 }}>
        {SIMULATION_PARAMS.map(param => (
          <div key={param.name}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{param.label}</span>
              <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                {values[param.name]}{param.unit}
              </span>
            </div>
            <input
              type="range"
              min={param.min} max={param.max} step={param.step}
              value={values[param.name]}
              onChange={e => handleChange(param.name, Number(e.target.value))}
              style={{ width: '100%', accentColor: 'var(--accent-cyan)', height: 4 }}
            />
          </div>
        ))}
      </div>

      {/* Run button */}
      <button
        onClick={runSimulation}
        disabled={loading || !patientId}
        className="btn-primary"
        style={{
          width: '100%', fontSize: 12, padding: '10px',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          marginBottom: result ? 14 : 0,
        }}
      >
        {loading ? <Loader2 size={13} className="animate-spin" /> : <SlidersHorizontal size={13} />}
        {loading ? 'Simulating...' : dirty ? 'Run Simulation' : 'Re-run'}
      </button>

      {/* Results */}
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
          >
            {/* Risk comparison */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px',
              borderRadius: 8,
              background: improved ? 'rgba(0,180,120,0.06)' : 'rgba(239,70,35,0.06)',
              border: `1px solid ${improved ? 'rgba(0,180,120,0.2)' : 'rgba(239,70,35,0.2)'}`,
              marginBottom: 10,
            }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>Original</div>
                <div style={{ fontSize: 20, fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
                  {Math.round(result.original_risk * 100)}%
                </div>
              </div>
              <div style={{ color: improved ? 'var(--risk-low)' : 'var(--risk-high)', display: 'flex', alignItems: 'center', gap: 4 }}>
                {improved ? <TrendingDown size={16} /> : <TrendingUp size={16} />}
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700 }}>
                  {delta > 0 ? '+' : ''}{Math.round(delta * 100)}%
                </span>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>Simulated</div>
                <div style={{
                  fontSize: 20, fontFamily: 'var(--font-display)',
                  color: improved ? 'var(--risk-low)' : 'var(--risk-high)',
                }}>
                  {Math.round(simRisk * 100)}%
                </div>
              </div>
            </div>

            {/* Recommendation */}
            <div style={{
              fontSize: 11, lineHeight: 1.5, color: 'var(--text-secondary)',
              padding: '8px 10px',
              background: 'var(--bg-surface)',
              borderRadius: 6,
              border: '1px solid var(--border)',
              display: 'flex', gap: 6, alignItems: 'flex-start',
            }}>
              {improved
                ? <CheckCircle size={13} color="var(--risk-low)" style={{ flexShrink: 0, marginTop: 2 }} />
                : <AlertTriangle size={13} color="var(--risk-high)" style={{ flexShrink: 0, marginTop: 2 }} />
              }
              <span>{result.recommendation}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
