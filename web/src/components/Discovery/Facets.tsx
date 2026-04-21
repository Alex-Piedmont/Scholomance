import type { KeywordCount } from '../../api/types'

export interface FacetState {
  patentStatus: string | null
}

interface FacetsProps {
  keywords: KeywordCount[]
  selectedKeyword: string | null
  onSelectKeyword: (keyword: string) => void
  facets: FacetState
  onTogglePatent: (status: string) => void
}

const PATENT_OPTIONS: Array<{ key: string; label: string }> = [
  { key: 'granted', label: 'Granted' },
  { key: 'pending', label: 'Pending' },
  { key: 'filed', label: 'Filed' },
]

export function Facets({
  keywords,
  selectedKeyword,
  onSelectKeyword,
  facets,
  onTogglePatent,
}: FacetsProps) {
  const topKeywords = keywords.slice(0, 9)

  return (
    <div className="facets">
      <span className="facet-group-label">Field</span>
      {topKeywords.map((k) => (
        <button
          key={k.keyword}
          type="button"
          className={`facet ${selectedKeyword === k.keyword ? 'is-active' : ''}`}
          onClick={() => onSelectKeyword(k.keyword)}
        >
          {k.keyword} <span className="count">{k.count.toLocaleString()}</span>
        </button>
      ))}
      <span className="facet-break" aria-hidden="true" />
      <span className="facet-group-label">Patent</span>
      {PATENT_OPTIONS.map((o) => (
        <button
          key={o.key}
          type="button"
          className={`facet ${facets.patentStatus === o.key ? 'is-active' : ''}`}
          onClick={() => onTogglePatent(o.key)}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
