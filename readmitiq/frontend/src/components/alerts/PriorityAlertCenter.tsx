import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, X, Shield, Activity } from 'lucide-react'
import type { AlertPayload } from '../../hooks/useAlertStream'

/**
 * PriorityAlertCenter — Displays critical/warning alerts as floating cards.
 * Only shown when there are active HIGH-risk alerts.
 */
export default function PriorityAlertCenter({
  alerts,
  onDismiss,
}: {
  alerts: AlertPayload[]
  onDismiss: (id: string) => void
}) {
  if (!alerts || alerts.length === 0) return null

  // Only show HIGH tier alerts (regardless of priority field)
  const criticalAlerts = alerts.filter(a => a.risk_tier === 'HIGH').slice(0, 3)
  if (criticalAlerts.length === 0) return null

  return (
    <div style={{
      position: 'fixed', top: 80, right: 24, zIndex: 200,
      display: 'flex', flexDirection: 'column', gap: 10,
      width: 340, pointerEvents: 'none',
    }}>
      <AnimatePresence>
        {criticalAlerts.map(alert => {
          const isCritical = (alert.risk_score ?? 0) >= 0.8

          return (
            <motion.div
              key={alert.alert_id}
              initial={{ opacity: 0, x: 40, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 40, scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 300, damping: 25 }}
              style={{
                pointerEvents: 'auto',
                borderRadius: 14,
                overflow: 'hidden',
                background: '#FFFFFF',
                border: `1px solid ${isCritical ? 'rgba(239,70,35,0.25)' : 'rgba(255,140,0,0.25)'}`,
                boxShadow: `0 8px 32px ${isCritical ? 'rgba(239,70,35,0.12)' : 'rgba(255,140,0,0.12)'}`,
              }}
            >
              {/* Header bar */}
              <div style={{
                padding: '8px 14px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                background: isCritical ? 'rgba(239,70,35,0.06)' : 'rgba(255,140,0,0.06)',
              }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-mono)',
                  textTransform: 'uppercase', letterSpacing: '0.06em',
                  color: isCritical ? '#EF4623' : '#FF8C00',
                }}>
                  {isCritical
                    ? <><AlertTriangle size={12} /> Critical Risk</>
                    : <><Shield size={12} /> Warning</>
                  }
                </div>
                <button
                  onClick={() => onDismiss(alert.alert_id)}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-muted)', padding: 2,
                  }}
                >
                  <X size={14} />
                </button>
              </div>

              {/* Body */}
              <div style={{ padding: '12px 14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 600,
                    color: '#2D3B42',
                  }}>
                    {alert.patient_mrn}
                  </span>
                  <span style={{
                    fontFamily: 'var(--font-mono)', fontSize: 16, fontWeight: 700,
                    color: isCritical ? '#EF4623' : '#FF8C00',
                  }}>
                    {Math.round((alert.risk_score ?? 0) * 100)}%
                  </span>
                </div>

                {/* AI explanation or recommended action */}
                <div style={{
                  fontSize: 11, lineHeight: 1.5, color: '#5A6B75',
                  padding: '8px 10px', marginBottom: 8,
                  background: 'rgba(45,59,66,0.03)', borderRadius: 6,
                  borderLeft: `2px solid ${isCritical ? '#EF4623' : '#FF8C00'}`,
                }}>
                  {alert.ai_explanation || alert.recommended_action || 'Review patient urgently'}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Activity size={11} color="var(--accent-cyan)" />
                  <span style={{ fontSize: 10, color: '#8A9AA3' }}>
                    {alert.recommended_action}
                  </span>
                </div>
              </div>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
