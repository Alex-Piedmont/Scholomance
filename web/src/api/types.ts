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
  description: string | null
  keywords: string[] | null
  patent_geography: string[] | null
  top_field: string | null
  subfield: string | null
  patent_status: string | null
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
  updated_since?: string
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

// QA types
export interface UniversityQAStatus {
  university: string
  count: number
  status: 'pending' | 'approved'
  conflict_count: number
}

export interface QASample {
  university: string
  technology_ids: number[]
}

export interface QAConflict {
  id: number
  technology_id: number
  field_name: string
  corrected_value: unknown
  new_scraped_value: unknown
}

export interface QARefreshResult {
  university: string
  results: Array<{ id: number; status: string; error?: string }>
}

// Chat types
export interface ChatTechnology {
  uuid: string
  title: string
  university: string
  similarity: number
  description: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  technologies?: ChatTechnology[]
}

export interface ChatRequest {
  query: string
  filters?: {
    university?: string[]
    top_field?: string
    subfield?: string
    patent_status?: string
    from_date?: string
    to_date?: string
  }
  history?: Array<{ role: string; content: string }>
}

export interface ChatResponse {
  response: string
  technologies: ChatTechnology[]
  fallback: boolean
  llm_available: boolean
}

// Coverage / pipeline-decision types (not TTO listings)
export type SourceClass = 'newspaper_tv' | 'specialist'
export type MatchStatus = 'matched' | 'unmatched' | 'candidate'
export type DecisionStatus = 'greenlit' | 'hold' | 'proceed' | 'archive' | 'dropped'

export interface CoverageSource {
  url?: string
  title?: string
  publisher?: string
  [key: string]: unknown
}

export interface PipelineDecision {
  id: string
  coverage_item_id: string
  technology_uuid: string | null
  user_story: string
  status: DecisionStatus
  blocker: string | null
  signed_off_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface CoverageItem {
  id: string
  technology_uuid: string | null
  university: string | null
  headline: string
  summary: string | null
  capability: string | null
  sources: CoverageSource[] | string[]
  source_class: SourceClass
  independence_note: string | null
  coverage_date: string | null
  packet_week: string | null
  match_status: MatchStatus
  created_at: string | null
  updated_at: string | null
  latest_decision: PipelineDecision | null
  decisions: PipelineDecision[] | null
}

export interface PaginatedCoverage {
  items: CoverageItem[]
  total: number
  page: number
  pages: number
  limit: number
}

export interface CoverageWeekCount {
  packet_week: string
  count: number
}

export interface CoverageFilters {
  page?: number
  limit?: number
  q?: string
  packet_week?: string
  university?: string
  match_status?: MatchStatus
  source_class?: SourceClass
  decision_status?: DecisionStatus
  unmatched_only?: boolean
}

export interface CoverageItemCreate {
  headline: string
  source_class: SourceClass
  university?: string | null
  summary?: string | null
  capability?: string | null
  sources?: CoverageSource[]
  independence_note?: string | null
  coverage_date?: string | null
  packet_week?: string | null
  technology_uuid?: string | null
  match_status?: MatchStatus
}

export interface CoverageItemUpdate {
  headline?: string
  source_class?: SourceClass
  university?: string | null
  summary?: string | null
  capability?: string | null
  sources?: CoverageSource[]
  independence_note?: string | null
  coverage_date?: string | null
  packet_week?: string | null
  technology_uuid?: string | null
  match_status?: MatchStatus
}

export interface PipelineDecisionCreate {
  user_story: string
  status: DecisionStatus
  technology_uuid?: string | null
  blocker?: string | null
  signed_off_at?: string | null
}

export interface PipelineDecisionUpdate {
  user_story?: string
  status?: DecisionStatus
  technology_uuid?: string | null
  blocker?: string | null
  signed_off_at?: string | null
}

export interface CoverageUpsertResponse {
  items: Array<{ item: CoverageItem; created: boolean }>
  created: number
  updated: number
}
