import type {
  StatsOverview,
  FieldCount,
  UniversityCount,
  TimelinePoint,
  KeywordCount,
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
  getKeywords: () => fetchJson<KeywordCount[]>('/stats/keywords'),
}

// Technologies API
export const technologiesApi = {
  list: (filters: TechnologyFilters = {}) => {
    const resolved = { ...filters }
    // Decode multiselect date encoding: from_date="2024,2024-03", to_date="sel"
    if (resolved.to_date === 'sel' && resolved.from_date) {
      const selections = resolved.from_date.split(',')
      let minDate = '9999-12-31'
      let maxDate = '0000-01-01'
      for (const key of selections) {
        const parts = key.split('-')
        const year = parseInt(parts[0])
        if (parts.length === 1) {
          if (`${year}-01-01` < minDate) minDate = `${year}-01-01`
          if (`${year}-12-31` > maxDate) maxDate = `${year}-12-31`
        } else {
          const month = parseInt(parts[1])
          const from = `${year}-${String(month).padStart(2, '0')}-01`
          const lastDay = new Date(year, month, 0).getDate()
          const to = `${year}-${String(month).padStart(2, '0')}-${lastDay}`
          if (from < minDate) minDate = from
          if (to > maxDate) maxDate = to
        }
      }
      resolved.from_date = minDate
      resolved.to_date = maxDate
    }
    const query = buildQueryString(resolved as Record<string, unknown>)
    return fetchJson<PaginatedTechnologies>(`/technologies${query}`)
  },

  get: (uuid: string) => fetchJson<TechnologyDetail>(`/technologies/${uuid}`),

  getTaxonomy: () => fetchJson<TaxonomyField[]>('/taxonomy'),
}

export { ApiError }
