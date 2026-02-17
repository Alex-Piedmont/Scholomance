# PRD: Technology Opportunity Assessment

**Version:** 1.0
**Date:** 2026-02-16
**Author:** Product Management
**Status:** Draft
**Project:** Avvintura V2 -- Patent Analysis Platform

---

## 1. Introduction / Overview

The platform currently holds ~41 universities' worth of technology transfer listings, each with structured `raw_data` containing descriptions, applications, advantages, development stages, and other metadata. An LLM classifier already assigns field/subfield taxonomy labels to each record. However, the database has no mechanism for surfacing **hidden commercial potential** -- technologies that may be more valuable than their listings suggest.

This feature introduces an LLM-powered assessment pipeline that evaluates each technology record against three opportunity categories:

1. **TRL Gap** -- The technology is likely at a higher readiness level than the inventors claim or imply.
2. **False Barrier** -- The stated obstacles to commercialization are not genuine blockers for the target market.
3. **Alternative Application** -- The technology is well-suited to a problem domain the inventors have not identified.

The primary audience is **external investors and technology scouts** browsing the database for undervalued or overlooked technologies. Results are surfaced through a dedicated **Opportunities dashboard** with filtering, sorting, and per-category scoring.

---

## 2. Goals

- **Surface hidden value:** Identify technologies whose commercial potential exceeds what their listing text conveys, across all three opportunity categories.
- **Enable investor discovery:** Provide a ranked, filterable dashboard where scouts can find the most promising opportunities without reading thousands of listings.
- **Structured explainability:** Every assessment includes a 1-3 sentence rationale and confidence score per category so investors understand *why* a technology was flagged.
- **Cost-efficient batch processing:** Assess the full database (currently ~10k-20k records) at a per-record cost comparable to classification (~$0.001-0.005/record using Haiku).
- **Tiered coverage:** Assess data-rich records fully (all 3 categories), data-moderate records partially, and skip title-only records.

### What Success Looks Like

An investor opens the Opportunities dashboard, filters to "TRL Gap" opportunities in "MedTech" with confidence > 0.7, and sees a ranked list of technologies where the LLM identified evidence (published clinical results, field trial data, industry partnerships) that the inventor-stated readiness level underestimates the true state. Each result shows the assessed TRL tier, the inventor-implied tier, the gap rationale, and a link to the full technology detail page.

---

## 3. User Stories

### US-1: Browse Opportunities by Category

**As an** investor, **I want to** filter the opportunities dashboard by assessment category (TRL Gap, False Barrier, Alternative Application), **so that** I can focus on the type of opportunity I specialize in.

**Acceptance Criteria:**
- [ ] Dashboard shows all assessed technologies with at least one category score > 0
- [ ] User can filter by one or more of the three categories
- [ ] Results can be sorted by category score (descending) or composite score
- [ ] Each result row shows the technology title, university, field, and per-category scores

### US-2: Understand Why a Technology Was Flagged

**As an** investor, **I want to** see the rationale behind each category assessment, **so that** I can quickly evaluate whether the opportunity is real.

**Acceptance Criteria:**
- [ ] Each category assessment includes a 1-3 sentence reasoning field
- [ ] Each category assessment includes a confidence score (0.0-1.0)
- [ ] For TRL Gap: displays both the inventor-implied tier and the LLM-assessed tier
- [ ] Rationale references specific evidence from the technology's raw_data (e.g., "3 publications describe field deployment")

### US-3: Filter Opportunities by Existing Dimensions

**As an** investor, **I want to** combine opportunity filters with existing filters (university, field/subfield, patent status), **so that** I can narrow results to my area of interest.

**Acceptance Criteria:**
- [ ] All existing technology list filters (university, field, subfield, patent_status, date range) work on the opportunities dashboard
- [ ] A minimum confidence threshold slider filters out low-confidence assessments
- [ ] Text search works across technology title, description, and assessment rationale

