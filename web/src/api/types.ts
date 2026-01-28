// Stats types
export interface StatsOverview {
  total_technologies: number
  total_universities: number
  total_fields: number
  classified_count: number
  pending_count: number
  last_scrape: string | null
}

export interface SubfieldCount {
  subfield: string
  count: number
}

export interface FieldCount {
  top_field: string
  count: number
  subfields: SubfieldCount[]
}

export interface UniversityCount {
  university: string
  count: number
  last_scraped: string | null
}

export interface TimelinePoint {
  month: string
  count: number
}

// Technology types
export interface TechnologySummary {
  uuid: string
  university: string
  tech_id: string
  title: string
  url: string
  top_field: string | null
  subfield: string | null
  first_seen: string | null
}

export interface TechnologyDetail {
  uuid: string
  university: string
  tech_id: string
  title: string
  description: string | null
  url: string
  top_field: string | null
  subfield: string | null
  patent_geography: string[] | null
  keywords: string[] | null
  classification_status: string | null
  classification_confidence: number | null
  scraped_at: string | null
  updated_at: string | null
  first_seen: string | null
  raw_data: Record<string, unknown> | null
}

export interface PaginatedTechnologies {
  items: TechnologySummary[]
  total: number
  page: number
  pages: number
  limit: number
}

// Taxonomy types
export interface TaxonomySubfield {
  name: string
  description: string | null
}

export interface TaxonomyField {
  name: string
  subfields: TaxonomySubfield[]
}

// Filter params
export interface TechnologyFilters {
  page?: number
  limit?: number
  q?: string
  top_field?: string
  subfield?: string
  university?: string
  from_date?: string
  to_date?: string
}
