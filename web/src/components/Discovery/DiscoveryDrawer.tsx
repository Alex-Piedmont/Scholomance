import { useEffect, useState } from 'react'
import { Icon } from '../Layout/Icon'
import { useTechnology } from '../../hooks/useTechnology'
import { getUniversityName } from '../../utils/universityNames'
import { parseRawData, stripHtml } from '../Detail/parseRawData'
import type { TechnologyDetail } from '../../api/types'

interface DiscoveryDrawerProps {
  uuid: string | null
  onClose: () => void
}

type Phase = 'idle' | 'queued'

export function DiscoveryDrawer({ uuid, onClose }: DiscoveryDrawerProps) {
  const open = !!uuid

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  return (
    <>
      <div
        className={`drawer-overlay ${open ? 'is-open' : ''}`}
        onClick={onClose}
        aria-hidden={!open}
      />
      <aside className={`drawer ${open ? 'is-open' : ''}`} aria-hidden={!open}>
        {uuid && <DrawerContent key={uuid} uuid={uuid} onClose={onClose} />}
      </aside>
    </>
  )
}

function DrawerContent({ uuid, onClose }: { uuid: string; onClose: () => void }) {
  const { data: tech, loading } = useTechnology(uuid)
  const [phase, setPhase] = useState<Phase>('idle')

  const status = (tech?.patent_status || '').toLowerCase()
  const statusClass =
    status === 'granted' ? 'is-granted' : status === 'pending' ? 'is-pending' : ''

  return (
    <>
      {tech && (
        <div className="drawer__head">
          <div className="drawer__head-top">
            <div className="drawer__univ">
              {getUniversityName(tech.university)} · {tech.tech_id}
            </div>
            <button className="drawer__close" onClick={onClose} aria-label="Close">
              ✕
            </button>
          </div>
          <h2 className="drawer__title">{tech.title}</h2>
          <div className="drawer__meta-row">
            {(tech.top_field || tech.subfield) && (
              <span>
                <b>{tech.top_field}</b>
                {tech.subfield && <> / {tech.subfield}</>}
              </span>
            )}
            {tech.patent_status && (
              <span className={`patent-badge ${statusClass}`}>
                <span className="dot" />
                Patent {tech.patent_status}
                {tech.patent_geography && tech.patent_geography.length > 0 && (
                  <> · {tech.patent_geography.join(', ')}</>
                )}
              </span>
            )}
            {tech.first_seen && (
              <span>
                First seen <b>{tech.first_seen.slice(0, 10)}</b>
              </span>
            )}
            {tech.url && (
              <a href={tech.url} target="_blank" rel="noreferrer">
                Source listing <Icon name="external" size={12} />
              </a>
            )}
          </div>
        </div>
      )}

      <div className="drawer__body">
        {loading && !tech && <p style={{ color: 'var(--fg-muted)' }}>Loading…</p>}
        {tech && <DrawerBody tech={tech} />}
      </div>

      <div className="drawer__footer">
        {phase === 'idle' ? (
          <>
            <button className="secondary-btn" type="button">
              Shortlist
            </button>
            <button
              className="assess-btn"
              type="button"
              onClick={() => setPhase('queued')}
              disabled={!tech}
            >
              <Icon name="arrow-right" size={16} />
              Hand-off for Enrichment
            </button>
          </>
        ) : (
          <>
            <button
              className="secondary-btn"
              type="button"
              onClick={() => setPhase('idle')}
            >
              Undo
            </button>
            <button className="assess-btn" type="button" disabled>
              <Icon name="sparkles" size={14} />
              Queued — view on Enrichment tab
            </button>
          </>
        )}
      </div>
    </>
  )
}

function DrawerBody({ tech }: { tech: TechnologyDetail }) {
  const parsed = parseRawData(tech)
  const desc =
    tech.description ||
    parsed.shortDescription ||
    parsed.fullDescription ||
    parsed.abstractText ||
    ''

  return (
    <>
      {desc && (
        <div className="section">
          <h4 className="section__head">Description</h4>
          <p>{stripHtml(desc)}</p>
        </div>
      )}

      {parsed.applications && parsed.applications.length > 0 && (
        <div className="section">
          <h4 className="section__head">Applications</h4>
          <ul>
            {parsed.applications.map((x, i) => (
              <li key={i}>{stripHtml(x)}</li>
            ))}
          </ul>
        </div>
      )}

      {parsed.advantages && parsed.advantages.length > 0 && (
        <div className="section">
          <h4 className="section__head">Advantages</h4>
          <ul>
            {parsed.advantages.map((x, i) => (
              <li key={i}>{stripHtml(x)}</li>
            ))}
          </ul>
        </div>
      )}

      {parsed.keyPoints && parsed.keyPoints.length > 0 && (
        <div className="section">
          <h4 className="section__head">Key Points</h4>
          <ul>
            {parsed.keyPoints.map((x, i) => (
              <li key={i}>{stripHtml(x)}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="section">
        <h4 className="section__head">Record Metadata</h4>
        <dl className="kv-grid">
          {parsed.developmentStage && (
            <>
              <dt>Development stage</dt>
              <dd>{parsed.developmentStage}</dd>
            </>
          )}
          {parsed.marketOpportunity && (
            <>
              <dt>Market context</dt>
              <dd>{stripHtml(parsed.marketOpportunity)}</dd>
            </>
          )}
          {parsed.inventors && parsed.inventors.length > 0 && (
            <>
              <dt>Inventors</dt>
              <dd>{parsed.inventors.join(', ')}</dd>
            </>
          )}
          {tech.keywords && tech.keywords.length > 0 && (
            <>
              <dt>Keywords</dt>
              <dd>
                <div className="tag-row">
                  {tech.keywords.map((k) => (
                    <span key={k} className="kw">
                      {k}
                    </span>
                  ))}
                </div>
              </dd>
            </>
          )}
          {tech.patent_geography && tech.patent_geography.length > 0 && (
            <>
              <dt>Patent geography</dt>
              <dd className="mono">{tech.patent_geography.join(' · ')}</dd>
            </>
          )}
        </dl>
      </div>

      {parsed.publicationsList && parsed.publicationsList.length > 0 && (
        <div className="section">
          <h4 className="section__head">Publications</h4>
          <ul>
            {parsed.publicationsList.map((p, i) => (
              <li key={i}>
                {p.url ? (
                  <a href={p.url} target="_blank" rel="noreferrer">
                    {p.text || p.url}
                  </a>
                ) : (
                  p.text
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  )
}
