import { useState, useEffect, useRef } from 'react'
import { Icon } from './Icon'

export type GateReason = 'Enrich' | 'Evaluate' | null

interface LoginModalProps {
  open: boolean
  onClose: () => void
  gateReason: GateReason
}

const GATE_COPY: Record<string, { label: string; verb: string }> = {
  Enrich: { label: 'Enrichment', verb: 'enrich records' },
  Evaluate: { label: 'Evaluation', verb: 'run Real·Win·Worth evaluations' },
}

export function LoginModal({ open, onClose, gateReason }: LoginModalProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const emailRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useEffect(() => {
    if (open && emailRef.current) {
      const t = setTimeout(() => emailRef.current?.focus(), 160)
      return () => clearTimeout(t)
    }
    // When closed, ensure any in-flight pending timeout resets.
    return undefined
  }, [open])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) return
    setSubmitting(true)
    setTimeout(() => {
      setSubmitting(false)
      setPassword('')
    }, 1100)
  }

  const g = (gateReason && GATE_COPY[gateReason]) || { label: 'this area', verb: 'continue' }

  return (
    <div
      className={`modal-overlay ${open ? 'is-open' : ''}`}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal__rule" />
        <button className="modal__close" onClick={onClose} aria-label="Close">
          ✕
        </button>

        <div className="modal__head">
          <div className="modal__lockup">
            <img src="/assets/piedmont-wordmark.png" alt="Piedmont" />
            <div className="modal__lockup-divider" />
            <div className="modal__lockup-product">Phronesis</div>
          </div>
          <div className="modal__eyebrow">Sign in required</div>
          <h2 className="modal__title">Sign in to access {g.label}</h2>
          <p className="modal__sub">
            Discovery is open for browsing. To {g.verb}, sign in with your{' '}
            <b>Piedmont</b> workspace account.
          </p>
        </div>

        <div className="modal__body">
          {gateReason && (
            <div className="login-gate-note">
              <span>
                <b>{gateReason}</b> is a member-only workspace. Your session will resume
                here after sign-in.
              </span>
            </div>
          )}
          <form onSubmit={handleSubmit}>
            <label className="login-field">
              <span className="login-field__label">Work email</span>
              <input
                ref={emailRef}
                type="email"
                className="login-field__input"
                placeholder="name@piedmontinnovation.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </label>
            <label className="login-field">
              <span className="login-field__label">Password</span>
              <input
                type="password"
                className="login-field__input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </label>

            <div className="login-row">
              <label className="login-remember">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                />
                Keep me signed in
              </label>
              <button
                type="button"
                className="login-forgot"
                onClick={(e) => e.preventDefault()}
              >
                Forgot password?
              </button>
            </div>

            <button
              type="submit"
              className="login-submit"
              disabled={submitting || !email || !password}
            >
              {submitting ? (
                <>
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    style={{ animation: 'spin 0.9s linear infinite' }}
                  >
                    <path d="M21 12a9 9 0 1 1-6.2-8.55" />
                  </svg>
                  Signing in…
                </>
              ) : (
                <>
                  Sign in <Icon name="arrow-right" size={14} />
                </>
              )}
            </button>

            <div className="login-divider">or</div>

            <button
              type="button"
              className="login-sso"
              onClick={(e) => e.preventDefault()}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="3" width="8" height="8" />
                <rect x="13" y="3" width="8" height="8" />
                <rect x="3" y="13" width="8" height="8" />
                <rect x="13" y="13" width="8" height="8" />
              </svg>
              Continue with Microsoft SSO
            </button>
          </form>
        </div>

        <div className="modal__foot">
          Don't have a Piedmont workspace account?{' '}
          <button type="button" onClick={(e) => e.preventDefault()}>
            Request access
          </button>
        </div>
      </div>
    </div>
  )
}
