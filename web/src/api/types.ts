// Stats types
export interface StatsOverview {
  total_technologies: number
  total_universities: number
  total_fields: number
  granted_patents: number
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

export interface KeywordCount {
  keyword: string
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
  published_on: string | null
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
  patent_status: string | null
  patent_status_confidence: string | null
  patent_status_source: string | null
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
  university?: string[]
  patent_status?: string
  from_date?: string
  to_date?: string
}

// Assessment types
export interface CategoryAssessment {
  score: number | null
  confidence: number | null
  reasoning: string | null
  details: Record<string, unknown> | null
}

export interface OpportunitySummary {
  uuid: string
  title: string
  university: string
  top_field: string | null
  subfield: string | null
  patent_status: string | null
  composite_score: number | null
  assessment_tier: string | null
  trl_gap: CategoryAssessment | null
  false_barrier: CategoryAssessment | null
  alt_application: CategoryAssessment | null
  assessed_at: string | null
}

export interface PaginatedOpportunities {
  items: OpportunitySummary[]
  total: number
  page: number
  pages: number
  limit: number
}

export interface OpportunityStats {
  total_assessed: number
  total_full: number
  total_limited: number
  avg_composite_score: number | null
  high_trl_gap_count: number
  high_false_barrier_count: number
  high_alt_application_count: number
}

export interface OpportunityFilters {
  page?: number
  limit?: number
  q?: string
  category?: 'trl_gap' | 'false_barrier' | 'alt_application'
  min_score?: number
  min_confidence?: number
  top_field?: string
  subfield?: string
  university?: string[]
  patent_status?: string
  assessment_tier?: 'full' | 'limited'
  sort?: 'composite' | 'trl_gap' | 'false_barrier' | 'alt_application'
}
