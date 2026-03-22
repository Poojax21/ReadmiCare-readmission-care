import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Search, ChevronRight, User, UserPlus } from 'lucide-react'
import { patientsAPI, PatientSummary } from '../services/api'
import NewPatientModal from '../components/patients/NewPatientModal'

const TIERS = ['ALL', 'HIGH', 'MEDIUM', 'LOW']

function RiskBar({ score }: { score: number }) {
  const color =
    score >= 0.70 ? 'var(--risk-high)' :
    score >= 0.40 ? 'var(--risk-medium)' : 'var(--risk-low)'
  return (
    <div className="risk-bar" style={{ width: 80 }}>
      <div className="risk-bar-fill" style={{ width: `${score * 100}%`, background: color }} />
    </div>
  )
}

function TierBadge({ tier }: { tier: string }) {
  const cls = tier === 'HIGH' ? 'badge-high' : tier === 'MEDIUM' ? 'badge-medium' : 'badge-low'
  return (
    <span className={cls} style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
      {tier}
    </span>
  )
}

export default function PatientsPage() {
  const [search, setSearch] = useState('')
  const [tier, setTier] = useState('ALL')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const navigate = useNavigate()

  const { data: patients = [], isLoading } = useQuery({
    queryKey: ['patients', search, tier],
    queryFn: () => patientsAPI.list({
      search: search || undefined,
      risk_tier: tier === 'ALL' ? undefined : tier,
      limit: 100,
    }),
    refetchInterval: 60_000,
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* Header */}
      <div>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: 0 }}>Patients</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '4px 0 0' }}>
          {patients.length} patients · sorted by risk score
        </p>
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: 320 }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            className="input-field"
            style={{ paddingLeft: 36 }}
            placeholder="Search by name or MRN..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {TIERS.map(t => (
            <button
              key={t}
              onClick={() => setTier(t)}
              style={{
                padding: '7px 14px',
                borderRadius: 6,
                border: '1px solid',
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'var(--font-mono)',
                transition: 'all 0.15s',
                background: tier === t ? (
                  t === 'HIGH' ? 'var(--risk-high-bg)' :
                  t === 'MEDIUM' ? 'var(--risk-medium-bg)' :
                  t === 'LOW' ? 'var(--risk-low-bg)' : 'rgba(0,212,255,0.08)'
                ) : 'transparent',
                borderColor: tier === t ? (
                  t === 'HIGH' ? 'var(--risk-high)' :
                  t === 'MEDIUM' ? 'var(--risk-medium)' :
                  t === 'LOW' ? 'var(--risk-low)' : 'var(--accent-cyan)'
                ) : 'var(--border)',
                color: tier === t ? (
                  t === 'HIGH' ? 'var(--risk-high)' :
                  t === 'MEDIUM' ? 'var(--risk-medium)' :
                  t === 'LOW' ? 'var(--risk-low)' : 'var(--accent-cyan)'
                ) : 'var(--text-muted)',
              }}
            >
              {t}
            </button>
          ))}
          <button 
            onClick={() => setIsModalOpen(true)}
            className="btn-primary" 
            style={{ marginLeft: 8, height: 32, padding: '0 16px', fontSize: 12 }}
          >
            <UserPlus size={14} style={{ marginRight: 6 }} />
            Add Patient
          </button>
        </div>
      </div>

      <NewPatientModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
      />

      {/* Table */}
      <div className="card" style={{ overflow: 'hidden' }}>
        {isLoading ? (
          <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading patients...
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Patient</th>
                <th>Age / Sex</th>
                <th>Diagnosis</th>
                <th>Ward</th>
                <th>Attending</th>
                <th>Risk Score</th>
                <th>Tier</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {[...patients]
                .sort((a, b) => (b.latest_risk_score ?? 0) - (a.latest_risk_score ?? 0))
                .map((p, i) => (
                <motion.tr
                  key={p.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.015 }}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/patients/${p.id}`)}
                >
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: '50%',
                        background: 'linear-gradient(135deg, rgba(0,212,255,0.1), rgba(139,92,246,0.1))',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        flexShrink: 0,
                      }}>
                        <User size={14} color="var(--accent-cyan)" />
                      </div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.3 }}>
                          {p.full_name || `${p.first_name || ''} ${p.last_name || ''}`.trim() || p.mrn}
                        </div>
                        <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {p.mrn}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td style={{ color: 'var(--text-secondary)' }}>
                    {p.age ?? '—'}y · {p.gender ?? '—'}
                  </td>
                  <td>
                    <div>
                      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        {p.primary_diagnosis_name || '—'}
                      </div>
                      <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                        {p.primary_diagnosis_icd ?? ''}
                      </div>
                    </div>
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {p.ward || '—'}
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {p.attending_physician || '—'}
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <RiskBar score={p.latest_risk_score ?? 0} />
                      <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', minWidth: 36 }}>
                        {p.latest_risk_score ? `${Math.round(p.latest_risk_score * 100)}%` : '—'}
                      </span>
                    </div>
                  </td>
                  <td><TierBadge tier={p.risk_tier ?? 'LOW'} /></td>
                  <td>
                    <ChevronRight size={14} style={{ color: 'var(--text-muted)' }} />
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
