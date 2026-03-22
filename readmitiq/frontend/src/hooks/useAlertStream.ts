import { useEffect, useRef, useState, useCallback } from 'react'

export interface AlertPayload {
  alert_id: string
  patient_mrn: string
  risk_score: number
  risk_tier: 'HIGH' | 'MEDIUM' | 'LOW'
  primary_diagnosis: string
  recommended_action: string
  timestamp: string
  priority?: 'CRITICAL' | 'WARN' | 'INFO'
  ai_explanation?: string
}

export interface WSMessage {
  type: 'patient_alert' | 'dashboard_update' | 'connected'
  payload: AlertPayload | Record<string, unknown>
}

const WS_URL = import.meta.env.VITE_WS_URL || `ws://${window.location.host}/ws/alerts`

export function useAlertStream(maxAlerts = 50) {
  const [alerts, setAlerts] = useState<AlertPayload[]>([])
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        setError(null)
      }

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data)
          if (msg.type === 'patient_alert') {
            const payload = msg.payload as AlertPayload
            setAlerts(prev => [payload, ...prev].slice(0, maxAlerts))
          }
        } catch { /* ignore malformed messages */ }
      }

      ws.onerror = () => {
        setError('WebSocket connection error')
        setConnected(false)
      }

      ws.onclose = () => {
        setConnected(false)
        // Reconnect after 5s
        reconnectTimeout.current = setTimeout(connect, 5000)
      }
    } catch (e) {
      setError('Failed to connect to alert stream')
      reconnectTimeout.current = setTimeout(connect, 8000)
    }
  }, [maxAlerts])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimeout.current)
      wsRef.current?.close()
    }
  }, [connect])

  const dismiss = useCallback((alertId: string) => {
    setAlerts(prev => prev.filter(a => a.alert_id !== alertId))
  }, [])

  return { alerts, connected, error, dismiss }
}
