import { useState, useEffect, useCallback } from 'react'
import { technologiesApi } from '../api/client'
import type {
  PaginatedTechnologies,
  TechnologyFilters,
  TaxonomyField,
} from '../api/types'

interface UseTechnologiesResult {
  data: PaginatedTechnologies | null
  loading: boolean
  error: Error | null
  filters: TechnologyFilters
  setFilters: (filters: TechnologyFilters) => void
  setPage: (page: number) => void
  refetch: () => void
}

export function useTechnologies(
  initialFilters: TechnologyFilters = {}
): UseTechnologiesResult {
  const [data, setData] = useState<PaginatedTechnologies | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [filters, setFiltersState] = useState<TechnologyFilters>({
    page: 1,
    limit: 20,
    ...initialFilters,
  })

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await technologiesApi.list(filters)
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'))
    } finally {
      setLoading(false)
    }
  }, [filters])

  useEffect(() => {
    fetch()
  }, [fetch])

  const setFilters = useCallback((newFilters: TechnologyFilters) => {
    setFiltersState((prev) => ({
      ...prev,
      ...newFilters,
      page: 1, // Reset to first page when filters change
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
    refetch: fetch,
  }
}

interface UseTaxonomyResult {
  data: TaxonomyField[] | null
  loading: boolean
  error: Error | null
}

export function useTaxonomy(): UseTaxonomyResult {
  const [data, setData] = useState<TaxonomyField[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const fetch = async () => {
      setLoading(true)
      setError(null)
      try {
        const result = await technologiesApi.getTaxonomy()
        setData(result)
      } catch (e) {
        setError(e instanceof Error ? e : new Error('Unknown error'))
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  return { data, loading, error }
}
