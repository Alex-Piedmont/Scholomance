"""Pydantic schemas for API responses."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


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
