import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ErrorMessage } from '../components/common'
import { coverageApi } from '../api/client'
import { useCoverageItem } from '../hooks'
import type { DecisionStatus, PipelineDecision } from '../api/types'

const DECISION_STATUSES: DecisionStatus[] = [
  'greenlit',
  'hold',
  'proceed',
  'archive',
  'dropped',
]

function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function sourceHref(source: unknown): { href?: string; label: string } {
  if (typeof source === 'string') {
    const isUrl = /^https?:\/\//i.test(source)
    return { href: isUrl ? source : undefined, label: source }
  }
  if (source && typeof source === 'object') {
    const rec = source as Record<string, unknown>
    const href = typeof rec.url === 'string' ? rec.url : undefined
    const label =
      (typeof rec.title === 'string' && rec.title) ||
      (typeof rec.publisher === 'string' && rec.publisher) ||
      href ||
      'Source'
    return { href, label }
  }
  return { label: String(source) }
}

export function CoverageDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: item, loading, error, refetch } = useCoverageItem(id)
  const [userStory, setUserStory] = useState('')
  const [status, setStatus] = useState<DecisionStatus>('hold')
  const [blocker, setBlocker] = useState('')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)

  const fillFrom = (decision: PipelineDecision) => {
    setEditingId(decision.id)
    setUserStory(decision.user_story)
    setStatus(decision.status)
    setBlocker(decision.blocker || '')
  }

  const resetForm = () => {
    setEditingId(null)
    setUserStory('')
    setStatus('hold')
    setBlocker('')
    setFormError(null)
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!id || !userStory.trim()) {
      setFormError('User story is required.')
      return
    }
    setSaving(true)
    setFormError(null)
    try {
      const payload = {
        user_story: userStory.trim(),
        status,
        blocker: blocker.trim() || null,
      }
      if (editingId) {
        await coverageApi.updateDecision(editingId, payload)
      } else {
        await coverageApi.createDecision(id, payload)
      }
      resetForm()
      refetch()
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Failed to save decision')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="page">
        <p className="muted">Loading coverage find…</p>
      </div>
    )
  }

  if (error || !item) {
    return (
      <div className="page">
        <ErrorMessage
          message={error?.message || 'Coverage item not found'}
          onRetry={error ? refetch : undefined}
        />
        <button type="button" className="secondary-btn" onClick={() => navigate('/coverage')}>
          Back to coverage
        </button>
      </div>
    )
  }

  const decisions = item.decisions || []

  return (
    <div className="page coverage-detail">
      <button type="button" className="coverage-back" onClick={() => navigate('/coverage')}>
        ← All coverage finds
      </button>

      <div className="page__intro">
        <div className="eyebrow">
          Packet week {formatDate(item.packet_week)} · {item.university || 'No university'}
        </div>
        <h1 className="page__title">{item.headline}</h1>
        <p className="page__dek">
          Independent coverage record. This is not a scraped TTO listing, and reviewing it
          does not start a use-case diamond or any listing-row workflow.
        </p>
      </div>

      <div className="coverage-detail__layout">
        <article className="coverage-detail__main">
          <div className="coverage-row__tags">
            <span className={`status-pill status-pill--match-${item.match_status}`}>
              {item.match_status}
            </span>
            <span className="status-pill">
              {item.source_class === 'newspaper_tv' ? 'Newspaper / TV' : 'Specialist'}
            </span>
            <span className="status-pill status-pill--muted">
              Covered {formatDate(item.coverage_date)}
            </span>
          </div>

          {item.summary && (
            <section>
              <h2>Summary</h2>
              <p>{item.summary}</p>
            </section>
          )}
          {item.capability && (
            <section>
              <h2>Capability</h2>
              <p>{item.capability}</p>
            </section>
          )}
          {item.independence_note && (
            <section>
              <h2>Independence</h2>
              <p>{item.independence_note}</p>
            </section>
          )}

          <section>
            <h2>Sources</h2>
            {item.sources.length === 0 ? (
              <p className="muted">No sources recorded.</p>
            ) : (
              <ul className="coverage-sources">
                {item.sources.map((source, idx) => {
                  const { href, label } = sourceHref(source)
                  return (
                    <li key={`${label}-${idx}`}>
                      {href ? (
                        <a href={href} target="_blank" rel="noreferrer">
                          {label}
                        </a>
                      ) : (
                        label
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </section>

          {item.technology_uuid && (
            <section className="coverage-tto-note">
              <h2>Optional TTO context</h2>
              <p>
                Best-effort join to a scraped listing for legal/IP background only.{' '}
                <Link to={`/technology/${item.technology_uuid}`}>Open TTO listing</Link>
              </p>
            </section>
          )}
        </article>

        <aside className="coverage-detail__aside">
          <h2>Pipeline decision</h2>
          <p className="muted">
            {editingId ? 'Updating an existing decision.' : 'Record hold / proceed / archive for this find.'}
          </p>
          <form className="decision-form" onSubmit={onSubmit}>
            <label>
              <span>Status</span>
              <select value={status} onChange={(e) => setStatus(e.target.value as DecisionStatus)}>
                {DECISION_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>User story</span>
              <textarea
                rows={5}
                value={userStory}
                onChange={(e) => setUserStory(e.target.value)}
                placeholder="As a … I can … so that …"
                required
              />
            </label>
            <label>
              <span>Blocker</span>
              <textarea
                rows={3}
                value={blocker}
                onChange={(e) => setBlocker(e.target.value)}
                placeholder="Optional — what is holding this?"
              />
            </label>
            {formError && <p className="decision-form__error">{formError}</p>}
            <div className="decision-form__actions">
              <button type="submit" className="assess-btn" disabled={saving}>
                {saving ? 'Saving…' : editingId ? 'Update decision' : 'Save decision'}
              </button>
              {editingId && (
                <button type="button" className="secondary-btn" onClick={resetForm}>
                  Cancel
                </button>
              )}
            </div>
          </form>

          <h3>History</h3>
          {decisions.length === 0 ? (
            <p className="muted">No decisions yet.</p>
          ) : (
            <ul className="decision-history">
              {decisions.map((d) => (
                <li key={d.id}>
                  <div className="decision-history__head">
                    <span className={`status-pill status-pill--decision-${d.status}`}>{d.status}</span>
                    <span className="muted">{formatDate(d.created_at)}</span>
                  </div>
                  <p>{d.user_story}</p>
                  {d.blocker && <p className="muted">Blocker: {d.blocker}</p>}
                  <button type="button" className="coverage-back" onClick={() => fillFrom(d)}>
                    Edit
                  </button>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </div>
    </div>
  )
}