### US-4: Run Batch Assessment

**As a** platform operator, **I want to** run assessments in batch via CLI, **so that** I can process the full database and re-assess after new scrapes.

**Acceptance Criteria:**
- [ ] CLI command: `python -m src.cli assess --batch <N>` processes N unassessed records
- [ ] CLI command: `python -m src.cli assess --university <code>` assesses all records for one university
- [ ] `--force` flag re-assesses previously assessed records
- [ ] Progress bar shows completion rate, running cost, and token usage
- [ ] Batch respects rate limits and uses concurrency control (same pattern as classifier)

### US-5: Re-assess a Single Technology On-Demand

**As an** investor, **I want to** trigger a re-assessment of a specific technology from the detail page, **so that** I can get fresh analysis after the record is updated or I want a second opinion.

**Acceptance Criteria:**
- [ ] Technology detail page shows current assessment results (if any) in a new section
- [ ] An "Assess" / "Re-assess" button triggers on-demand assessment via API
- [ ] Loading state shown during LLM processing (expected 2-5 seconds)
- [ ] Result updates in-place without page reload

### US-6: Handle Sparse Data Gracefully

**As a** platform operator, **I want** the system to skip or partially assess records with insufficient data, **so that** low-confidence noise does not pollute the opportunities dashboard.

**Acceptance Criteria:**
- [ ] Records with only title (no description, no raw_data fields) are skipped entirely
- [ ] Records with title + description but no structured raw_data fields receive a limited assessment (TRL Gap only, using qualitative signals from description text)
- [ ] Records with title + description + at least 2 structured fields (applications, advantages, key_points, development_stage, publications) receive full 3-category assessment
- [ ] Assessment tier (full / limited / skipped) is stored and visible in results

---

## 4. Functional Requirements

### 4.1 TRL Assessment Scale

The system uses a hybrid 3-tier + prototype sub-level scale:

| Tier | Sub-level | TRL Equivalent | Signals |
|------|-----------|----------------|---------|
| Concept | -- | 1-3 | Theory, simulation, initial lab work, no prototype mentioned |
| Prototype | Early | 4 | Lab-validated component, bench testing described |
| Prototype | Demonstrated | 5-6 | Tested in relevant or operational environment, pilot study results |
| Prototype | Advanced | 7 | Full system prototype demonstrated, field trial data |
| Market-ready | -- | 8-9 | Qualified system, production-ready, regulatory approval mentioned |

