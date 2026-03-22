import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  PieChart, Pie, Legend,
} from 'recharts'
import {
  DollarSign, TrendingDown, Shield, Building2,
  ArrowUpRight, Loader2,
} from 'lucide-react'
import { financialsAPI, FinancialROI } from '../services/api'

function formatMoney(val: number): string {
  if (val >= 1_000_000) return `$${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `$${(val / 1_000).toFixed(0)}K`
  return `$${val.toFixed(0)}`
}

function MetricCard({ label, value, sub, icon: Icon, color, delay = 0 }: {
  label: string; value: string; sub?: string; icon: React.ElementType; color: string; delay?: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay }}
      className="card" style={{ padding: '20px 22px' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {label}
        </div>
        <div style={{ padding: 6, borderRadius: 6, background: `${color}18` }}>
          <Icon size={14} color={color} />
        </div>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, fontFamily: 'var(--font-display)', color, lineHeight: 1, marginBottom: 4 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{sub}</div>}
    </motion.div>
  )
}

export default function FinancialsPage() {
  const { data: roi, isLoading, error } = useQuery({
    queryKey: ['financial-roi'],
    queryFn: financialsAPI.roi,
    refetchInterval: 120_000,
  })

  if (isLoading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 80 }}>
        <Loader2 size={24} className="animate-spin" style={{ color: 'var(--accent-cyan)', marginBottom: 12 }} />
        <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>Computing financial impact...</p>
      </div>
    )
  }

  if (error || !roi) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <p style={{ color: 'var(--risk-high)' }}>Failed to load financial data</p>
      </div>
    )
  }

  const tierPieData = roi.tier_breakdown.map(t => ({
    name: `${t.tier} Risk`,
    value: t.net_savings,
    color: t.tier === 'HIGH' ? 'var(--risk-high)' : t.tier === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)',
  }))

  const barData = roi.tier_breakdown.map(t => ({
    tier: t.tier,
    savings: t.savings,
    cost: t.intervention_cost,
    net: t.net_savings,
    prevented: t.prevented_readmissions,
    patients: t.patient_count,
  }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1200 }}>

      {/* Header */}
      <div>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: 0, letterSpacing: '-0.02em' }}>
          Financial Impact & ROI
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '4px 0 0' }}>
          Cost savings from ML-driven readmission prevention · {roi.total_patients_analyzed} patients analyzed
        </p>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        <MetricCard label="Net Savings" value={formatMoney(roi.net_savings)} sub={`${roi.estimated_preventable_readmissions} readmissions prevented`} icon={DollarSign} color="var(--risk-low)" delay={0} />
        <MetricCard label="CMS Penalty Avoided" value={formatMoney(roi.cms_penalty_avoided)} sub="HRRP penalty prevention" icon={Shield} color="var(--accent-cyan)" delay={0.05} />
        <MetricCard label="ROI" value={`${roi.roi_percentage}%`} sub="Return on intervention investment" icon={ArrowUpRight} color="var(--accent-blue)" delay={0.1} />
        <MetricCard label="Cost per Outcome" value={`$${roi.cost_per_quality_adjusted_outcome.toFixed(0)}`} sub="Per prevented readmission" icon={Building2} color="var(--accent-violet)" delay={0.15} />
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>

        {/* Tier breakdown bar chart */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Savings by Risk Tier</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={barData} barSize={20}>
              <XAxis dataKey="tier" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false}
                tickFormatter={v => formatMoney(v)} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
                formatter={(val: number, name: string) => [formatMoney(val), name === 'savings' ? 'Gross Savings' : name === 'cost' ? 'Intervention Cost' : 'Net Savings']}
              />
              <Bar dataKey="savings" fill="var(--risk-low)" opacity={0.7} radius={[4, 4, 0, 0]} name="Gross Savings" />
              <Bar dataKey="cost" fill="var(--risk-medium)" opacity={0.6} radius={[4, 4, 0, 0]} name="Intervention Cost" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Net savings pie */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Net Savings Distribution</div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={tierPieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80}
                paddingAngle={3} dataKey="value">
                {tierPieData.map((entry, i) => (
                  <Cell key={i} fill={entry.color} opacity={0.85} />
                ))}
              </Pie>
              <Legend iconType="circle" iconSize={8}
                formatter={(val) => <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{val}</span>} />
              <Tooltip
                contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
                formatter={(val: number) => [formatMoney(val), 'Net Savings']}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed breakdown */}
      <div className="card" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Detailed Tier Breakdown</div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Risk Tier</th>
              <th>Patients</th>
              <th>Prevented Readmissions</th>
              <th>Gross Savings</th>
              <th>Intervention Cost</th>
              <th>Net Savings</th>
            </tr>
          </thead>
          <tbody>
            {roi.tier_breakdown.map(t => (
              <tr key={t.tier}>
                <td>
                  <span style={{
                    padding: '3px 10px', borderRadius: 4, fontSize: 11, fontWeight: 600,
                    fontFamily: 'var(--font-mono)',
                    background: t.tier === 'HIGH' ? 'var(--risk-high-bg)' : t.tier === 'MEDIUM' ? 'var(--risk-medium-bg)' : 'var(--risk-low-bg)',
                    color: t.tier === 'HIGH' ? 'var(--risk-high)' : t.tier === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)',
                  }}>
                    {t.tier}
                  </span>
                </td>
                <td style={{ fontFamily: 'var(--font-mono)' }}>{t.patient_count}</td>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>{t.prevented_readmissions}</td>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--risk-low)' }}>{formatMoney(t.savings)}</td>
                <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--risk-medium)' }}>{formatMoney(t.intervention_cost)}</td>
                <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: t.net_savings > 0 ? 'var(--risk-low)' : 'var(--risk-high)' }}>
                  {formatMoney(t.net_savings)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
