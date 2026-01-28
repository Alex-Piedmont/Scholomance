import { useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Header } from '../components/Layout'
import { FilterPanel, TechnologyTable, Pagination } from '../components/Browser'
import { ErrorMessage, EmptyState } from '../components/common'
import { useTechnologies } from '../hooks'
import type { TechnologyFilters } from '../api/types'

export function BrowserPage() {
  const [searchParams, setSearchParams] = useSearchParams()

  // Parse URL params into filters
  const filtersFromUrl: TechnologyFilters = {
    page: parseInt(searchParams.get('page') || '1', 10),
    limit: parseInt(searchParams.get('limit') || '20', 10),
    q: searchParams.get('q') || undefined,
    top_field: searchParams.get('top_field') || undefined,
    subfield: searchParams.get('subfield') || undefined,
    university: searchParams.get('university') || undefined,
    from_date: searchParams.get('from_date') || undefined,
    to_date: searchParams.get('to_date') || undefined,
  }

  const { data, loading, error, filters, setFilters, setPage, refetch } = useTechnologies(filtersFromUrl)

  // Sync filters to URL
  const updateUrl = useCallback(
    (newFilters: TechnologyFilters) => {
      const params = new URLSearchParams()

      if (newFilters.page && newFilters.page > 1) {
        params.set('page', String(newFilters.page))
      }
      if (newFilters.limit && newFilters.limit !== 20) {
        params.set('limit', String(newFilters.limit))
      }
      if (newFilters.q) params.set('q', newFilters.q)
      if (newFilters.top_field) params.set('top_field', newFilters.top_field)
      if (newFilters.subfield) params.set('subfield', newFilters.subfield)
      if (newFilters.university) params.set('university', newFilters.university)
      if (newFilters.from_date) params.set('from_date', newFilters.from_date)
      if (newFilters.to_date) params.set('to_date', newFilters.to_date)

      setSearchParams(params, { replace: true })
    },
    [setSearchParams]
  )

  // Update URL when filters change
  useEffect(() => {
    updateUrl(filters)
  }, [filters, updateUrl])

  const handleFilterChange = (newFilters: Partial<TechnologyFilters>) => {
    setFilters({ ...filters, ...newFilters })
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  const handleLimitChange = (newLimit: number) => {
    setFilters({ ...filters, limit: newLimit, page: 1 })
  }

  const hasActiveFilters = filters.q || filters.top_field || filters.subfield || filters.university

  if (error) {
    return (
      <div>
        <Header title="Browse Technologies" />
        <div className="p-6">
          <FilterPanel filters={filters} onFilterChange={handleFilterChange} />
          <ErrorMessage
            message="Failed to load technologies. Please try again."
            onRetry={refetch}
          />
        </div>
      </div>
    )
  }

  return (
    <div>
      <Header title="Browse Technologies" />

      <div className="p-6">
        <FilterPanel filters={filters} onFilterChange={handleFilterChange} />

        {!loading && data?.items.length === 0 ? (
          <EmptyState
            title="No technologies found"
            description={hasActiveFilters ? "Try adjusting your filters" : "No technologies in the database yet"}
            action={hasActiveFilters ? {
              label: "Clear Filters",
              onClick: () => handleFilterChange({
                q: undefined,
                top_field: undefined,
                subfield: undefined,
                university: undefined,
              })
            } : undefined}
          />
        ) : (
          <>
            <TechnologyTable data={data?.items || []} loading={loading} />

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
