import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts'
import { Brain, Play, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { retrainAPI, RetrainStatus } from '../services/api'
import toast from 'react-hot-toast'

const MODEL_METRICS = [
  { model: 'Ensemble',         auc: 0.847, pr_auc: 0.612, f1: 0.681, brier: 0.142, primary: true },
  { model: 'XGBoost',          auc: 0.831, pr_auc: 0.588, f1: 0.657, brier: 0.158 },
  { model: 'LightGBM',         auc: 0.829, pr_auc: 0.579, f1: 0.651, brier: 0.161 },
  { model: 'Logistic Reg.',    auc: 0.784, pr_auc: 0.521, f1: 0.612, brier: 0.181 },
]

const RADAR_DATA = [
  { metric: 'ROC-AUC',     ensemble: 84.7, xgboost: 83.1, lgbm: 82.9 },
  { metric: 'PR-AUC',      ensemble: 61.2, xgboost: 58.8, lgbm: 57.9 },
  { metric: 'F1 Score',    ensemble: 68.1, xgboost: 65.7, lgbm: 65.1 },
  { metric: 'Calibration', ensemble: 85.8, xgboost: 84.2, lgbm: 83.9 },
  { metric: 'Sensitivity', ensemble: 72.4, xgboost: 69.8, lgbm: 70.1 },
  { metric: 'Specificity', ensemble: 88.3, xgboost: 86.1, lgbm: 85.4 },
]

const FEATURE_IMPORTANCE_GLOBAL = [
  { feature: 'Charlson Index',       importance: 0.142 },
  { feature: 'Age',                  importance: 0.118 },
  { feature: 'AKI Risk',             importance: 0.094 },
  { feature: 'Length of Stay',       importance: 0.087 },
  { feature: 'Shock Index',          importance: 0.072 },
  { feature: 'Albumin (min)',        importance: 0.065 },
  { feature: 'Hemoglobin (min)',     importance: 0.058 },
  { feature: 'Creatinine (max)',     importance: 0.055 },
  { feature: 'Emergency Admit',      importance: 0.048 },
  { feature: 'N Comorbidities',      importance: 0.044 },
  { feature: 'Hypotension',          importance: 0.041 },
  { feature: 'SpO2 (min)',           importance: 0.038 },
]

function StatusIcon({ status }: { status: string }) {
  if (status === 'COMPLETED') return <CheckCircle size={16} color="var(--risk-low)" />
  if (status === 'RUNNING')   return <Clock size={16} color="var(--risk-medium)" />
  if (status === 'FAILED')    return <AlertCircle size={16} color="var(--risk-high)" />
  return <Clock size={16} color="var(--text-muted)" />
}

export default function ModelPage() {
  const [taskId, setTaskId] = useState<string | null>(null)
  const [modelTypes, setModelTypes] = useState(['xgboost', 'lgbm', 'logistic'])
  const [nTrials, setNTrials] = useState(30)

  const { data: status, refetch: refetchStatus } = useQuery({
    queryKey: ['retrain-status', taskId],
    queryFn: () => retrainAPI.status(taskId!),
    enabled: !!taskId,
    refetchInterval: 2000,
  })

  const { mutate: triggerRetrain, isPending } = useMutation({
    mutationFn: () => retrainAPI.trigger({ model_types: modelTypes, n_optuna_trials: nTrials, dataset_source: 'synthetic' }),
    onSuccess: (data) => {
      setTaskId(data.task_id)
      toast.success('Retraining started!')
    },
    onError: () => toast.error('Failed to start retraining'),
  })

  const toggle = (m: string) =>
    setModelTypes(prev => prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 1200 }}>
      <div>
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 24, margin: 0 }}>Model Performance</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 13, margin: '4px 0 0' }}>
          Ensemble metrics · SHAP global importance · Retraining controls
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Model comparison table */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Model Comparison</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>AUC-ROC</th>
                <th>PR-AUC</th>
                <th>F1</th>
                <th>Brier</th>
              </tr>
            </thead>
            <tbody>
              {MODEL_METRICS.map(m => (
                <tr key={m.model}>
                  <td>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      {m.primary && <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--accent-cyan)', display: 'inline-block' }} />}
                      <span style={{ color: m.primary ? 'var(--accent-cyan)' : 'var(--text-secondary)', fontWeight: m.primary ? 600 : 400 }}>
                        {m.model}
                      </span>
                    </span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{m.auc.toFixed(3)}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{m.pr_auc.toFixed(3)}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{m.f1.toFixed(3)}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>{m.brier.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Radar chart */}
        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Performance Radar</div>
          <ResponsiveContainer width="100%" height={240}>
            <RadarChart data={RADAR_DATA}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
              <Radar name="Ensemble" dataKey="ensemble" stroke="var(--accent-cyan)"   fill="var(--accent-cyan)"   fillOpacity={0.15} />
              <Radar name="XGBoost"  dataKey="xgboost"  stroke="var(--accent-blue)"   fill="var(--accent-blue)"   fillOpacity={0.10} />
              <Radar name="LightGBM" dataKey="lgbm"     stroke="var(--accent-violet)" fill="var(--accent-violet)" fillOpacity={0.08} />
            </RadarChart>
          </ResponsiveContainer>
          <div style={{ display: 'flex', gap: 16, justifyContent: 'center', fontSize: 11, color: 'var(--text-muted)' }}>
            {[['var(--accent-cyan)', 'Ensemble'], ['var(--accent-blue)', 'XGBoost'], ['var(--accent-violet)', 'LightGBM']].map(([c, l]) => (
              <span key={l} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span style={{ width: 8, height: 2, background: c as string, display: 'inline-block', borderRadius: 1 }} /> {l}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Global feature importance */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 16 }}>Global Feature Importance (mean |SHAP|)</div>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={FEATURE_IMPORTANCE_GLOBAL} layout="vertical" barSize={12}>
            <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false}
              tickFormatter={v => v.toFixed(3)} />
            <YAxis type="category" dataKey="feature" width={160}
              tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
              formatter={(v: number) => [v.toFixed(4), 'Mean |SHAP|']}
            />
            <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
              {FEATURE_IMPORTANCE_GLOBAL.map((_, i) => (
                <Cell key={i}
                  fill={`hsl(${195 + i * 6}, 80%, ${55 - i * 2}%)`}
                  opacity={1 - i * 0.04}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Retraining panel */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        <div className="card" style={{ padding: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <Brain size={16} color="var(--accent-cyan)" />
            <span style={{ fontSize: 14, fontWeight: 600 }}>Retrain Models</span>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
              Select Models
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {['xgboost', 'lgbm', 'logistic', 'lstm'].map(m => (
                <button
                  key={m}
                  onClick={() => toggle(m)}
                  style={{
                    padding: '5px 12px', borderRadius: 4, border: '1px solid',
                    cursor: 'pointer', fontSize: 12, fontFamily: 'var(--font-mono)',
                    transition: 'all 0.15s',
                    background: modelTypes.includes(m) ? 'rgba(0,212,255,0.1)' : 'transparent',
                    borderColor: modelTypes.includes(m) ? 'var(--accent-cyan)' : 'var(--border)',
                    color: modelTypes.includes(m) ? 'var(--accent-cyan)' : 'var(--text-muted)',
                  }}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 6 }}>
              Optuna Trials: {nTrials}
            </label>
            <input
              type="range" min="10" max="100" step="5" value={nTrials}
              onChange={e => setNTrials(+e.target.value)}
              style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
              <span>10 (fast)</span><span>100 (thorough)</span>
            </div>
          </div>

          <button
            className="btn-primary"
            onClick={() => triggerRetrain()}
            disabled={isPending || modelTypes.length === 0}
            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}
          >
            <Play size={14} />
            {isPending ? 'Starting...' : 'Start Retraining'}
          </button>
        </div>

        {/* Status panel */}
        <div className="card" style={{ padding: 24 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Retraining Status</div>
          <AnimatePresence mode="wait">
            {status ? (
              <motion.div key="status" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                  <StatusIcon status={status.status} />
                  <span style={{ fontSize: 14, fontWeight: 500 }}>{status.status}</span>
                  <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {status.task_id.slice(0, 8)}...
                  </span>
                </div>
                {/* Progress bar */}
                <div className="risk-bar" style={{ marginBottom: 8 }}>
                  <div className="risk-bar-fill" style={{
                    width: `${status.progress}%`,
                    background: status.status === 'FAILED' ? 'var(--risk-high)' :
                               status.status === 'COMPLETED' ? 'var(--risk-low)' : 'var(--accent-cyan)',
                  }} />
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                  {status.current_step} · {status.progress}%
                </div>

                {status.metrics && (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                    {Object.entries(status.metrics).map(([k, v]) => (
                      <div key={k} style={{
                        padding: '10px 14px', background: 'var(--bg-surface)',
                        borderRadius: 6, border: '1px solid var(--border)',
                      }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                          {k.replace(/_/g, ' ')}
                        </div>
                        <div style={{ fontSize: 20, fontFamily: 'var(--font-display)', color: 'var(--accent-cyan)', marginTop: 4 }}>
                          {(v * 100).toFixed(1)}%
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '30px 0' }}>
                No active retraining task
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
