"""Pydantic schemas for API responses."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


# Stats schemas
class SubfieldCount(BaseModel):
    subfield: str
    count: int


class FieldCount(BaseModel):
    top_field: str
    count: int
    subfields: list[SubfieldCount]


class UniversityCount(BaseModel):
    university: str
    count: int
    last_scraped: Optional[datetime] = None


class TimelinePoint(BaseModel):
    month: str  # Format: "2024-01"
    count: int


class KeywordCount(BaseModel):
    keyword: str
    count: int


class StatsOverview(BaseModel):
    total_technologies: int
    total_universities: int
    total_fields: int
    granted_patents: int
    last_scrape: Optional[datetime] = None


# Technology schemas
class TechnologySummary(BaseModel):
    uuid: str
    university: str
    tech_id: str
    title: str
    url: str
    description: Optional[str] = None
    keywords: Optional[list[str]] = None
    patent_geography: Optional[list[str]] = None
    top_field: Optional[str] = None
    subfield: Optional[str] = None
    patent_status: Optional[str] = None
    first_seen: Optional[datetime] = None
    published_on: Optional[str] = None

    class Config:
        from_attributes = True


class TechnologyDetail(BaseModel):
    uuid: str
    university: str
    tech_id: str
    title: str
    description: Optional[str] = None
    url: str
    top_field: Optional[str] = None
    subfield: Optional[str] = None
    patent_geography: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    classification_status: Optional[str] = None
    classification_confidence: Optional[Decimal] = None
    patent_status: Optional[str] = None
    patent_status_confidence: Optional[Decimal] = None
    patent_status_source: Optional[str] = None
    scraped_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    first_seen: Optional[datetime] = None
    raw_data: Optional[dict] = None

    class Config:
        from_attributes = True


class PaginatedTechnologies(BaseModel):
    items: list[TechnologySummary]
    total: int
    page: int
    pages: int
    limit: int


# Taxonomy schemas
class TaxonomySubfield(BaseModel):
    name: str
    description: Optional[str] = None


class TaxonomyField(BaseModel):
    name: str
    subfields: list[TaxonomySubfield]


# Assessment/Opportunity schemas
class CategoryAssessmentResponse(BaseModel):
    score: Optional[Decimal] = None
    confidence: Optional[Decimal] = None
    reasoning: Optional[str] = None
    details: Optional[dict] = None

class OpportunitySummary(BaseModel):
    uuid: str
    title: str
    university: str
    top_field: Optional[str] = None
    subfield: Optional[str] = None
    patent_status: Optional[str] = None
    composite_score: Optional[Decimal] = None
    assessment_tier: Optional[str] = None
    trl_gap: Optional[CategoryAssessmentResponse] = None
    false_barrier: Optional[CategoryAssessmentResponse] = None
    alt_application: Optional[CategoryAssessmentResponse] = None
    assessed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaginatedOpportunities(BaseModel):
    items: list[OpportunitySummary]
    total: int
    page: int
    pages: int
    limit: int

class OpportunityStats(BaseModel):
    total_assessed: int
    total_full: int
    total_limited: int
    avg_composite_score: Optional[Decimal] = None
    high_trl_gap_count: int  # score > 0.7
    high_false_barrier_count: int
    high_alt_application_count: int


# Chat schemas
class ChatFilters(BaseModel):
    university: Optional[list[str]] = None
    top_field: Optional[str] = None
    subfield: Optional[str] = None
    patent_status: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class ChatHistoryMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    query: str
    filters: Optional[ChatFilters] = None
    history: Optional[list[ChatHistoryMessage]] = None


class ChatTechnology(BaseModel):
    uuid: str
    title: str
    university: str
    similarity: float
    description: str


class ChatResponse(BaseModel):
    response: str
    technologies: list[ChatTechnology]
    fallback: bool = False
    llm_available: bool = True


# Coverage / pipeline-decision schemas
# These are independent of TTO listing rows (Technology*).

SourceClass = Literal["newspaper_tv", "specialist"]
MatchStatus = Literal["matched", "unmatched", "candidate"]
DecisionStatus = Literal["greenlit", "hold", "proceed", "archive", "dropped"]


class PipelineDecisionResponse(BaseModel):
    id: str
    coverage_item_id: str
    technology_uuid: Optional[str] = None
    user_story: str
    status: DecisionStatus
    blocker: Optional[str] = None
    signed_off_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PipelineDecisionCreate(BaseModel):
    user_story: str
    status: DecisionStatus
    technology_uuid: Optional[UUID] = None
    blocker: Optional[str] = None
    signed_off_at: Optional[datetime] = None


class PipelineDecisionUpdate(BaseModel):
    user_story: Optional[str] = None
    status: Optional[DecisionStatus] = None
    technology_uuid: Optional[UUID] = None
    blocker: Optional[str] = None
    signed_off_at: Optional[datetime] = None


class CoverageItemResponse(BaseModel):
    id: str
    technology_uuid: Optional[str] = None
    university: Optional[str] = None
    headline: str
    summary: Optional[str] = None
    capability: Optional[str] = None
    sources: list[Any] = Field(default_factory=list)
    source_class: SourceClass
    independence_note: Optional[str] = None
    coverage_date: Optional[date] = None
    packet_week: Optional[date] = None
    match_status: MatchStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    latest_decision: Optional[PipelineDecisionResponse] = None
    decisions: Optional[list[PipelineDecisionResponse]] = None

    class Config:
        from_attributes = True


class CoverageItemCreate(BaseModel):
    headline: str
    source_class: SourceClass
    university: Optional[str] = None
    summary: Optional[str] = None
    capability: Optional[str] = None
    sources: list[Any] = Field(default_factory=list)
    independence_note: Optional[str] = None
    coverage_date: Optional[date] = None
    packet_week: Optional[date] = None
    technology_uuid: Optional[UUID] = None
    match_status: Optional[MatchStatus] = None


class CoverageItemUpdate(BaseModel):
    headline: Optional[str] = None
    source_class: Optional[SourceClass] = None
    university: Optional[str] = None
    summary: Optional[str] = None
    capability: Optional[str] = None
    sources: Optional[list[Any]] = None
    independence_note: Optional[str] = None
    coverage_date: Optional[date] = None
    packet_week: Optional[date] = None
    technology_uuid: Optional[UUID] = None
    match_status: Optional[MatchStatus] = None


class CoverageUpsertRequest(BaseModel):
    """Weekly packet upsert. One item, or a batch under ``items``."""

    items: Optional[list[CoverageItemCreate]] = None
    headline: Optional[str] = None
    source_class: Optional[SourceClass] = None
    university: Optional[str] = None
    summary: Optional[str] = None
    capability: Optional[str] = None
    sources: Optional[list[Any]] = None
    independence_note: Optional[str] = None
    coverage_date: Optional[date] = None
    packet_week: Optional[date] = None
    technology_uuid: Optional[UUID] = None
    match_status: Optional[MatchStatus] = None
    auto_match: bool = True


class CoverageUpsertItemResult(BaseModel):
    item: CoverageItemResponse
    created: bool


class CoverageUpsertResponse(BaseModel):
    items: list[CoverageUpsertItemResult]
    created: int
    updated: int


class PaginatedCoverage(BaseModel):
    items: list[CoverageItemResponse]
    total: int
    page: int
    pages: int
    limit: int


class CoverageWeekCount(BaseModel):
    packet_week: date
    count: int


class PaginatedDecisions(BaseModel):
    items: list[PipelineDecisionResponse]
    total: int
    page: int
    pages: int
    limit: int
