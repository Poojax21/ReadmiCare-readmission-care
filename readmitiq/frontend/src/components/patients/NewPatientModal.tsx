import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, UserPlus, Loader2 } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { patientsAPI, PatientCreate } from '../../services/api'
import { useNavigate } from 'react-router-dom'

interface Props {
  isOpen: boolean
  onClose: () => void
}

const ICD_OPTIONS = [
  { value: 'I50.9', label: 'Heart failure, unspecified' },
  { value: 'I21.9', label: 'Acute MI, unspecified' },
  { value: 'I10', label: 'Essential hypertension' },
  { value: 'J44.1', label: 'COPD with exacerbation' },
  { value: 'J18.9', label: 'Pneumonia, unspecified' },
  { value: 'E11.65', label: 'Type 2 DM with hyperglycemia' },
  { value: 'K92.1', label: 'GI bleed' },
  { value: 'N17.9', label: 'AKI, unspecified' },
  { value: 'A41.9', label: 'Sepsis, unspecified' },
]

export default function NewPatientModal({ isOpen, onClose }: Props) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  
  const [formData, setFormData] = useState<Partial<PatientCreate>>({
    mrn: `MRN${Math.floor(100000 + Math.random() * 900000)}`,
    first_name: '',
    last_name: '',
    age: 65,
    gender: 'M',
    ethnicity: 'WHITE',
    primary_diagnosis_icd: 'I50.9',
    ward: 'General Medicine 3B',
    attending_physician: 'Dr. Sarah Chen',
  })

  const mutation = useMutation({
    mutationFn: (data: PatientCreate) => patientsAPI.create(data),
    onSuccess: (newPatient) => {
      queryClient.invalidateQueries({ queryKey: ['patients'] })
      queryClient.invalidateQueries({ queryKey: ['patient'] })
      onClose()
      navigate(`/patients/${newPatient.id}`)
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.mrn || !formData.age) return
    
    // Auto-fill diagnosis name based on ICD
    const dxName = ICD_OPTIONS.find(o => o.value === formData.primary_diagnosis_icd)?.label

    mutation.mutate({
      ...formData,
      primary_diagnosis_name: dxName,
      comorbidities: [],
    } as PatientCreate)
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: 20
        }}>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            style={{
              position: 'absolute', inset: 0,
              background: 'rgba(15,23,42,0.8)',
              backdropFilter: 'blur(4px)',
            }}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="card"
            style={{
              position: 'relative', width: '100%', maxWidth: 500,
              padding: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column',
              maxHeight: '90vh'
            }}
          >
            {/* Header */}
            <div style={{
              padding: '20px 24px', borderBottom: '1px solid var(--border)',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              background: 'rgba(255,255,255,0.02)'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 8,
                  background: 'rgba(0,212,255,0.1)', color: 'var(--accent-cyan)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                  <UserPlus size={20} />
                </div>
                <div>
                  <h2 style={{ margin: 0, fontSize: 18, fontFamily: 'var(--font-display)' }}>Add New Patient</h2>
                  <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>Enter clinical details to generate risk profile</p>
                </div>
              </div>
              <button onClick={onClose} className="btn-ghost" style={{ padding: 8 }}>
                <X size={20} />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} style={{ padding: 24, overflowY: 'auto' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>MRN</label>
                  <input
                    required
                    className="input-field"
                    value={formData.mrn}
                    onChange={e => setFormData({ ...formData, mrn: e.target.value })}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>First Name</label>
                  <input
                    className="input-field"
                    placeholder="e.g. James"
                    value={formData.first_name}
                    onChange={e => setFormData({ ...formData, first_name: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Last Name</label>
                  <input
                    className="input-field"
                    placeholder="e.g. Wilson"
                    value={formData.last_name}
                    onChange={e => setFormData({ ...formData, last_name: e.target.value })}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Age</label>
                  <input
                    type="number" required min={0} max={120}
                    className="input-field"
                    value={formData.age}
                    onChange={e => setFormData({ ...formData, age: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Gender</label>
                  <select
                    className="input-field"
                    value={formData.gender}
                    onChange={e => setFormData({ ...formData, gender: e.target.value })}
                  >
                    <option value="M">Male</option>
                    <option value="F">Female</option>
                  </select>
                </div>

                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Primary Diagnosis</label>
                  <select
                    className="input-field"
                    value={formData.primary_diagnosis_icd}
                    onChange={e => setFormData({ ...formData, primary_diagnosis_icd: e.target.value })}
                  >
                    {ICD_OPTIONS.map(opt => (
                      <option key={opt.value} value={opt.value}>{opt.value} - {opt.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Ward</label>
                  <input
                    className="input-field"
                    value={formData.ward}
                    onChange={e => setFormData({ ...formData, ward: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>Attending Physician</label>
                  <input
                    className="input-field"
                    value={formData.attending_physician}
                    onChange={e => setFormData({ ...formData, attending_physician: e.target.value })}
                  />
                </div>

              </div>

              {/* Footer */}
              <div style={{ display: 'flex', gap: 12, marginTop: 32, justifyContent: 'flex-end' }}>
                <button type="button" onClick={onClose} className="btn-ghost" disabled={mutation.isPending}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" style={{ minWidth: 120 }} disabled={mutation.isPending}>
                  {mutation.isPending ? <Loader2 size={16} className="spin" /> : 'Create Patient'}
                </button>
              </div>
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
