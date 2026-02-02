import type {
  StatsOverview,
  FieldCount,
  UniversityCount,
  TimelinePoint,
  PaginatedTechnologies,
  TechnologyDetail,
  TaxonomyField,
  TechnologyFilters,
} from './types'

const API_BASE = '/api'

class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function fetchJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`)

  if (!response.ok) {
    throw new ApiError(response.status, `API error: ${response.statusText}`)
  }

  return response.json()
}

function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams()

  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') {
      if (Array.isArray(value)) {
        for (const item of value) {
          searchParams.append(key, String(item))
        }
      } else {
        searchParams.append(key, String(value))
      }
    }
  }

  const queryString = searchParams.toString()
  return queryString ? `?${queryString}` : ''
}

// Stats API
export const statsApi = {
  getOverview: () => fetchJson<StatsOverview>('/stats/overview'),

  getByField: () => fetchJson<FieldCount[]>('/stats/by-field'),

  getByUniversity: () => fetchJson<UniversityCount[]>('/stats/by-university'),

  getTimeline: () => fetchJson<TimelinePoint[]>('/stats/timeline'),
}

// Technologies API
export const technologiesApi = {
  list: (filters: TechnologyFilters = {}) => {
    const query = buildQueryString(filters as Record<string, unknown>)
    return fetchJson<PaginatedTechnologies>(`/technologies${query}`)
  },

  get: (uuid: string) => fetchJson<TechnologyDetail>(`/technologies/${uuid}`),

  getTaxonomy: () => fetchJson<TaxonomyField[]>('/taxonomy'),
}

export { ApiError }
