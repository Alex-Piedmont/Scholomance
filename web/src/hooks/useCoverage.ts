import { useState, useEffect, useCallback } from 'react'
import { coverageApi } from '../api/client'
import type {
  CoverageFilters,
  CoverageItem,
  CoverageWeekCount,
  PaginatedCoverage,
} from '../api/types'

interface UseCoverageResult {
  data: PaginatedCoverage | null
  weeks: CoverageWeekCount[]
  loading: boolean
  error: Error | null
  filters: CoverageFilters
  setFilters: (filters: CoverageFilters) => void
  setPage: (page: number) => void
  refetch: () => void
}

export function useCoverage(initialFilters: CoverageFilters = {}): UseCoverageResult {
  const [data, setData] = useState<PaginatedCoverage | null>(null)
  const [weeks, setWeeks] = useState<CoverageWeekCount[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [filters, setFiltersState] = useState<CoverageFilters>({
    page: 1,
    limit: 20,
    ...initialFilters,
  })

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [result, weekRows] = await Promise.all([
        coverageApi.list(filters),
        coverageApi.weeks().catch(() => [] as CoverageWeekCount[]),
      ])
      setData(result)
      setWeeks(weekRows)
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'))
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const setFilters = useCallback((newFilters: CoverageFilters) => {
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
    weeks,
    loading,
    error,
    filters,
    setFilters,
    setPage,
    refetch: fetchData,
  }
}

interface UseCoverageItemResult {
  data: CoverageItem | null
  loading: boolean
  error: Error | null
  refetch: () => void
}

export function useCoverageItem(id: string | undefined): UseCoverageItemResult {
  const [data, setData] = useState<CoverageItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchItem = useCallback(async () => {
    if (!id) {
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const result = await coverageApi.get(id)
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchItem()
  }, [fetchItem])

  return { data, loading, error, refetch: fetchItem }
}
