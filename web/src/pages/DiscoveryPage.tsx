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
import { useTechnologies, useStatsKeywords } from '../hooks'
import type { TechnologyFilters } from '../api/types'

export function DiscoveryPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [mode, setMode] = useState<SearchMode>('semantic')
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [committedQuery, setCommittedQuery] = useState(query)
  // Deep-link surface for Playwright and bookmarks: ?openTech=<uuid>
  // hydrates the drawer on mount. Additive — does not round-trip to URL
  // when the drawer is opened by click (preserves existing UX).
  const [selectedUuid, setSelectedUuid] = useState<string | null>(
    () => searchParams.get('openTech') || null,
  )
  const searchRef = useRef<HTMLInputElement>(null)

  const [facets, setFacets] = useState<FacetState>({
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
      patent_status: facets.patentStatus || undefined,
    }),
    [committedQuery, facets],
  )

  const { data, loading, error, setFilters } = useTechnologies(filters)
  const { data: keywordStats } = useStatsKeywords()

  useEffect(() => {
    setFilters(filters)
    const next = new URLSearchParams()
    if (filters.q) next.set('q', filters.q)
    if (filters.patent_status) next.set('patent_status', filters.patent_status)
    setSearchParams(next, { replace: true })
  }, [filters, setFilters, setSearchParams])

  const selectKeyword = (keyword: string) => {
    if (committedQuery === keyword) {
      setQuery('')
      setCommittedQuery('')
    } else {
      setQuery(keyword)
      setCommittedQuery(keyword)
    }
  }

  const togglePatent = (status: string) => {
    setFacets((prev) => ({
      ...prev,
      patentStatus: prev.patentStatus === status ? null : status,
    }))
  }

  const resetFilters = () => {
    setQuery('')
    setCommittedQuery('')
    setFacets({ patentStatus: null })
  }

  const items = data?.items || []
  const total = data?.total || 0
  const selectedKeyword =
    keywordStats?.find((k) => k.keyword === committedQuery)?.keyword || null
  const hasFilters = !!(committedQuery || facets.patentStatus)

  return (
    <div className="page">
      <div className="page__intro">
        <div className="eyebrow">Discovery · Technology Opportunities</div>
        <h1 className="page__title">Find the best deep-tech opportunities for commercialization</h1>
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
        keywords={keywordStats || []}
        selectedKeyword={selectedKeyword}
        onSelectKeyword={selectKeyword}
        facets={facets}
        onTogglePatent={togglePatent}
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
