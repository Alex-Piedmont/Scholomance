import { useCallback, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Pagination } from '../components/Browser'
import { ErrorMessage } from '../components/common'
import { useCoverage } from '../hooks'
import type { CoverageFilters, DecisionStatus, MatchStatus, SourceClass } from '../api/types'

const MATCH_OPTIONS: Array<{ value: '' | MatchStatus; label: string }> = [
  { value: '', label: 'All matches' },
  { value: 'unmatched', label: 'Unmatched' },
  { value: 'candidate', label: 'Candidate' },
  { value: 'matched', label: 'Matched' },
]

const SOURCE_OPTIONS: Array<{ value: '' | SourceClass; label: string }> = [
  { value: '', label: 'All sources' },
  { value: 'newspaper_tv', label: 'Newspaper / TV' },
  { value: 'specialist', label: 'Specialist' },
]

const DECISION_OPTIONS: Array<{ value: '' | DecisionStatus; label: string }> = [
  { value: '', label: 'Any decision' },
  { value: 'greenlit', label: 'Greenlit' },
  { value: 'hold', label: 'Hold' },
  { value: 'proceed', label: 'Proceed' },
  { value: 'archive', label: 'Archive' },
  { value: 'dropped', label: 'Dropped' },
]

function formatWeek(value: string | null | undefined): string {
  if (!value) return 'No week'
  const d = new Date(`${value}T00:00:00`)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

function sourceLabel(value: SourceClass): string {
  return value === 'newspaper_tv' ? 'Newspaper / TV' : 'Specialist'
}

export function CoveragePage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const filtersFromUrl: CoverageFilters = {
    page: parseInt(searchParams.get('page') || '1', 10),
    limit: parseInt(searchParams.get('limit') || '20', 10),
    q: searchParams.get('q') || undefined,
    packet_week: searchParams.get('packet_week') || undefined,
    match_status: (searchParams.get('match_status') as MatchStatus) || undefined,
    source_class: (searchParams.get('source_class') as SourceClass) || undefined,
    decision_status: (searchParams.get('decision_status') as DecisionStatus) || undefined,
    unmatched_only: searchParams.get('unmatched_only') === '1' || undefined,
  }

  const { data, weeks, loading, error, filters, setFilters, setPage, refetch } =
    useCoverage(filtersFromUrl)

  const updateUrl = useCallback(
    (next: CoverageFilters) => {
      const params = new URLSearchParams()
      if (next.page && next.page > 1) params.set('page', String(next.page))
      if (next.limit && next.limit !== 20) params.set('limit', String(next.limit))
      if (next.q) params.set('q', next.q)
      if (next.packet_week) params.set('packet_week', next.packet_week)
      if (next.match_status) params.set('match_status', next.match_status)
      if (next.source_class) params.set('source_class', next.source_class)
      if (next.decision_status) params.set('decision_status', next.decision_status)
      if (next.unmatched_only) params.set('unmatched_only', '1')
      setSearchParams(params, { replace: true })
    },
    [setSearchParams],
  )

  useEffect(() => {
    updateUrl(filters)
  }, [filters, updateUrl])

  const handleFilterChange = (partial: Partial<CoverageFilters>) => {
    setFilters({ ...filters, ...partial })
  }

  if (error) {
    return (
      <div className="page">
        <div className="page__intro">
          <div className="eyebrow">Pipeline · Independent coverage</div>
          <h1 className="page__title">Coverage review</h1>
        </div>
        <ErrorMessage message="Failed to load coverage items. Please try again." onRetry={refetch} />
      </div>
    )
  }

  const items = data?.items || []
  const total = data?.total || 0

  return (
    <div className="page">
      <div className="page__intro">
        <div className="eyebrow">Pipeline · Independent coverage</div>
        <h1 className="page__title">Weekly coverage finds</h1>
        <p className="page__dek">
          These records are produced by the Monday briefing packet. They are{' '}
          <b>not</b> TTO listings. A find can be saved unmatched; optional joins to
          scraped IP/legal listings are best-effort context only. Hold, proceed, and
          archive decisions live here — never on a scraped listing row.
        </p>
      </div>

      <div className="coverage-filters">
        <label className="coverage-filters__field">
          <span>Search</span>
          <input
            type="search"
            placeholder="Headline, university, capability…"
            value={filters.q || ''}
            onChange={(e) => handleFilterChange({ q: e.target.value || undefined })}
          />
        </label>
        <label className="coverage-filters__field">
          <span>Packet week</span>
          <select
            value={filters.packet_week || ''}
            onChange={(e) => handleFilterChange({ packet_week: e.target.value || undefined })}
          >
            <option value="">All weeks</option>
            {weeks.map((w) => (
              <option key={w.packet_week} value={w.packet_week}>
                {formatWeek(w.packet_week)} ({w.count})
              </option>
            ))}
          </select>
        </label>
        <label className="coverage-filters__field">
          <span>Match</span>
          <select
            value={filters.match_status || ''}
            onChange={(e) =>
              handleFilterChange({
                match_status: (e.target.value || undefined) as MatchStatus | undefined,
              })
            }
          >
            {MATCH_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="coverage-filters__field">
          <span>Source</span>
          <select
            value={filters.source_class || ''}
            onChange={(e) =>
              handleFilterChange({
                source_class: (e.target.value || undefined) as SourceClass | undefined,
              })
            }
          >
            {SOURCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
        <label className="coverage-filters__field">
          <span>Decision</span>
          <select
            value={filters.decision_status || ''}
            onChange={(e) =>
              handleFilterChange({
                decision_status: (e.target.value || undefined) as DecisionStatus | undefined,
              })
            }
          >
            {DECISION_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="results-meta">
        <div>
          {loading && !data ? (
            <span className="muted">Loading…</span>
          ) : (
            <>
              <b>{total.toLocaleString()}</b> {total === 1 ? 'find' : 'finds'}
            </>
          )}
        </div>
        <div className="sort-hint">Keyed by Monday packet week · not TTO listings</div>
      </div>

      {!loading && items.length === 0 ? (
        <div className="empty-state">
          <h3>No coverage finds</h3>
          <p>
            Weekly upserts land here via <code>POST /api/coverage/upsert</code>. Unmatched
            items are expected — a TTO listing is optional context, not a prerequisite.
          </p>
        </div>
      ) : (
        <div className="coverage-list">
          {items.map((item) => (
              <div
                key={item.id}
                className="coverage-row"
                role="link"
                tabIndex={0}
                onClick={() => navigate(`/coverage/${item.id}`)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    navigate(`/coverage/${item.id}`)
                  }
                }}
              >
                <div className="coverage-row__meta">
                  <span className="coverage-row__week">{formatWeek(item.packet_week)}</span>
                  <span className="coverage-row__univ">{item.university || 'No university'}</span>
                </div>
                <h2 className="coverage-row__headline">{item.headline}</h2>
                {item.summary && <p className="coverage-row__summary">{item.summary}</p>}
                <div className="coverage-row__tags">
                  <span className={`status-pill status-pill--match-${item.match_status}`}>
                    {item.match_status}
                  </span>
                  <span className="status-pill">{sourceLabel(item.source_class)}</span>
                  {item.latest_decision ? (
                    <span className={`status-pill status-pill--decision-${item.latest_decision.status}`}>
                      {item.latest_decision.status}
                    </span>
                  ) : (
                    <span className="status-pill status-pill--muted">No decision</span>
                  )}
                  {item.technology_uuid && (
                    <Link
                      to={`/technology/${item.technology_uuid}`}
                      className="coverage-row__tto"
                      onClick={(e) => e.stopPropagation()}
                    >
                      TTO listing
                    </Link>
                  )}
                </div>
              </div>
          ))}
        </div>
      )}

      {data && data.total > 0 && (
        <Pagination
          page={data.page}
          pages={data.pages}
          total={data.total}
          limit={data.limit}
          onPageChange={setPage}
          onLimitChange={(limit) => handleFilterChange({ limit })}
        />
      )}
    </div>
  )
}
