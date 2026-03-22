import { Outlet, NavLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Users, Zap, Brain, Bell, Activity,
  Wifi, WifiOff,
} from 'lucide-react'
import { useAlertStream } from '../../hooks/useAlertStream'
import { useState, useCallback } from 'react'
import toast from 'react-hot-toast'
import PriorityAlertCenter from '../alerts/PriorityAlertCenter'

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/patients',  icon: Users,           label: 'Patients' },
  { to: '/predict',   icon: Zap,             label: 'Predict Risk' },
  { to: '/model',     icon: Brain,           label: 'Model' },
  { to: '/financials',icon: Activity,        label: 'Financials' },
]

export default function Layout() {
  const { alerts, connected } = useAlertStream(20)
  const [alertPanelOpen, setAlertPanelOpen] = useState(false)
  
  // Custom dismiss for PriorityAlertCenter
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set())
  const handleDismissAlert = useCallback((id: string) => {
    setDismissedAlerts(prev => new Set(prev).add(id))
  }, [])
  
  const activeAlerts = alerts.filter(a => !dismissedAlerts.has(a.alert_id))
  const highRisk = activeAlerts.filter(a => a.risk_tier === 'HIGH').length

  // Show toast for HIGH risk alerts
  const seenAlerts = new Set<string>()
  alerts.forEach(a => {
    if (a.risk_tier === 'HIGH' && !seenAlerts.has(a.alert_id)) {
      seenAlerts.add(a.alert_id)
    }
  })

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#FFFFFF' }}>
      {/* ── Sidebar ───────────────────────────────────────────── */}
      <aside style={{
        width: 260,
        flexShrink: 0,
        background: '#FDF1EE',
        borderRight: '1px solid rgba(45, 59, 66, 0.06)',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px 16px',
        position: 'sticky',
        top: 0,
        height: '100vh',
      }}>
        {/* Logo */}
        <div style={{ padding: '8px 12px 32px' }}>
          <div style={{
            fontFamily: 'var(--font-serif)',
            fontSize: 22,
            color: '#2D3B42',
            letterSpacing: '-0.02em',
            display: 'flex',
            alignItems: 'center',
            gap: 10,
          }}>
            <div 
              className="logo-container"
              style={{
                width: 36,
                height: 36,
                background: '#EF4623',
                borderRadius: 8,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontFamily: 'var(--font-serif)',
                fontStyle: 'italic',
                fontWeight: 700,
                fontSize: 18,
              }}
            >
              R
            </div>
            ReadmitIQ
          </div>
          <div style={{ fontSize: 12, color: '#8A9AA3', marginTop: 4, paddingLeft: 46, fontWeight: 500 }}>
            Readmission Intelligence
          </div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              style={({ isActive }) => ({
                background: isActive ? 'rgba(239, 70, 35, 0.08)' : 'transparent',
                color: isActive ? '#EF4623' : '#5A6B75',
                fontWeight: isActive ? 600 : 500,
              })}
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Connection status */}
        <div style={{
          padding: '16px 12px',
          borderTop: '1px solid rgba(45, 59, 66, 0.06)',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          fontSize: 12,
          fontWeight: 500,
          color: connected ? '#00B478' : '#8A9AA3',
        }}>
          {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
          {connected ? 'Live Stream' : 'Connecting...'}
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Glassmorphism Top bar */}
        <header className="glass" style={{
          height: 72,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 32px',
          flexShrink: 0,
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}>
          <div style={{ fontSize: 13, color: '#8A9AA3', fontFamily: 'var(--font-sans)', fontWeight: 500 }}>
            {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
          </div>

          {/* Alert bell */}
          <button
            onClick={() => setAlertPanelOpen(p => !p)}
            style={{
              position: 'relative',
              background: highRisk > 0 ? 'rgba(239, 70, 35, 0.08)' : 'transparent',
              border: '1px solid rgba(45, 59, 66, 0.1)',
              borderRadius: '24px',
              padding: '10px 18px',
              color: highRisk > 0 ? '#EF4623' : '#5A6B75',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 13,
              fontWeight: 500,
              transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          >
            <Bell size={16} />
            {highRisk > 0 && (
              <span style={{
                background: '#EF4623',
                color: 'white',
                borderRadius: '99px',
                fontSize: 10,
                fontWeight: 700,
                padding: '2px 8px',
              }}>
                {highRisk}
              </span>
            )}
            Alerts
          </button>
        </header>

        {/* Alert panel */}
        <AnimatePresence>
          {alertPanelOpen && (
            <motion.div
              initial={{ opacity: 0, y: -12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -12, scale: 0.98 }}
              style={{
                position: 'absolute',
                right: 32,
                top: 82,
                width: 380,
                maxHeight: 520,
                overflowY: 'auto',
                background: '#FFFFFF',
                border: '1px solid rgba(45, 59, 66, 0.08)',
                borderRadius: '24px',
                boxShadow: '0 20px 60px rgba(45, 59, 66, 0.12)',
                zIndex: 100,
              }}
            >
              <div style={{ padding: '18px 20px', borderBottom: '1px solid rgba(45, 59, 66, 0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 14, fontWeight: 600, fontFamily: 'var(--font-serif)' }}>Recent Alerts</span>
                <span style={{ fontSize: 12, color: '#8A9AA3' }}>{alerts.length} total</span>
              </div>
              {alerts.length === 0 ? (
                <div style={{ padding: 32, textAlign: 'center', color: '#8A9AA3', fontSize: 14 }}>
                  No alerts yet
                </div>
              ) : (
                alerts.slice(0, 12).map((a) => (
                  <div key={a.alert_id} style={{
                    padding: '14px 20px',
                    borderBottom: '1px solid rgba(45, 59, 66, 0.04)',
                    display: 'flex',
                    gap: 14,
                    alignItems: 'flex-start',
                    transition: 'background 0.2s',
                  }}>
                    <div style={{
                      width: 10, height: 10, borderRadius: '50%', marginTop: 5, flexShrink: 0,
                      background: a.risk_tier === 'HIGH' ? '#EF4623' : a.risk_tier === 'MEDIUM' ? '#FF8C00' : '#00B478',
                    }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4, color: '#2D3B42' }}>
                        {a.patient_mrn}
                        <span style={{
                          marginLeft: 10, fontSize: 11, padding: '3px 10px', borderRadius: '12px',
                          background: a.risk_tier === 'HIGH' ? 'rgba(239, 70, 35, 0.1)' : a.risk_tier === 'MEDIUM' ? 'rgba(255, 140, 0, 0.1)' : 'rgba(0, 180, 120, 0.1)',
                          color: a.risk_tier === 'HIGH' ? '#EF4623' : a.risk_tier === 'MEDIUM' ? '#FF8C00' : '#00B478',
                          fontWeight: 600,
                        }}>
                          {a.risk_tier} {Math.round(a.risk_score * 100)}%
                        </span>
                      </div>
                      <div style={{ fontSize: 13, color: '#8A9AA3' }}>{a.recommended_action}</div>
                    </div>
                  </div>
                ))
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <PriorityAlertCenter alerts={activeAlerts} onDismiss={handleDismissAlert} />

        {/* Page content */}
        <main style={{ flex: 1, overflow: 'auto', padding: '32px' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
