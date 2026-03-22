import { useQuery } from '@tanstack/react-query'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { Activity, Loader2 } from 'lucide-react'
import { patientsAPI } from '../../services/api'

export default function RiskTrajectoryChart({ patientId }: { patientId?: string }) {
  const { data: trajectoryData, isLoading } = useQuery({
    queryKey: ['trajectory', patientId],
    queryFn: () => patientsAPI.trajectory(patientId!, 24),
    enabled: !!patientId,
    refetchInterval: 120_000,
  })

  if (!patientId) {
    return (
      <div className="card" style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>
        <Activity size={20} style={{ opacity: 0.3, margin: '0 auto 8px' }} />
        <p style={{ fontSize: 12 }}>Select a patient to view trajectory</p>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="card" style={{ padding: 20, textAlign: 'center' }}>
        <Loader2 size={16} className="animate-spin" style={{ margin: '0 auto 8px', color: 'var(--accent-cyan)' }} />
        <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Loading trajectory...</p>
      </div>
    )
  }

  const trajectory = trajectoryData?.trajectory ?? []
  const currentRisk = trajectoryData?.current_risk ?? 0
  const currentTier = trajectoryData?.current_tier ?? 'MEDIUM'

  // Format data for the chart
  const chartData = trajectory.map(point => ({
    hour: `${point.hour_offset}h`,
    risk: Math.round(point.risk_score * 100),
    rawRisk: point.risk_score,
    tier: point.risk_tier,
  }))

  const tierColor = currentTier === 'HIGH' ? 'var(--risk-high)' : currentTier === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    const color = d.tier === 'HIGH' ? 'var(--risk-high)' : d.tier === 'MEDIUM' ? 'var(--risk-medium)' : 'var(--risk-low)'
    return (
      <div style={{
        background: 'var(--bg-elevated)', border: '1px solid var(--border)',
        borderRadius: 8, padding: '8px 12px', fontSize: 11,
      }}>
        <div style={{ fontWeight: 600, marginBottom: 3 }}>{d.hour}</div>
        <div style={{ color, fontFamily: 'var(--font-mono)' }}>
          Risk: {d.risk}%
          <span style={{ marginLeft: 8, fontSize: 10, opacity: 0.8 }}>{d.tier}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="card" style={{ padding: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700 }}>Risk Trajectory</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            24-hour risk evolution
          </div>
        </div>
        <div style={{
          fontSize: 18, fontFamily: 'var(--font-display)', fontWeight: 700, color: tierColor,
        }}>
          {Math.round(currentRisk * 100)}%
        </div>
      </div>

      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={tierColor} stopOpacity={0.25} />
              <stop offset="95%" stopColor={tierColor} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="hour" interval={5}
            tick={{ fill: 'var(--text-muted)', fontSize: 9 }}
            axisLine={false} tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: 'var(--text-muted)', fontSize: 9 }}
            axisLine={false} tickLine={false}
            tickFormatter={v => `${v}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={70} stroke="var(--risk-high)" strokeDasharray="3 3" strokeOpacity={0.4} />
          <ReferenceLine y={40} stroke="var(--risk-medium)" strokeDasharray="3 3" strokeOpacity={0.3} />
          <Area
            type="monotone" dataKey="risk"
            stroke={tierColor} strokeWidth={2}
            fill="url(#riskGradient)"
            dot={false}
            activeDot={{ r: 4, fill: tierColor }}
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Threshold legend */}
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginTop: 6, fontSize: 9, color: 'var(--text-muted)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <span style={{ width: 16, height: 1, background: 'var(--risk-high)', display: 'inline-block', borderRadius: 1 }} />
          High (70%)
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <span style={{ width: 16, height: 1, background: 'var(--risk-medium)', display: 'inline-block', borderRadius: 1 }} />
          Medium (40%)
        </span>
      </div>
    </div>
  )
}
