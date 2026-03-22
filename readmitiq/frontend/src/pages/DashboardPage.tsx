import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, PieChart, Pie, Legend,
} from 'recharts'
import {
  Users, TrendingUp, AlertTriangle, Activity,
  ChevronRight, RefreshCw,
} from 'lucide-react'
import { patientsAPI, cohortAPI } from '../services/api'
import { useNavigate } from 'react-router-dom'
import { useAlertStream } from '../hooks/useAlertStream'

// ── Stat card ─────────────────────────────────────────────────
function StatCard({ label, value, sub, color, icon: Icon, trend }: {
  label: string; value: string | number; sub?: string;
  color: string; icon: React.ElementType; trend?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="card"
      style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 8 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          {label}
        </div>
        <div style={{ color, padding: 6, borderRadius: 6, background: `${color}18` }}>
          <Icon size={14} />
        </div>
      </div>
      <div style={{ fontSize: 32, fontWeight: 700, fontFamily: 'var(--font-display)', color, lineHeight: 1 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sub}</div>}
      {trend !== undefined && (
        <div style={{ fontSize: 11, color: trend >= 0 ? 'var(--risk-high)' : 'var(--risk-low)' }}>
          {trend >= 0 ? '▲' : '▼'} {Math.abs(trend)}% from yesterday
        </div>
      )}
    </motion.div>
  )
}

// ── Risk distribution donut ───────────────────────────────────
function RiskDonut({ high, medium, low }: { high: number; medium: number; low: number }) {
  const data = [
    { name: 'High Risk',   value: high,   color: 'var(--risk-high)' },
    { name: 'Medium Risk', value: medium, color: 'var(--risk-medium)' },
    { name: 'Low Risk',    value: low,    color: 'var(--risk-low)' },
  ]
  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} opacity={0.85} />
          ))}
        </Pie>
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(val) => <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{val}</span>}
        />
        <Tooltip
          formatter={(val: number) => [`${val} patients`, '']}
          contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13 }}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}

// ── Heatmap grid ──────────────────────────────────────────────
function RiskHeatmapGrid() {
  const { data: heatmap = [] } = useQuery({
    queryKey: ['heatmap'],
    queryFn: () => patientsAPI.heatmap(80),
    refetchInterval: 60_000,
  })
  const navigate = useNavigate()

  const tierColor = (tier: string) =>
    tier === 'HIGH' ? 'var(--risk-high)' :
    tier === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(52px, 1fr))',
      gap: 4,
    }}>
      {heatmap.map((p) => (
        <div
          key={p.patient_id}
          onClick={() => navigate(`/patients/${p.patient_id}`)}
          title={`${p.mrn}\nRisk: ${Math.round(p.risk_score * 100)}%\n${p.primary_diagnosis || ''}`}
          style={{
            height: 38,
            borderRadius: 4,
            background: `${tierColor(p.risk_tier)}${Math.round(p.risk_score * 150 + 40).toString(16).padStart(2, '0')}`,
            border: `1px solid ${tierColor(p.risk_tier)}40`,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 10,
            fontFamily: 'var(--font-mono)',
            color: 'rgba(255,255,255,0.7)',
            transition: 'transform 0.1s, box-shadow 0.1s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.transform = 'scale(1.15)'
            ;(e.currentTarget as HTMLElement).style.zIndex = '10'
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.transform = 'scale(1)'
            ;(e.currentTarget as HTMLElement).style.zIndex = '1'
          }}
        >
          {Math.round(p.risk_score * 100)}
        </div>
      ))}
    </div>
  )
}

