import { useState, useEffect } from 'react'
import { statsApi } from '../api/client'
import type {
  StatsOverview,
  FieldCount,
  UniversityCount,
  TimelinePoint,
} from '../api/types'

interface UseStatsResult<T> {
  data: T | null
  loading: boolean
  error: Error | null
  refetch: () => void
}

export function useStatsOverview(): UseStatsResult<StatsOverview> {
  const [data, setData] = useState<StatsOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetch = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await statsApi.getOverview()
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
  }, [])

  return { data, loading, error, refetch: fetch }
}

export function useStatsByField(): UseStatsResult<FieldCount[]> {
  const [data, setData] = useState<FieldCount[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetch = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await statsApi.getByField()
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
  }, [])

  return { data, loading, error, refetch: fetch }
}

export function useStatsByUniversity(): UseStatsResult<UniversityCount[]> {
  const [data, setData] = useState<UniversityCount[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetch = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await statsApi.getByUniversity()
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
  }, [])

  return { data, loading, error, refetch: fetch }
}

export function useStatsTimeline(): UseStatsResult<TimelinePoint[]> {
  const [data, setData] = useState<TimelinePoint[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetch = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await statsApi.getTimeline()
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
  }, [])

  return { data, loading, error, refetch: fetch }
}