- **FR-1:** The LLM shall assign both an "inventor-implied TRL tier" (inferred from how the listing describes the technology's state) and an "assessed TRL tier" (inferred from evidence in the full record). A TRL Gap exists when the assessed tier is higher than the inventor-implied tier.

- **FR-2:** The LLM shall cite specific evidence from raw_data fields (publications, development_stage, applications, key_points) that justifies the assessed tier.

### 4.2 Assessment Categories

- **FR-3:** Each category assessment shall produce:

| Field | Type | Description |
|-------|------|-------------|
| `category` | enum | `trl_gap`, `false_barrier`, `alt_application` |
| `score` | float (0.0-1.0) | Strength of the opportunity signal |
| `confidence` | float (0.0-1.0) | How confident the LLM is given available data |
| `reasoning` | string | 1-3 sentence rationale with evidence citations |
| `details` | JSON | Category-specific structured data (see below) |

- **FR-4:** Category-specific `details` fields:

**TRL Gap:**
```json
{
  "inventor_implied_tier": "Prototype:Early",
  "assessed_tier": "Prototype:Advanced",
  "evidence_fields": ["publications", "key_points"],
  "key_evidence": "Three peer-reviewed publications describe successful in-vivo testing"
}
```

**False Barrier:**
```json
{
  "stated_barrier": "Requires rare earth materials, limiting scalability",
  "rebuttal": "Sensor unit cost at scale would be <$5, well within commodity pricing for IoT sensors",
  "barrier_source_field": "description",
  "market_context": "IoT sensor market accepts $2-10 unit costs at volume"
}
```

**Alternative Application:**
```json
{
  "original_application": "Aerial UAV navigation in GPS-denied environments",
  "suggested_application": "Underground infrastructure inspection and mapping",
  "reasoning": "Core SLAM algorithm works identically in any GPS-denied environment; infrastructure inspection is a $4B market with fewer regulatory barriers than commercial UAV flight",
  "market_signal": "infrastructure monitoring"
}
```

### 4.3 Composite Score

- **FR-5:** A composite opportunity score shall be calculated as the equally-weighted average of the three category scores: `composite = (trl_gap_score + false_barrier_score + alt_application_score) / 3`. For limited assessments (where only TRL Gap is evaluated), the composite equals the single score.

### 4.4 Data Tiering

- **FR-6:** Before sending a record to the LLM, the system shall evaluate data richness:

| Tier | Criteria | Assessment Scope |
|------|----------|-----------------|
| Full | title + description + 2 or more of: applications, advantages, key_points, development_stage, publications, market_opportunity | All 3 categories |
| Limited | title + description, but fewer than 2 structured fields | TRL Gap only |
| Skipped | title only (no description or empty description) | No assessment |

### 4.5 Database Schema

- **FR-7:** New `technology_assessments` table:

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `id` | SERIAL | PK | auto | |
| `technology_id` | INTEGER | FK | -- | References `technologies(id)` ON DELETE CASCADE |
| `assessed_at` | TIMESTAMPTZ | Yes | CURRENT_TIMESTAMP | |
| `model` | VARCHAR(100) | Yes | -- | LLM model used |
| `assessment_tier` | VARCHAR(20) | Yes | -- | `full`, `limited`, `skipped` |
| `composite_score` | DECIMAL(3,2) | No | -- | Weighted average of category scores |
| `trl_gap_score` | DECIMAL(3,2) | No | -- | |
| `trl_gap_confidence` | DECIMAL(3,2) | No | -- | |
| `trl_gap_reasoning` | TEXT | No | -- | |
| `trl_gap_details` | JSONB | No | -- | Structured TRL Gap data |
| `false_barrier_score` | DECIMAL(3,2) | No | -- | |
| `false_barrier_confidence` | DECIMAL(3,2) | No | -- | |
| `false_barrier_reasoning` | TEXT | No | -- | |
| `false_barrier_details` | JSONB | No | -- | Structured False Barrier data |
| `alt_application_score` | DECIMAL(3,2) | No | -- | |
| `alt_application_confidence` | DECIMAL(3,2) | No | -- | |
| `alt_application_reasoning` | TEXT | No | -- | |
| `alt_application_details` | JSONB | No | -- | Structured Alt Application data |
| `prompt_tokens` | INTEGER | No | -- | |
| `completion_tokens` | INTEGER | No | -- | |
| `total_cost` | DECIMAL(10,6) | No | -- | |
| `raw_response` | JSONB | No | -- | Full LLM response for debugging |

- **FR-8:** New columns on `technologies` table for fast filtering:

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `assessment_status` | VARCHAR(50) | `pending` | `pending`, `in_progress`, `completed`, `failed` |
| `composite_opportunity_score` | DECIMAL(3,2) | NULL | Denormalized from latest assessment |
| `last_assessed_at` | TIMESTAMPTZ | NULL | |

### 4.6 API Endpoints

- **FR-9:** New endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/opportunities` | Paginated list of assessed technologies, sorted by score |
| `GET` | `/api/opportunities/{uuid}` | Full assessment detail for one technology |
| `POST` | `/api/opportunities/{uuid}/assess` | Trigger on-demand assessment for one technology |
| `GET` | `/api/opportunities/stats` | Aggregate stats: count by category, score distributions |

**GET `/api/opportunities`** query parameters:

| Param | Type | Description |
|-------|------|-------------|
| `page`, `limit` | int | Pagination |
| `q` | string | Text search across title, description, reasoning |
| `category` | enum | Filter: `trl_gap`, `false_barrier`, `alt_application` |
| `min_score` | float | Minimum category score (applied to selected category, or composite if no category) |
| `min_confidence` | float | Minimum confidence for the selected category |
| `top_field` | string | Existing field filter |
| `subfield` | string | Existing subfield filter |
| `university` | string[] | Existing university filter |
| `patent_status` | string | Existing patent status filter |
| `assessment_tier` | enum | `full`, `limited` |
| `sort` | enum | `composite`, `trl_gap`, `false_barrier`, `alt_application` (default: `composite`) |

**POST `/api/opportunities/{uuid}/assess`** response:
```json
{
  "uuid": "...",
  "assessment_tier": "full",
  "composite_score": 0.72,
  "categories": {
    "trl_gap": {
      "score": 0.85,
      "confidence": 0.78,
      "reasoning": "Three publications describe in-vivo trials, but listing states 'early-stage research'. Evidence suggests Prototype:Advanced, not Concept.",
      "details": { ... }
    },
    "false_barrier": { ... },
    "alt_application": { ... }
  }
}
```

### 4.7 LLM Prompt Design

- **FR-10:** The assessment prompt shall include:
  1. The hybrid TRL scale definition (Section 4.1)
  2. Explicit instructions for each of the three categories with examples
  3. The technology's title, description, and all non-empty raw_data fields (serialized)
  4. Instructions to return structured JSON matching the schema in FR-3/FR-4
  5. Instructions to cite which raw_data fields informed each judgment

- **FR-11:** The system shall use `claude-3-5-haiku-20241022` by default (matching existing classifier cost profile), with a `--model` CLI flag to override.

- **FR-12:** Max tokens for the assessment response shall be 1024 (higher than classification's 256 due to structured reasoning across 3 categories).

### 4.8 CLI Commands

- **FR-13:** New CLI commands following existing patterns in `src/cli.py` (1,029 lines):

```
python -m src.cli assess --batch 100           # Assess next 100 unassessed records
python -m src.cli assess --university stanford  # Assess all records for a university
python -m src.cli assess --uuid <uuid>          # Assess a single record
python -m src.cli assess --force                # Re-assess already assessed records
python -m src.cli assess --model claude-3-5-sonnet-20241022  # Override model
python -m src.cli assess --dry-run              # Show what would be assessed, with data tier breakdown
```

---

## 5. Non-Goals (Out of Scope)

- **Cross-referencing other records:** The assessment uses only the individual technology's data + LLM general knowledge. No similarity search or cross-database analysis.
- **External market data:** No web search, market research API integration, or RAG pipeline. LLM general knowledge only.
- **Automated re-assessment triggers:** No webhook or event-driven re-assessment when a record is updated. Re-assessment is manual (CLI or on-demand button).
- **User accounts or saved searches:** The opportunities dashboard is public, same as the existing technology list. No authentication.
- **Assessment editing or overrides:** Investors cannot manually adjust scores or mark assessments as incorrect. This is a future feedback loop feature.
- **Email/notification alerts:** No alerts when high-scoring opportunities are found.
- **Multi-language support:** Assessment prompts and UI are English-only.
- **Historical assessment comparison:** Only the latest assessment is displayed. Previous assessments are retained in the `technology_assessments` table but not surfaced in the UI.
- **Assessment of technologies without classification:** Records must have `classification_status = 'completed'` before assessment. Assessment depends on the field/subfield context.

---

## 6. Design Considerations

### User Interface

**Opportunities Dashboard (new page: `/opportunities`)**

```
+------------------------------------------------------------------+
| Opportunities                                          [Stats]    |
|------------------------------------------------------------------|
| [Search...                    ]  [Category v] [Min Score: 0.5 v] |
| [University v] [Field v] [Subfield v] [Patent v] [Tier v]       |
|------------------------------------------------------------------|
| Sort: [Composite v]                              Showing 1-20/847 |
|------------------------------------------------------------------|
| Score | Title                    | University | Field   | TRL | FB | AA |
|-------|--------------------------|------------|---------|-----|----|----|
| 0.82  | Graphene Biosensor...    | stanford   | MedTech | 0.9 |0.7 |0.8 |
| 0.78  | SLAM Navigation Sys...   | gatech     | Robot.. | 0.8 |0.6 |0.9 |
| 0.71  | Polymer Membrane...      | mit        | Mater.. | 0.8 |0.7 |0.6 |
|       |                          |            |         |     |    |    |
+------------------------------------------------------------------+
```

Column abbreviations: TRL = TRL Gap score, FB = False Barrier score, AA = Alt Application score.

**Clicking a row** navigates to the technology detail page, which now includes an Assessment section.

**Assessment Section on Detail Page:**

```
+------------------------------------------------------------------+
| Opportunity Assessment                    [Re-assess]  Full Tier  |
|------------------------------------------------------------------|
| Composite Score: 0.82                  Assessed: Feb 14, 2026     |
|------------------------------------------------------------------|
| TRL Gap                                        Score: 0.90       |
| Confidence: 0.78                                                  |
| Inventor implies: Concept                                         |
| Assessed at: Prototype:Advanced                                   |
| "Three peer-reviewed publications describe successful in-vivo     |
|  testing in murine models. Development stage listed as 'early     |
|  research' understates demonstrated readiness."                   |
|------------------------------------------------------------------|
| False Barrier                                   Score: 0.72       |
| Confidence: 0.65                                                  |
| Barrier: "Requires specialized manufacturing equipment"           |
| "Standard MEMS fabrication processes can produce this sensor at   |
|  commodity scale. Barrier applies to custom one-off builds, not   |
|  commercial production runs."                                     |
|------------------------------------------------------------------|
| Alternative Application                         Score: 0.85       |
| Confidence: 0.71                                                  |
| Original: Wearable glucose monitoring                             |
| Suggested: Environmental contaminant detection                    |
| "Core electrochemical sensing mechanism is analyte-agnostic.      |
|  Environmental water testing is a $3.2B market with less          |
|  regulatory burden than clinical diagnostics."                    |
+------------------------------------------------------------------+
```

### User Experience

**Journey 1: Investor Discovers Opportunities**
1. Investor navigates to `/opportunities`
2. Filters by category "Alternative Application" and field "Robotics"
3. Sorts by Alt Application score descending
4. Scans titles and scores; clicks a promising result
5. Reads the full assessment rationale on the detail page
6. Clicks source URL to view the original university listing

**Journey 2: Operator Runs Batch Assessment**
1. After a scrape run, operator runs `python -m src.cli assess --dry-run`
2. Reviews count of new unassessed records and tier breakdown
3. Runs `python -m src.cli assess --batch 500`
4. Monitors progress bar showing cost and completion
5. Checks dashboard for new high-scoring results

**Loading States:**
- On-demand assessment: spinner on the "Assess" button, assessment section shows skeleton placeholder
- Dashboard: standard pagination loading (same as existing technology list)

**Error States:**
- LLM API failure during on-demand assessment: toast notification "Assessment failed. Try again later."
- Partially completed batch: progress saved; next run resumes from where it stopped

---

## 7. Technical Considerations

### Architecture

The assessment system mirrors the existing classification pipeline (`src/classifier.py`, 354 lines). A new `Assessor` class handles prompt construction, LLM interaction, response parsing, and validation. The CLI integrates it the same way `classify` integrates `Classifier`.

**New backend files:**
- `src/assessor.py` -- Core assessment logic (prompt, LLM call, parse, validate)
- `src/api/routes/opportunities.py` -- API endpoints for opportunities dashboard

**Modified backend files:**
- `schema.sql` (209 lines) -- Add `technology_assessments` table + columns on `technologies`
- `src/database.py` (751 lines) -- Add ORM model for assessments, query methods
- `src/cli.py` (1,029 lines) -- Add `assess` command group
- `src/api/main.py` (87 lines) -- Register opportunities router
- `src/api/schemas.py` (104 lines) -- Add assessment response schemas

**New frontend files:**
- `web/src/pages/OpportunitiesPage.tsx` -- Dashboard page
- `web/src/components/Opportunities/OpportunityRow.tsx` -- Table row component
- `web/src/components/Opportunities/OpportunityFilters.tsx` -- Filter bar
- `web/src/components/Detail/AssessmentSection.tsx` -- Assessment section for detail page

**Modified frontend files:**
- `web/src/api/types.ts` (103 lines) -- Add assessment types
- `web/src/App.tsx` -- Add `/opportunities` route
- `web/src/components/Detail/ContentSections.tsx` (186 lines) -- Integrate AssessmentSection
- Navigation component -- Add "Opportunities" nav link

### Data

**New table DDL:**

```sql
CREATE TABLE IF NOT EXISTS technology_assessments (
    id SERIAL PRIMARY KEY,
    technology_id INTEGER NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    model VARCHAR(100) NOT NULL,
    assessment_tier VARCHAR(20) NOT NULL,  -- 'full', 'limited'

    composite_score DECIMAL(3,2),

    trl_gap_score DECIMAL(3,2),
    trl_gap_confidence DECIMAL(3,2),
    trl_gap_reasoning TEXT,
    trl_gap_details JSONB,

    false_barrier_score DECIMAL(3,2),
    false_barrier_confidence DECIMAL(3,2),
    false_barrier_reasoning TEXT,
    false_barrier_details JSONB,

    alt_application_score DECIMAL(3,2),
    alt_application_confidence DECIMAL(3,2),
    alt_application_reasoning TEXT,
    alt_application_details JSONB,

    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_cost DECIMAL(10,6),
    raw_response JSONB
);

CREATE INDEX idx_assessments_technology_id ON technology_assessments(technology_id);
CREATE INDEX idx_assessments_composite_score ON technology_assessments(composite_score DESC NULLS LAST);
CREATE INDEX idx_assessments_assessed_at ON technology_assessments(assessed_at);
```

**ALTER for technologies table:**

```sql
ALTER TABLE technologies
    ADD COLUMN assessment_status VARCHAR(50) DEFAULT 'pending',
    ADD COLUMN composite_opportunity_score DECIMAL(3,2),
    ADD COLUMN last_assessed_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX idx_technologies_assessment_status ON technologies(assessment_status);
CREATE INDEX idx_technologies_composite_score ON technologies(composite_opportunity_score DESC NULLS LAST);
```

### APIs

See FR-9 for full endpoint specifications.

**Example: GET `/api/opportunities?category=trl_gap&min_score=0.7&top_field=MedTech&sort=trl_gap&limit=20`**

Response:
```json
{
  "items": [
    {
      "uuid": "abc-123",
      "title": "Graphene-based Biosensor for Rapid Pathogen Detection",
      "university": "stanford",
      "top_field": "MedTech",
      "subfield": "Diagnostics",
      "patent_status": "pending",
      "composite_score": 0.82,
      "assessment_tier": "full",
      "trl_gap": { "score": 0.90, "confidence": 0.78, "reasoning": "..." },
      "false_barrier": { "score": 0.72, "confidence": 0.65, "reasoning": "..." },
      "alt_application": { "score": 0.85, "confidence": 0.71, "reasoning": "..." },
      "assessed_at": "2026-02-14T10:30:00Z"
    }
  ],
  "total": 847,
  "page": 1,
  "pages": 43,
  "limit": 20
}
```

### Performance

- Batch assessment: 3 concurrent LLM calls (matching classifier pattern), ~100ms rate limit between requests
- On-demand assessment: single synchronous call, expected p95 latency under 5 seconds
- Dashboard queries: composite_score index enables fast sorted pagination; target p95 under 200ms
- Estimated batch cost: ~$0.003-0.008 per record with Haiku (1024 max output tokens vs 256 for classification)

---

## 8. Security and Privacy

### Authentication & Authorization

No authentication required (matches existing platform). The on-demand `/assess` endpoint is rate-limited to prevent abuse (10 requests/minute per IP).

### Input Validation

- UUID path parameters validated as UUID format
- Query parameters validated via FastAPI/Pydantic (same pattern as existing endpoints)
- No user-supplied text is sent to the LLM; only database-sourced content

### Sensitive Data

- LLM API key: sourced from environment variable `ANTHROPIC_API_KEY` (existing pattern)
- Raw LLM responses stored in `raw_response` JSONB for debugging; no PII involved
- Assessment costs tracked per-record for budget monitoring

---

## 9. Testing Strategy

### Unit Tests

**Backend (pytest):**
- `test_assessor.py`: Prompt construction with varying data richness levels
- `test_assessor.py`: Response parsing (valid JSON, malformed JSON, markdown-wrapped JSON)
- `test_assessor.py`: Data tier classification (full, limited, skipped) across representative raw_data shapes
- `test_assessor.py`: TRL tier validation (valid tiers accepted, invalid tiers rejected)
- `test_assessor.py`: Composite score calculation (3-category average, single-category fallback)
- `test_assessor.py`: Cost calculation matches expected pricing

**Frontend (vitest):**
- OpportunityFilters: filter state management, URL param sync
- OpportunityRow: renders all three category scores, handles null categories for limited assessments
- AssessmentSection: displays structured reasoning, handles loading/error states

### Integration Tests

- Full assess-and-query cycle: insert a technology, run assessment, query via opportunities API, verify scores match
- On-demand assessment endpoint: POST triggers LLM call, stores result, returns structured response
- Batch CLI: mock LLM client, verify correct records are selected and results stored

### Edge Cases

- Technology with empty raw_data (`{}`) but a description -- should tier as "limited"
- Technology with raw_data containing only `inventors` and `contacts` (metadata only, no technical content) -- should tier as "limited"
- LLM returns scores outside 0.0-1.0 range -- clamp to valid range
- LLM returns TRL tier not in the defined scale -- fall back to qualitative assessment
- Re-assessment of already-assessed technology -- new row in `technology_assessments`, update denormalized fields on `technologies`
- Batch interrupted mid-run -- already-assessed records marked `completed`, remaining stay `pending`

---

## 10. Dependencies and Assumptions

### Dependencies

**New libraries to install:**
- None. The feature uses the existing `anthropic` SDK, `FastAPI`, `SQLAlchemy`, and `Pydantic` stack.

**Existing dependencies (no changes):**
- `anthropic` -- Claude API client (already used by classifier)
- `fastapi`, `sqlalchemy`, `pydantic` -- API framework
- `loguru` -- Logging
- `click` / `rich` -- CLI (progress bars, tables)

### Assumptions

- The existing classification pipeline has already been run on target records (`classification_status = 'completed'`). Assessment depends on field/subfield context for prompt construction.
- The Anthropic API key has sufficient quota for batch assessment runs.
- The `raw_data` JSONB fields across all 41 scrapers contain enough varied content to make the assessment meaningful. Scrapers that produce only title + URL will yield mostly "skipped" records.
- Claude 3.5 Haiku can reliably produce structured JSON assessments matching the defined schema with adequate reasoning quality.

### Known Constraints

- LLM assessments are non-deterministic. Running the same record twice may produce different scores. The latest assessment wins.
- Assessment quality degrades with sparse data. The tiering system mitigates this but does not eliminate it.
- No ground truth exists for validating assessment accuracy. Initial quality will be evaluated manually by reviewing a sample of high-scoring results.

---

## 11. Success Metrics

### Quantitative Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Records assessed (full tier) | > 60% of total database | `SELECT COUNT(*) WHERE assessment_tier = 'full'` / total |
| Records assessed (any tier) | > 80% of total database | `SELECT COUNT(*) WHERE assessment_status = 'completed'` / total |
| Assessment cost per record | < $0.008 (Haiku) | `AVG(total_cost)` from `technology_assessments` |
| Batch throughput | > 200 records/minute | Measured during batch run |
| On-demand assessment latency | p95 < 5 seconds | API response time logging |
| Dashboard page load | p95 < 500ms | Frontend performance measurement |

### Qualitative Metrics

| Metric | How to Assess |
|--------|---------------|
| Assessment reasoning quality | Manual review of 50 random high-scoring assessments across all 3 categories |
| False positive rate | Review 20 top-scoring records per category; estimate what fraction are genuinely interesting opportunities |
| TRL tier accuracy | Compare LLM-assigned tiers against human judgment for 30 records with known development stages |

---

## 12. Implementation Order

| Phase | Scope | Risk Level | Verification |
|-------|-------|------------|--------------|
| **Phase 1** | Database schema (new table, alter technologies), ORM model, data tier logic | Low | Migration runs cleanly, tier function classifies 5 sample records correctly |
| **Phase 2** | `src/assessor.py`: prompt construction, LLM call, response parsing, validation | Medium | Unit tests pass; manually assess 5 records and review JSON output quality |
| **Phase 3** | CLI `assess` command: batch, single, dry-run, force | Low | Batch 10 records via CLI, verify DB storage and progress output |
| **Phase 4** | API endpoints: `/api/opportunities` (list + detail + stats) | Low | curl/httpie queries return correctly filtered, sorted, paginated results |
| **Phase 5** | Frontend: Opportunities dashboard page with filters and sorting | Medium | Visual QA at localhost:5173; filters, sort, pagination all work |
| **Phase 6** | Frontend: Assessment section on detail page + on-demand assess button | Medium | Click "Assess" on a record, see result appear in-place |
| **Phase 7** | Batch run on full database, quality review, score calibration | High | Manual review of 50 top results; adjust prompt if reasoning quality is poor |

---

## Clarifying Questions

**Q1: [OPTIONAL] Should the composite score on the dashboard be filterable independently of category scores?** For example, an investor might want "composite > 0.6" regardless of which categories contribute. The current design supports this via `min_score` without a `category` filter, but confirm this is the intended behavior. ANSWER: Yes

**Q2: [OPTIONAL] Should the "Alternative Application" category suggest a single alternative or up to N alternatives?** The current design produces one suggested application per assessment. Multiple suggestions would increase output tokens and cost but could surface more opportunities. ANSWER: provide up to 3 but do not excessively speculate to fill these out. Only provide suggestions if a reasonable third party would agree it is plausible. 

**Q3: [OPTIONAL] Should assessment results influence the existing technology list page at all?** For example, adding a small "opportunity" badge or score column to the main `/technologies` list view. The current design keeps them fully separate. ANSWER: Add it

**Q4: [OPTIONAL] For the False Barrier category, should the system attempt to identify barriers only from explicit text (e.g., "challenges include...") or also infer unstated barriers from the technology description?** Explicit-only is more reliable; inferred barriers are more comprehensive but risk false positives. ANSWER: most technologies will not list blockers explicitly

**Q5: [OPTIONAL] What is the expected re-assessment cadence?** If records are rarely updated, a one-time batch may suffice. If scrapers run weekly and content changes, periodic re-assessment may be needed. This affects whether to add a `--stale-after <days>` flag to the CLI. ANSWER: records are almost never updated, so once a technology is assessed it's likely to remain that way. 
