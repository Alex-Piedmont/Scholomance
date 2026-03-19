"""Technology API endpoints."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import aiohttp
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import String, func, or_

from ...database import db, Technology
from ...scrapers import SCRAPERS, get_scraper
from ...taxonomy import TAXONOMY
from ..schemas import (
    TechnologySummary,
    TechnologyDetail,
    PaginatedTechnologies,
    TaxonomyField,
    TaxonomySubfield,
)

# ── Playwright rendering for SPA pages ───────────────────────────

_render_semaphore = asyncio.Semaphore(1)
_render_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 30 * 60  # 30 minutes


def _sync_render(url: str) -> str:
    """Render a page with Playwright (runs in thread pool)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=15000, wait_until="networkidle")
        html = page.content()
        browser.close()
        return html


async def render_with_playwright(url: str) -> str:
    """Render a SPA page using Playwright with semaphore and caching."""
    # Check cache
    now = time.time()
    cached = _render_cache.get(url)
    if cached and (now - cached[1]) < _CACHE_TTL:
        return cached[0]

    async with _render_semaphore:
        # Double-check cache after acquiring semaphore
        cached = _render_cache.get(url)
        if cached and (now - cached[1]) < _CACHE_TTL:
            return cached[0]

        html = await asyncio.to_thread(_sync_render, url)
        _render_cache[url] = (html, time.time())
        return html


def _is_spa_page(html: str) -> bool:
    """Detect if the HTML indicates a JavaScript SPA that needs rendering."""
    if len(html) < 500:
        return True
    lower = html.lower()
    if "you need to enable javascript" in lower:
        return True
    if '<div id="root"></div>' in html or '<div id="root"> </div>' in html:
        return True
    if '<div id="app"></div>' in html or '<div id="app"> </div>' in html:
        return True
    return False


def _is_allowed_proxy_url(url: str) -> bool:
    """Validate that the URL belongs to a known university base URL."""
    allowed_bases = set()
    for code in SCRAPERS:
        try:
            scraper = get_scraper(code)
            if hasattr(scraper, "base_url") and scraper.base_url:
                allowed_bases.add(scraper.base_url.rstrip("/"))
        except Exception:
            pass
    return any(url.startswith(base) for base in allowed_bases)

router = APIRouter(prefix="/api", tags=["technologies"])


@router.get("/technologies", response_model=PaginatedTechnologies)
def list_technologies(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    q: Optional[str] = Query(None, description="Search in title and description"),
    top_field: Optional[str] = Query(None, description="Filter by top field"),
    subfield: Optional[str] = Query(None, description="Filter by subfield"),
    university: Optional[list[str]] = Query(None, description="Filter by university (multi-select)"),
    patent_status: Optional[str] = Query(None, description="Filter by patent status (unknown, pending, provisional, filed, granted, expired)"),
    from_date: Optional[datetime] = Query(None, description="Filter by first_seen >= date"),
    to_date: Optional[datetime] = Query(None, description="Filter by first_seen <= date"),
    updated_since: Optional[datetime] = Query(None, description="Filter by updated_at >= timestamp (for QA of recent re-scrapes)"),
):
    """List technologies with pagination and filters."""
    with db.get_session() as session:
        query = session.query(Technology)

        # Apply filters
        if q:
            search_pattern = f"%{q}%"
            query = query.filter(
                or_(
                    Technology.title.ilike(search_pattern),
                    Technology.description.ilike(search_pattern),
                    Technology.raw_data.cast(String).ilike(search_pattern),
                    Technology.keywords.cast(String).ilike(search_pattern),
                )
            )

        if top_field:
            query = query.filter(Technology.top_field == top_field)

        if subfield:
            query = query.filter(Technology.subfield == subfield)

        if university:
            query = query.filter(Technology.university.in_(university))

        if patent_status:
            query = query.filter(Technology.patent_status == patent_status)

        if from_date:
            query = query.filter(Technology.first_seen >= from_date)

        if to_date:
            query = query.filter(Technology.first_seen <= to_date)

        if updated_since:
            query = query.filter(Technology.updated_at >= updated_since)

        # Get total count
        total = query.count()

        # Calculate pagination
        pages = (total + limit - 1) // limit if total > 0 else 1
        offset = (page - 1) * limit

        # Get paginated results
        technologies = (
            query
            .order_by(Technology.first_seen.desc().nullslast())
            .offset(offset)
            .limit(limit)
            .all()
        )

        items = [
            TechnologySummary(
                uuid=str(t.uuid),
                university=t.university,
                tech_id=t.tech_id,
                title=t.title,
                url=t.url,
                top_field=t.top_field,
                subfield=t.subfield,
                patent_status=t.patent_status,
                first_seen=t.first_seen,
                published_on=(t.raw_data or {}).get('published_on') or (t.raw_data or {}).get('web_published'),
            )
            for t in technologies
        ]

        return PaginatedTechnologies(
            items=items,
            total=total,
            page=page,
            pages=pages,
            limit=limit,
        )


@router.get("/technologies/{uuid}", response_model=TechnologyDetail)
def get_technology(uuid: UUID):
    """Get a single technology by UUID."""
    with db.get_session() as session:
        tech = session.query(Technology).filter(Technology.uuid == uuid).first()

        if not tech:
            raise HTTPException(status_code=404, detail="Technology not found")

        return TechnologyDetail(
            uuid=str(tech.uuid),
            university=tech.university,
            tech_id=tech.tech_id,
            title=tech.title,
            description=tech.description,
            url=tech.url,
            top_field=tech.top_field,
            subfield=tech.subfield,
            patent_geography=tech.patent_geography,
            keywords=tech.keywords,
            classification_status=tech.classification_status,
            classification_confidence=tech.classification_confidence,
            patent_status=tech.patent_status,
            patent_status_confidence=tech.patent_status_confidence,
            patent_status_source=tech.patent_status_source,
            scraped_at=tech.scraped_at,
            updated_at=tech.updated_at,
            first_seen=tech.first_seen,
            raw_data=tech.raw_data,
        )


