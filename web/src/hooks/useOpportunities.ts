import { useState, useEffect, useCallback } from 'react'
import { opportunitiesApi } from '../api/client'
import type { PaginatedOpportunities, OpportunityFilters } from '../api/types'

interface UseOpportunitiesResult {
  data: PaginatedOpportunities | null
  loading: boolean
  error: Error | null
  filters: OpportunityFilters
  setFilters: (filters: OpportunityFilters) => void
  setPage: (page: number) => void
  refetch: () => void
}

export function useOpportunities(
  initialFilters: OpportunityFilters = {}
): UseOpportunitiesResult {
  const [data, setData] = useState<PaginatedOpportunities | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [filters, setFiltersState] = useState<OpportunityFilters>({
    page: 1,
    limit: 20,
    ...initialFilters,
  })

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await opportunitiesApi.list(filters)
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'))
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const setFilters = useCallback((newFilters: OpportunityFilters) => {
    setFiltersState((prev) => ({
      ...prev,
      ...newFilters,
      page: 1,
    }))
  }, [])

  const setPage = useCallback((page: number) => {
    setFiltersState((prev) => ({ ...prev, page }))
  }, [])

  return {
    data,
    loading,
    error,
    filters,
    setFilters,
    setPage,
    refetch: fetchData,
  }
}