// ── Live alert feed ───────────────────────────────────────────
function LiveAlerts() {
  const { alerts, connected } = useAlertStream(8)

  const tierColor = (tier: string) =>
    tier === 'HIGH' ? 'var(--risk-high)' :
    tier === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <div style={{
          width: 6, height: 6, borderRadius: '50%',
          background: connected ? 'var(--risk-low)' : 'var(--text-muted)',
          animation: connected ? 'pulse-ring 1.5s infinite' : 'none',
        }} />
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Live Feed
        </span>
      </div>
      {alerts.slice(0, 6).map((a) => (
        <motion.div
          key={a.alert_id}
          initial={{ opacity: 0, x: 16 }}
          animate={{ opacity: 1, x: 0 }}
          style={{
            padding: '10px 12px',
            borderRadius: 8,
            background: a.risk_tier === 'HIGH' ? 'var(--risk-high-bg)' : 'rgba(255,255,255,0.02)',
            border: `1px solid ${tierColor(a.risk_tier)}30`,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <div style={{
            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
            background: tierColor(a.risk_tier),
          }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 500, display: 'flex', justifyContent: 'space-between' }}>
              <span>{a.patient_mrn}</span>
              <span style={{ color: tierColor(a.risk_tier), fontFamily: 'var(--font-mono)', fontSize: 12 }}>
                {Math.round(a.risk_score * 100)}%
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {a.recommended_action}
            </div>
          </div>
        </motion.div>
      ))}
      {alerts.length === 0 && (
        <div style={{ fontSize: 13, color: 'var(--text-muted)', padding: 16, textAlign: 'center' }}>
          Awaiting patient assessments...
        </div>
      )}
    </div>
  )
}

// Weekly trend data fetched from API (replaces old MOCK_TREND)

// ── Main ─────────────────────────────────────────────────────
export default function DashboardPage() {
  const { data: stats, isLoading, refetch } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: patientsAPI.stats,
    refetchInterval: 30_000,
  })

  const { data: trendData = [] } = useQuery({
    queryKey: ['dashboard-trend'],
    queryFn: patientsAPI.trend,
    refetchInterval: 60_000,
  })

  if (isLoading || !stats) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card skeleton" style={{ height: 120 }} />
        ))}
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: 0, letterSpacing: '-0.02em' }}>
            Clinical Dashboard
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '4px 0 0' }}>
            {stats.total_active_admissions} active admissions · Model AUC {(stats.model_accuracy * 100).toFixed(1)}%
          </p>
        </div>
        <button className="btn-ghost" onClick={() => refetch()} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <RefreshCw size={13} /> Refresh
        </button>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        <StatCard label="Total Patients"  value={stats.total_active_admissions} icon={Users}          color="var(--accent-cyan)"   sub="Active admissions" />
        <StatCard label="High Risk"       value={stats.high_risk_count}         icon={AlertTriangle}  color="var(--risk-high)"     trend={+8} />
        <StatCard label="Medium Risk"     value={stats.medium_risk_count}       icon={TrendingUp}     color="var(--risk-medium)"   sub="Need monitoring" />
        <StatCard label="Avg Risk Score"  value={`${(stats.avg_risk_score * 100).toFixed(1)}%`} icon={Activity} color="var(--accent-blue)" sub="Across all admissions" />
      </div>

      {/* Middle row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 320px', gap: 16 }}>

        {/* Trend chart */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Weekly Risk Trend</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={trendData} barSize={12}>
              <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
                cursor={{ fill: 'rgba(255,255,255,0.03)' }}
              />
              <Bar dataKey="high"   stackId="a" fill="var(--risk-high)"   radius={[0,0,0,0]} />
              <Bar dataKey="medium" stackId="a" fill="var(--risk-medium)" />
              <Bar dataKey="low"    stackId="a" fill="var(--risk-low)"    radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Distribution donut */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Risk Distribution</div>
          <RiskDonut
            high={stats.high_risk_count}
            medium={stats.medium_risk_count}
            low={stats.low_risk_count}
          />
        </div>

        {/* Live alerts */}
        <div className="card" style={{ padding: 16 }}>
          <LiveAlerts />
        </div>
      </div>

      {/* Heatmap */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600 }}>Patient Risk Heatmap</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
              Each cell = 1 patient · Color intensity = risk score · Click to view
            </div>
          </div>
          <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-muted)' }}>
            {[['var(--risk-high)', 'High'], ['var(--risk-medium)', 'Medium'], ['var(--risk-low)', 'Low']].map(([c, l]) => (
              <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 8, height: 8, borderRadius: 2, background: c as string, display: 'inline-block' }} />
                {l}
              </span>
            ))}
          </div>
        </div>
        <RiskHeatmapGrid />
      </div>
    </div>
  )
}
