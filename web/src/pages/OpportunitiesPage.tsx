import { useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Header } from '../components/Layout'
import { Pagination } from '../components/Browser'
import { ErrorMessage, EmptyState } from '../components/common'
import { useOpportunities } from '../hooks'
import { getUniversityName } from '../utils/universityNames'
import type { OpportunityFilters } from '../api/types'

const CATEGORY_OPTIONS = [
  { value: '', label: 'All Categories' },
  { value: 'trl_gap', label: 'TRL Gap' },
  { value: 'false_barrier', label: 'False Barrier' },
  { value: 'alt_application', label: 'Alt Application' },
] as const

const SORT_OPTIONS = [
  { value: 'composite', label: 'Composite' },
  { value: 'trl_gap', label: 'TRL Gap' },
  { value: 'false_barrier', label: 'False Barrier' },
  { value: 'alt_application', label: 'Alt Application' },
] as const

function ScorePill({ score }: { score: number | string | null }) {
  if (score === null || score === undefined) {
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-400">--</span>
  }
  const num = typeof score === 'string' ? parseFloat(score) : score
  if (isNaN(num)) {
    return <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-400">--</span>
  }
  const color =
    num >= 0.7
      ? 'bg-green-100 text-green-700'
      : num >= 0.4
        ? 'bg-yellow-100 text-yellow-700'
        : 'bg-gray-100 text-gray-500'
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${color}`}>{num.toFixed(2)}</span>
}

export function OpportunitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const filtersFromUrl: OpportunityFilters = {
    page: parseInt(searchParams.get('page') || '1', 10),
    limit: parseInt(searchParams.get('limit') || '20', 10),
    q: searchParams.get('q') || undefined,
    category: (searchParams.get('category') as OpportunityFilters['category']) || undefined,
    min_score: searchParams.get('min_score') ? parseFloat(searchParams.get('min_score')!) : undefined,
    min_confidence: searchParams.get('min_confidence') ? parseFloat(searchParams.get('min_confidence')!) : undefined,
    university: searchParams.getAll('university').length > 0 ? searchParams.getAll('university') : undefined,
    sort: (searchParams.get('sort') as OpportunityFilters['sort']) || undefined,
  }

  const { data, loading, error, filters, setFilters, setPage, refetch } = useOpportunities(filtersFromUrl)

  const updateUrl = useCallback(
    (newFilters: OpportunityFilters) => {
      const params = new URLSearchParams()
      if (newFilters.page && newFilters.page > 1) params.set('page', String(newFilters.page))
      if (newFilters.limit && newFilters.limit !== 20) params.set('limit', String(newFilters.limit))
      if (newFilters.q) params.set('q', newFilters.q)
      if (newFilters.category) params.set('category', newFilters.category)
      if (newFilters.min_score !== undefined) params.set('min_score', String(newFilters.min_score))
      if (newFilters.min_confidence !== undefined) params.set('min_confidence', String(newFilters.min_confidence))
      if (newFilters.university) {
        for (const uni of newFilters.university) params.append('university', uni)
      }
      if (newFilters.sort) params.set('sort', newFilters.sort)
      setSearchParams(params, { replace: true })
    },
    [setSearchParams]
  )

  useEffect(() => {
    updateUrl(filters)
  }, [filters, updateUrl])

  const handleFilterChange = (newFilters: Partial<OpportunityFilters>) => {
    setFilters({ ...filters, ...newFilters })
  }

  const handlePageChange = (newPage: number) => setPage(newPage)
  const handleLimitChange = (newLimit: number) => setFilters({ ...filters, limit: newLimit, page: 1 })

  const hasActiveFilters = filters.q || filters.category || filters.min_score !== undefined || (filters.university && filters.university.length > 0)

  if (error) {
    return (
      <div>
        <Header title="Opportunities" />
        <div className="p-6">
          <ErrorMessage message="Failed to load opportunities. Please try again." onRetry={refetch} />
        </div>
      </div>
    )
  }

  return (
    <div>
      <Header title="Opportunities" />

      <div className="p-6">
        {/* Filter Bar */}
        <div className="mb-6 flex flex-wrap items-end gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          {/* Search */}
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-medium text-gray-500 mb-1">Search</label>
            <input
              type="text"
              placeholder="Search opportunities..."
              value={filters.q || ''}
              onChange={(e) => handleFilterChange({ q: e.target.value || undefined })}
              className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Category</label>
            <select
              value={filters.category || ''}
              onChange={(e) => handleFilterChange({ category: (e.target.value || undefined) as OpportunityFilters['category'] })}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* Min Score */}
          <div className="min-w-[140px]">
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Min Score: {filters.min_score !== undefined ? filters.min_score.toFixed(1) : '0.0'}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={filters.min_score ?? 0}
              onChange={(e) => {
                const val = parseFloat(e.target.value)
                handleFilterChange({ min_score: val > 0 ? val : undefined })
              }}
              className="w-full"
            />
          </div>

          {/* Sort */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Sort By</label>
            <select
              value={filters.sort || 'composite'}
              onChange={(e) => handleFilterChange({ sort: e.target.value as OpportunityFilters['sort'] })}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {SORT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Results */}
        {!loading && data?.items.length === 0 ? (
          <EmptyState
            title="No opportunities found"
            description={hasActiveFilters ? 'Try adjusting your filters' : 'No assessed opportunities yet'}
            action={hasActiveFilters ? {
              label: 'Clear Filters',
              onClick: () => handleFilterChange({ q: undefined, category: undefined, min_score: undefined, university: undefined }),
            } : undefined}
          />
        ) : (
          <>
            <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Composite</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Title</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">University</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Field</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">TRL Gap</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">False Barrier</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Alt App</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">Tier</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {loading
                    ? Array.from({ length: 5 }).map((_, i) => (
                        <tr key={i} className="animate-pulse">
                          {Array.from({ length: 8 }).map((_, j) => (
                            <td key={j} className="px-4 py-3">
                              <div className="h-4 w-16 rounded bg-gray-200" />
                            </td>
                          ))}
                        </tr>
                      ))
                    : data?.items.map((opp) => (
                        <tr
                          key={opp.uuid}
                          onClick={() => navigate(`/technology/${opp.uuid}`)}
                          className="cursor-pointer hover:bg-gray-50 transition-colors"
                        >
                          <td className="px-4 py-3 whitespace-nowrap">
                            <ScorePill score={opp.composite_score} />
                          </td>
                          <td className="px-4 py-3 text-sm font-medium text-gray-900 max-w-[300px] truncate">
                            {opp.title}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                            {getUniversityName(opp.university)}
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                            {opp.top_field || '--'}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <ScorePill score={opp.trl_gap?.score ?? null} />
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <ScorePill score={opp.false_barrier?.score ?? null} />
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <ScorePill score={opp.alt_application?.score ?? null} />
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                            {opp.assessment_tier || '--'}
                          </td>
                        </tr>
                      ))}
                </tbody>
              </table>
            </div>

            {data && data.total > 0 && (
              <Pagination
                page={data.page}
                pages={data.pages}
                total={data.total}
                limit={data.limit}
                onPageChange={handlePageChange}
                onLimitChange={handleLimitChange}
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}
