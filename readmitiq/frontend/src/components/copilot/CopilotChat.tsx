import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Bot, User, Sparkles, Loader2, BookOpen } from 'lucide-react'
import { copilotAPI, CopilotResponse } from '../../services/api'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  references?: string[]
  conditions?: string[]
  riskContext?: { score: number; tier: string; top_driver: string }
  timestamp: Date
}

const QUICK_PROMPTS = [
  "Why is this patient high risk?",
  "What should I do to reduce risk?",
  "Compare with similar patients",
  "Review medication plan",
]

export default function CopilotChat({ patientId }: { patientId: string }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading || !patientId) return
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const response: CopilotResponse = await copilotAPI.query(patientId, text.trim())
      const assistantMsg: Message = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: response.answer,
        references: response.clinical_references,
        conditions: response.matched_conditions,
        riskContext: response.risk_context,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch {
      setMessages(prev => [...prev, {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: 'Unable to process your query. Please ensure the backend is running and try again.',
        timestamp: new Date(),
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card" style={{
      display: 'flex', flexDirection: 'column',
      height: 520, overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 18px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10,
        background: 'linear-gradient(135deg, rgba(0,212,255,0.04), rgba(139,92,246,0.04))',
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: 'linear-gradient(135deg, #00d4ff, #8b5cf6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Sparkles size={16} color="white" />
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, letterSpacing: '-0.01em' }}>AI Clinical Copilot</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            Evidence-based reasoning
          </div>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} style={{
        flex: 1, overflowY: 'auto', padding: '12px 14px',
        display: 'flex', flexDirection: 'column', gap: 10,
      }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '24px 8px' }}>
            <Bot size={28} style={{ margin: '0 auto 8px', opacity: 0.2 }} />
            <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '0 0 14px' }}>
              Ask clinical questions about this patient
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {QUICK_PROMPTS.map(q => (
                <button key={q} onClick={() => sendMessage(q)} style={{
                  padding: '8px 12px', borderRadius: 8,
                  border: '1px solid var(--border)', background: 'var(--bg-surface)',
                  fontSize: 11, color: 'var(--text-secondary)', cursor: 'pointer',
                  textAlign: 'left', transition: 'all 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--accent-cyan)'; e.currentTarget.style.color = 'var(--accent-cyan)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <AnimatePresence>
          {messages.map(msg => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                display: 'flex', gap: 8,
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
              }}
            >
              <div style={{
                width: 26, height: 26, borderRadius: 6, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: msg.role === 'user'
                  ? 'var(--accent-cyan)'
                  : 'linear-gradient(135deg, #00d4ff, #8b5cf6)',
                marginTop: 2,
              }}>
                {msg.role === 'user'
                  ? <User size={13} color="white" />
                  : <Bot size={13} color="white" />
                }
              </div>
              <div style={{
                flex: 1,
                padding: '10px 14px',
                borderRadius: msg.role === 'user' ? '12px 4px 12px 12px' : '4px 12px 12px 12px',
                background: msg.role === 'user' ? 'rgba(0,212,255,0.08)' : 'var(--bg-surface)',
                border: `1px solid ${msg.role === 'user' ? 'rgba(0,212,255,0.2)' : 'var(--border)'}`,
                fontSize: 12, lineHeight: 1.6, color: 'var(--text-secondary)',
                whiteSpace: 'pre-wrap',
              }}>
                {msg.content}

                {msg.references && msg.references.length > 0 && (
                  <div style={{
                    marginTop: 10, paddingTop: 8,
                    borderTop: '1px solid var(--border)',
                    display: 'flex', flexDirection: 'column', gap: 3,
                  }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                      <BookOpen size={10} /> References
                    </div>
                    {msg.references.map((ref, i) => (
                      <div key={i} style={{ fontSize: 10, color: 'var(--accent-cyan)' }}>
                        • {ref}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0' }}>
            <Loader2 size={14} className="animate-spin" style={{ color: 'var(--accent-cyan)' }} />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Analyzing patient data...</span>
          </motion.div>
        )}
      </div>

      {/* Input */}
      <div style={{
        padding: '10px 14px',
        borderTop: '1px solid var(--border)',
        display: 'flex', gap: 8,
      }}>
        <input
          className="input-field"
          style={{ flex: 1, fontSize: 12 }}
          placeholder="Ask about this patient..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage(input)}
          disabled={loading}
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          style={{
            padding: '8px 14px', borderRadius: 8, border: 'none',
            background: input.trim() ? 'var(--accent-cyan)' : 'var(--bg-surface)',
            color: input.trim() ? 'white' : 'var(--text-muted)',
            cursor: input.trim() ? 'pointer' : 'default',
            transition: 'all 0.15s', display: 'flex', alignItems: 'center',
          }}
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}
