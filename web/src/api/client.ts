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
  OpportunitySummary,
  PaginatedOpportunities,
  OpportunityFilters,
  OpportunityStats,
  UniversityQAStatus,
  QASample,
  QAConflict,
  QARefreshResult,
} from './types'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

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

  getByDbId: (id: number) => fetchJson<TechnologyDetail>(`/technologies/by-id/${id}`),

  getTaxonomy: () => fetchJson<TaxonomyField[]>('/taxonomy'),

  patchRawData: async (uuid: string, updates: Record<string, unknown>) => {
    const response = await fetch(`${API_BASE}/technologies/${uuid}/raw-data`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ updates }),
    })
    if (!response.ok) {
      throw new ApiError(response.status, `API error: ${response.statusText}`)
    }
    return response.json() as Promise<TechnologyDetail>
  },

  getProxyUrl: (url: string) =>
    `${API_BASE}/proxy?url=${encodeURIComponent(url)}`,
}

// Mutation helpers
async function postJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' })

  if (!response.ok) {
    throw new ApiError(response.status, `API error: ${response.statusText}`)
  }

  return response.json()
}

async function postJsonWithBody<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw new ApiError(response.status, `API error: ${response.statusText}`)
  }

  return response.json()
}

async function putJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, { method: 'PUT' })

  if (!response.ok) {
    throw new ApiError(response.status, `API error: ${response.statusText}`)
  }

  return response.json()
}

export const opportunitiesApi = {
  list: (filters: OpportunityFilters = {}) => {
    const query = buildQueryString(filters as Record<string, unknown>)
    return fetchJson<PaginatedOpportunities>(`/opportunities${query}`)
  },

  get: (uuid: string) => fetchJson<OpportunitySummary>(`/opportunities/${uuid}`),

  assess: (uuid: string) => postJson<OpportunitySummary>(`/opportunities/${uuid}/assess`),

  getStats: () => fetchJson<OpportunityStats>('/opportunities/stats'),
}

// QA API
export const qaApi = {
  getUniversities: () => fetchJson<UniversityQAStatus[]>('/qa/universities'),

  approve: (code: string) => putJson<{ status: string }>(`/qa/universities/${code}/approve`),

  unapprove: (code: string) => putJson<{ status: string }>(`/qa/universities/${code}/unapprove`),

  getSample: (university: string) => fetchJson<QASample>(`/qa/samples/${university}`),

  createSample: (university: string) => postJson<QASample>(`/qa/samples/${university}`),

  refreshSample: (university: string) => postJson<QARefreshResult>(`/qa/samples/${university}/refresh`),

  getConflicts: (university: string) => fetchJson<QAConflict[]>(`/qa/conflicts/${university}`),

  resolveConflict: (id: number, resolution: 'keep_correction' | 'accept_new') =>
    postJsonWithBody<{ resolved: boolean }>(`/qa/conflicts/${id}/resolve`, { resolution }),
}

export { ApiError }
