import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, Cell,
} from 'recharts'
import { ArrowLeft, AlertTriangle, Activity, Clipboard, ChevronRight } from 'lucide-react'
import { patientsAPI } from '../services/api'
import CopilotChat from '../components/copilot/CopilotChat'
import WhatIfSliders from '../components/simulation/WhatIfSliders'
import RiskTrajectoryChart from '../components/charts/RiskTrajectoryChart'

// ── SHAP Waterfall Chart ───────────────────────────────────────
function SHAPWaterfall({ features }: { features: any[] }) {
  if (!features?.length) return null

  const sorted = [...features]
    .sort((a, b) => Math.abs(b.shap_value) - Math.abs(a.shap_value))
    .slice(0, 12)

  const data = sorted.map(f => ({
    name: (f.label || f.feature || '').replace(/_/g, ' ').slice(0, 22),
    value: f.shap_value,
    feature_value: f.feature_value,
    direction: f.direction,
  }))

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 14px', fontSize: 12 }}>
        <div style={{ fontWeight: 600, marginBottom: 4 }}>{d.name}</div>
        <div style={{ color: d.value > 0 ? 'var(--risk-high)' : 'var(--risk-low)' }}>
          SHAP: {d.value > 0 ? '+' : ''}{d.value.toFixed(3)}
        </div>
        {d.feature_value !== null && (
          <div style={{ color: 'var(--text-muted)' }}>Value: {d.feature_value?.toFixed?.(2) ?? d.feature_value}</div>
        )}
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} layout="vertical" barSize={14} margin={{ left: 0, right: 20, top: 4, bottom: 4 }}>
        <XAxis
          type="number"
          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          axisLine={false} tickLine={false}
          tickFormatter={v => v > 0 ? `+${v.toFixed(2)}` : v.toFixed(2)}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={160}
          tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
          axisLine={false} tickLine={false}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine x={0} stroke="var(--border)" strokeDasharray="3 3" />
        <Bar dataKey="value" radius={[0, 3, 3, 0]}>
          {data.map((entry, i) => (
            <Cell
              key={i}
              fill={entry.value > 0 ? 'var(--risk-high)' : 'var(--risk-low)'}
              opacity={0.8 + Math.min(Math.abs(entry.value) * 2, 0.2)}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Risk gauge ────────────────────────────────────────────────
function RiskGauge({ score, tier }: { score: number; tier: string }) {
  const angle = -135 + (score * 270)
  const color =
    tier === 'HIGH' ? 'var(--risk-high)' :
    tier === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'

  return (
    <div style={{ textAlign: 'center', padding: '8px 0' }}>
      {/* Semicircle gauge */}
      <svg viewBox="0 0 160 100" style={{ width: 200, display: 'block', margin: '0 auto' }}>
        {/* Background arc */}
        <path d="M 20,90 A 60,60 0 0,1 140,90" fill="none" stroke="var(--border)" strokeWidth="12" strokeLinecap="round" />
        {/* Colored arc */}
        <path
          d="M 20,90 A 60,60 0 0,1 140,90"
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={`${score * 188} 188`}
          opacity="0.85"
        />
        {/* Needle */}
        <g transform={`rotate(${angle - 90}, 80, 90)`}>
          <line x1="80" y1="90" x2="80" y2="38" stroke={color} strokeWidth="2" strokeLinecap="round" />
        </g>
        <circle cx="80" cy="90" r="5" fill={color} />
        {/* Score text */}
        <text x="80" y="80" textAnchor="middle" fill={color} fontSize="20" fontFamily="Space Mono" fontWeight="700">
          {Math.round(score * 100)}%
        </text>
      </svg>
      <div style={{
        display: 'inline-block',
        padding: '4px 14px',
        borderRadius: 4,
        fontSize: 13,
        fontWeight: 700,
        fontFamily: 'var(--font-mono)',
        background: `${color}20`,
        color,
        border: `1px solid ${color}40`,
        letterSpacing: '0.06em',
      }}>
        {tier} RISK
      </div>
    </div>
  )
}

// ── Main ─────────────────────────────────────────────────────
export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: patient, isLoading, error } = useQuery({
    queryKey: ['patient', id],
    queryFn: () => patientsAPI.get(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return <div style={{ padding: 40, color: 'var(--text-muted)', textAlign: 'center' }}>Loading patient...</div>
  }
  if (error || !patient) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <p style={{ color: 'var(--risk-high)' }}>Patient not found</p>
        <button className="btn-ghost" style={{ marginTop: 12 }} onClick={() => navigate('/patients')}>Back to Patients</button>
      </div>
    )
  }

  const riskScore = patient.risk_score ?? 0
  const riskTier = patient.risk_tier ?? 'LOW'
  const features = patient.top_features ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 1200 }}>

      {/* Back */}
      <button
        onClick={() => navigate('/patients')}
        style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, padding: 0 }}
      >
        <ArrowLeft size={14} /> Back to Patients
      </button>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 26, margin: 0, letterSpacing: '-0.02em' }}>
            {patient.full_name || `${patient.first_name || ''} ${patient.last_name || ''}`.trim() || patient.mrn}
          </h1>
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', margin: '6px 0 0', flexWrap: 'wrap' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--accent-cyan)' }}>
              {patient.mrn}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {patient.age}y · {patient.gender} · {patient.ethnicity || 'Unknown'}
            </span>
            {patient.date_of_birth && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                DOB: {patient.date_of_birth}
              </span>
            )}
            {patient.phone && (
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                ☎ {patient.phone}
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 16, marginTop: 6, flexWrap: 'wrap' }}>
            {patient.ward && (
              <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 4, background: 'rgba(0,212,255,0.06)', color: 'var(--accent-cyan)', fontWeight: 600 }}>
                📍 {patient.ward}
              </span>
            )}
            {patient.attending_physician && (
              <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 4, background: 'rgba(139,92,246,0.06)', color: 'var(--accent-violet)', fontWeight: 600 }}>
                🩺 {patient.attending_physician}
              </span>
            )}
            {patient.insurance_type && (
              <span style={{ fontSize: 11, padding: '3px 10px', borderRadius: 4, background: 'rgba(255,255,255,0.04)', color: 'var(--text-muted)', fontWeight: 500 }}>
                {patient.insurance_type}
              </span>
            )}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {patient.was_readmitted_30d !== undefined && (
            <span style={{
              padding: '4px 12px', borderRadius: 4, fontSize: 12, fontWeight: 600,
              background: patient.was_readmitted_30d ? 'var(--risk-high-bg)' : 'var(--risk-low-bg)',
              color: patient.was_readmitted_30d ? 'var(--risk-high)' : 'var(--risk-low)',
              border: `1px solid ${patient.was_readmitted_30d ? 'rgba(255,69,96,0.3)' : 'rgba(0,227,150,0.3)'}`,
            }}>
              {patient.was_readmitted_30d ? '⚠ Readmitted' : '✓ Not Readmitted'}
            </span>
          )}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 340px', gap: 16 }}>

        {/* Left: Risk gauge + info */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div className="card" style={{ padding: 20 }}>
            <RiskGauge score={riskScore} tier={riskTier} />
            <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)' }}>
                <span>Confidence Interval</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>
                  {Math.round((patient.confidence_lower ?? riskScore * 0.85) * 100)}% – {Math.round((patient.confidence_upper ?? riskScore * 1.15) * 100)}%
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)' }}>
                <span>LOS</span>
                <span style={{ fontFamily: 'var(--font-mono)' }}>{patient.los_days?.toFixed(1) ?? '—'}d</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)' }}>
                <span>Admission Type</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{patient.admission_type ?? '—'}</span>
              </div>
            </div>
          </div>

          {/* Diagnoses */}
          <div className="card" style={{ padding: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Diagnoses
            </div>
            {[patient.primary_diagnosis_icd, ...(patient.comorbidities ?? [])].filter(Boolean).map((code: string) => (
              <div key={code} style={{
                padding: '5px 10px', marginBottom: 4,
                background: 'var(--bg-surface)', borderRadius: 4,
                fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)',
              }}>
                {code}
              </div>
            ))}
          </div>

          {/* Clinical Intervention Engine */}
          <div className="card" style={{ 
            padding: 16, 
            border: '1px solid var(--accent-cyan-40)',
            position: 'relative',
            overflow: 'hidden'
          }}>
            {/* Ambient glow */}
            <div style={{
              position: 'absolute', top: -40, right: -40, width: 80, height: 80,
              background: 'var(--accent-cyan)', filter: 'blur(50px)', opacity: 0.15,
              pointerEvents: 'none'
            }} />
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--accent-cyan)', fontFamily: 'var(--font-mono)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Activity size={12} /> Intervention Engine
              </div>
              <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 3, background: 'var(--accent-cyan)', color: '#000', fontWeight: 800 }}>BETA</span>
            </div>
            
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
              Recommended Actions
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 14, lineHeight: 1.4, fontStyle: 'italic' }}>
              “We don’t just predict risk — we recommend personalized interventions.”
            </div>

            {patient.recommended_actions?.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {patient.recommended_actions.map((action: string, i: number) => (
                  <motion.div 
                    key={i} 
                    initial={{ x: -5, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    transition={{ delay: i * 0.1 }}
                    style={{
                      display: 'flex', gap: 10, alignItems: 'flex-start',
                      padding: '8px 10px',
                      borderRadius: 6,
                      background: 'rgba(255,255,255,0.03)',
                      marginBottom: 4,
                      fontSize: 12, color: 'var(--text-secondary)',
                      border: '1px solid transparent',
                      transition: 'all 0.2s ease',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(0,212,255,0.05)'
                      e.currentTarget.style.borderColor = 'rgba(0,212,255,0.1)'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
                      e.currentTarget.style.borderColor = 'transparent'
                    }}
                  >
                    <div style={{ 
                      width: 16, height: 16, borderRadius: '50%', background: 'var(--accent-cyan)20', 
                      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 
                    }}>
                      <div style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--accent-cyan)' }} />
                    </div>
                    <span style={{ lineHeight: 1.4 }}>{action}</span>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '10px 0' }}>
                No active interventions for this risk tier.
              </div>
            )}
          </div>
          
          {/* What If Simulation Sandbox */}
          <WhatIfSliders initialRisk={riskScore} patientId={id} />
        </div>

        {/* Right: SHAP + explanation */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

          {/* Clinical explanation */}
          {patient.clinical_explanation && (
            <motion.div className="card" style={{ padding: 20 }} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <Clipboard size={16} style={{ color: 'var(--accent-cyan)', marginTop: 2, flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Clinical Summary</div>
                  <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7, margin: 0 }}>
                    {patient.clinical_explanation}
                  </p>
                </div>
              </div>
            </motion.div>
          )}

          {/* SHAP waterfall */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Feature Contributions (SHAP)</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
              <span style={{ color: 'var(--risk-high)' }}>Red</span> = increases risk ·
              <span style={{ color: 'var(--risk-low)' }}> Green</span> = decreases risk
            </div>
            <SHAPWaterfall features={features} />
          </div>
          
          {/* Risk Trajectory Chart */}
          <RiskTrajectoryChart patientId={id} />
        </div>

        {/* Third Column: AI Copilot */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <CopilotChat patientId={id || ''} />
        </div>
      </div>
    </div>
  )
}
