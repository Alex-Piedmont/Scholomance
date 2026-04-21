import type { FieldCount } from '../../api/types'

export interface FacetState {
  field: string | null
  patentStatus: string | null
}

interface FacetsProps {
  fields: FieldCount[]
  facets: FacetState
  onToggle: (group: keyof FacetState, value: string) => void
}

const PATENT_OPTIONS: Array<{ key: string; label: string }> = [
  { key: 'granted', label: 'Granted' },
  { key: 'pending', label: 'Pending' },
  { key: 'filed', label: 'Filed' },
]

export function Facets({ fields, facets, onToggle }: FacetsProps) {
  const topFields = [...fields].sort((a, b) => b.count - a.count).slice(0, 10)

  return (
    <div className="facets">
      <span className="facet-group-label">Field</span>
      {topFields.map((f) => (
        <button
          key={f.top_field}
          type="button"
          className={`facet ${facets.field === f.top_field ? 'is-active' : ''}`}
          onClick={() => onToggle('field', f.top_field)}
        >
          {f.top_field} <span className="count">{f.count.toLocaleString()}</span>
        </button>
      ))}
      <span className="facet-group-label" style={{ marginLeft: 12 }}>
        Patent
      </span>
      {PATENT_OPTIONS.map((o) => (
        <button
          key={o.key}
          type="button"
          className={`facet ${facets.patentStatus === o.key ? 'is-active' : ''}`}
          onClick={() => onToggle('patentStatus', o.key)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