@router.get("/technologies/by-id/{tech_id}", response_model=TechnologyDetail)
def get_technology_by_db_id(tech_id: int):
    """Get a single technology by its database ID."""
    with db.get_session() as session:
        tech = session.query(Technology).filter(Technology.id == tech_id).first()

        if not tech:
            raise HTTPException(status_code=404, detail="Technology not found")

        return TechnologyDetail(
            uuid=str(tech.uuid),
            university=tech.university,
            tech_id=tech.tech_id,
            title=tech.title,
            description=tech.description,
            url=tech.url,
            top_field=tech.top_field,
            subfield=tech.subfield,
            patent_geography=tech.patent_geography,
            keywords=tech.keywords,
            classification_status=tech.classification_status,
            classification_confidence=tech.classification_confidence,
            patent_status=tech.patent_status,
            patent_status_confidence=tech.patent_status_confidence,
            patent_status_source=tech.patent_status_source,
            scraped_at=tech.scraped_at,
            updated_at=tech.updated_at,
            first_seen=tech.first_seen,
            raw_data=tech.raw_data,
        )


@router.get("/taxonomy", response_model=list[TaxonomyField])
def get_taxonomy():
    """Get the field/subfield taxonomy for filter dropdowns."""
    return [
        TaxonomyField(
            name=field_name,
            subfields=[
                TaxonomySubfield(name=sf)
                for sf in definition.subfields
            ],
        )
        for field_name, definition in TAXONOMY.items()
    ]


class RawDataUpdate(BaseModel):
    updates: dict[str, object]


@router.patch("/technologies/{uuid}/raw-data", response_model=TechnologyDetail)
def patch_raw_data(uuid: UUID, body: RawDataUpdate):
    """Update specific fields in a technology's raw_data."""
    from ...database import QACorrection
    from sqlalchemy.orm import make_transient

    with db.get_session() as session:
        tech = session.query(Technology).filter(Technology.uuid == str(uuid)).first()
        if not tech:
            raise HTTPException(status_code=404, detail="Technology not found")

        # Record corrections BEFORE updating raw_data
        if body.updates:
            original_raw = dict(tech.raw_data or {})
            for field_name, corrected_value in body.updates.items():
                if corrected_value is None:
                    continue  # deletions aren't corrections
                existing = (
                    session.query(QACorrection)
                    .filter(QACorrection.technology_id == tech.id, QACorrection.field_name == field_name)
                    .first()
                )
                if existing:
                    existing.corrected_value = corrected_value
                    existing.corrected_at = datetime.now(timezone.utc)
                else:
                    session.add(QACorrection(
                        technology_id=tech.id,
                        field_name=field_name,
                        corrected_value=corrected_value,
                        original_scraped_value=original_raw.get(field_name),
                    ))

        # Update raw_data
        current_raw_data = dict(tech.raw_data or {})
        for key, value in body.updates.items():
            if value is None:
                current_raw_data.pop(key, None)
            else:
                current_raw_data[key] = value
        tech.raw_data = current_raw_data
        tech.updated_at = datetime.now(timezone.utc)

        session.flush()
        session.refresh(tech)
        _ = (tech.id, tech.uuid, tech.university, tech.tech_id, tech.title,
             tech.description, tech.url, tech.raw_data, tech.updated_at,
             tech.top_field, tech.subfield, tech.patent_geography, tech.keywords,
             tech.classification_status, tech.classification_confidence,
             tech.patent_status, tech.patent_status_confidence,
             tech.patent_status_source, tech.scraped_at, tech.first_seen)
        session.expunge(tech)
        make_transient(tech)

    return TechnologyDetail(
        uuid=str(tech.uuid),
        university=tech.university,
        tech_id=tech.tech_id,
        title=tech.title,
        description=tech.description,
        url=tech.url,
        top_field=tech.top_field,
        subfield=tech.subfield,
        patent_geography=tech.patent_geography,
        keywords=tech.keywords,
        classification_status=tech.classification_status,
        classification_confidence=tech.classification_confidence,
        patent_status=tech.patent_status,
        patent_status_confidence=tech.patent_status_confidence,
        patent_status_source=tech.patent_status_source,
        scraped_at=tech.scraped_at,
        updated_at=tech.updated_at,
        first_seen=tech.first_seen,
        raw_data=tech.raw_data,
    )


@router.get("/proxy")
async def proxy_page(url: str = Query(..., description="URL to proxy")):
    """Proxy an external page to bypass X-Frame-Options restrictions.

    Detects SPA pages and falls back to Playwright rendering.
    """
    if not _is_allowed_proxy_url(url):
        raise HTTPException(status_code=403, detail="URL not in allowed university domains")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=15),
                allow_redirects=True,
            ) as resp:
                html = await resp.text()

                # If the page looks like an SPA, render with Playwright
                if _is_spa_page(html):
                    try:
                        html = await render_with_playwright(url)
                    except Exception:
                        # Fall through with original HTML if Playwright fails
                        pass

                return HTMLResponse(content=html, status_code=resp.status)
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch: {e}")
