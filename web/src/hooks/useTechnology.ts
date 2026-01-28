import { useState, useEffect } from 'react'
import { technologiesApi } from '../api/client'
import type { TechnologyDetail } from '../api/types'

interface UseTechnologyResult {
  data: TechnologyDetail | null
  loading: boolean
  error: Error | null
  refetch: () => void
}

export function useTechnology(uuid: string | undefined): UseTechnologyResult {
  const [data, setData] = useState<TechnologyDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetch = async () => {
    if (!uuid) {
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    try {
      const result = await technologiesApi.get(uuid)
      setData(result)
    } catch (e) {
      setError(e instanceof Error ? e : new Error('Unknown error'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch()
  }, [uuid])

  return { data, loading, error, refetch: fetch }
}
