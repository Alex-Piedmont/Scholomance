import { useState, useEffect, useMemo, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  SearchBar,
  Facets,
  TechCard,
  DiscoveryDrawer,
  type SearchMode,
  type FacetState,
} from '../components/Discovery'
import { useTechnologies, useStatsByField } from '../hooks'
import type { TechnologyFilters } from '../api/types'

export function DiscoveryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [mode, setMode] = useState<SearchMode>('semantic')
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [committedQuery, setCommittedQuery] = useState(query)
  const [selectedUuid, setSelectedUuid] = useState<string | null>(null)
  const searchRef = useRef<HTMLInputElement>(null)

  const [facets, setFacets] = useState<FacetState>({
    field: searchParams.get('top_field') || null,
    patentStatus: searchParams.get('patent_status') || null,
  })

  useEffect(() => {
    const t = setTimeout(() => setCommittedQuery(query), 250)
    return () => clearTimeout(t)
  }, [query])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        searchRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const filters: TechnologyFilters = useMemo(
    () => ({
      page: 1,
      limit: 30,
      q: committedQuery || undefined,
      top_field: facets.field || undefined,
      patent_status: facets.patentStatus || undefined,
    }),
    [committedQuery, facets],
  )

  const { data, loading, error, setFilters } = useTechnologies(filters)
  const { data: fieldStats } = useStatsByField()

  useEffect(() => {
    setFilters(filters)
    const next = new URLSearchParams()
    if (filters.q) next.set('q', filters.q)
    if (filters.top_field) next.set('top_field', filters.top_field)
    if (filters.patent_status) next.set('patent_status', filters.patent_status)
    setSearchParams(next, { replace: true })
  }, [filters, setFilters, setSearchParams])

  const toggleFacet = (group: keyof FacetState, value: string) => {
    setFacets((prev) => ({
      ...prev,
      [group]: prev[group] === value ? null : value,
    }))
  }

  const resetFilters = () => {
    setQuery('')
    setFacets({ field: null, patentStatus: null })
  }

  const items = data?.items || []
  const total = data?.total || 0
  const hasFilters = !!(committedQuery || facets.field || facets.patentStatus)

  return (
    <div className="page">
      <div className="page__intro">
        <div className="eyebrow">University Tech Transfer</div>
        <h1 className="page__title">Discovery</h1>
        <p className="page__dek">
          Phronesis indexes university technology listings across dozens of
          institutions. Search semantically against titles and descriptions, filter by
          field and patent status, and drill into any record to hand off for{' '}
          <b>Enrichment</b>. Assessments feed the commercialization shortlist.
        </p>
      </div>

      <SearchBar
        ref={searchRef}
        query={query}
        setQuery={setQuery}
        mode={mode}
        setMode={setMode}
        onSubmit={() => setCommittedQuery(query)}
      />

      <Facets
        fields={fieldStats || []}
        facets={facets}
        onToggle={toggleFacet}
      />

      <div className="results-meta">
        <div>
          {loading && !data ? (
            <span className="muted">Loading…</span>
          ) : error ? (
            <span className="muted">Failed to load results.</span>
          ) : (
            <>
              <b>{total.toLocaleString()}</b> {total === 1 ? 'record' : 'records'}
              {committedQuery && (
                <>
                  {' '}
                  for <em>"{committedQuery}"</em>
                </>
              )}
              {hasFilters && (
                <button
                  type="button"
                  className="search__clear"
                  style={{ padding: '0 0 0 12px' }}
                  onClick={resetFilters}
                >
                  Reset
                </button>
              )}
            </>
          )}
        </div>
        <div className="sort-hint">
          {committedQuery ? 'Ranked by relevance' : 'Sorted by first seen'}
        </div>
      </div>

      <div className="grid">
        {!loading && items.length === 0 ? (
          <div className="empty-state">
            <h3>No matches</h3>
            <p>Try loosening facets or switch to Semantic mode.</p>
          </div>
        ) : (
          items.map((t) => (
            <TechCard
              key={t.uuid}
              tech={t}
              onOpen={(uuid) => setSelectedUuid(uuid)}
            />
          ))
        )}
      </div>

      <DiscoveryDrawer uuid={selectedUuid} onClose={() => setSelectedUuid(null)} />
    </div>
  )
}
