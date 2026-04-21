import type { TechnologySummary } from '../../api/types'
import { getUniversityName } from '../../utils/universityNames'

interface TechCardProps {
  tech: TechnologySummary
  excerpt?: string | null
  keywords?: string[] | null
  patentStatus?: string | null
  patentGeography?: string[] | null
  dense?: boolean
  onOpen: (uuid: string) => void
}

function universityShort(code: string): string {
  const full = getUniversityName(code)
  if (full === code) return code.toUpperCase()
  if (full.startsWith('University of ')) return 'U ' + full.slice('University of '.length)
  return full.replace(/ University$/, '')
}

export function TechCard({
  tech,
  excerpt,
  keywords,
  patentStatus,
  patentGeography,
  dense,
  onOpen,
}: TechCardProps) {
  const kwList = (keywords || []).slice(0, dense ? 3 : 4)
  const status = (patentStatus || '').toLowerCase()
  const statusClass =
    status === 'granted' ? 'is-granted' : status === 'pending' ? 'is-pending' : ''
  const statusLabel = status
    ? status.charAt(0).toUpperCase() + status.slice(1)
    : 'Unknown'

  return (
    <button
      type="button"
      className="card"
      onClick={() => onOpen(tech.uuid)}
      aria-label={`Open ${tech.title}`}
    >
      <div className="card__head">
        <div className="card__univ">{universityShort(tech.university)}</div>
        <div className="card__tech-id">{tech.tech_id}</div>
      </div>
      <h3 className="card__title">{tech.title}</h3>
      {!dense && excerpt && <p className="card__excerpt">{excerpt}</p>}
      {(tech.top_field || tech.subfield) && (
        <div className="card__field-line">
          <span className="card__field-dot" />
          {tech.top_field && <span className="card__field">{tech.top_field}</span>}
          {tech.subfield && <span className="card__subfield">/ {tech.subfield}</span>}
        </div>
      )}
      {kwList.length > 0 && (
        <div className="card__keywords">
          {kwList.map((k) => (
            <span key={k} className="kw">
              {k}
            </span>
          ))}
        </div>
      )}
      <div className="card__foot">
        <span className={`patent-badge ${statusClass}`}>
          <span className="dot" />
          {statusLabel}
          {patentGeography && patentGeography.length > 0 && (
            <span className="geos">{patentGeography.join('·')}</span>
          )}
        </span>
        <span className="tier-flag is-full">{tech.first_seen?.slice(0, 7) || 'new'}</span>
      </div>
    </button>
  )
}
