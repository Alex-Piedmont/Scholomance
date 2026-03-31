# PRD: QA Review Tool for Scraper Data Validation

**Version:** 1.0
**Date:** 2026-03-18
**Author:** Product Management
**Status:** Draft
**Project:** Scholomance -- University Tech Transfer Platform

---

## 1. Introduction / Overview

Scraper QA is the bottleneck in the data pipeline. After a scraper runs, each technology's extracted data must be verified against its source page to confirm correct parsing -- fields present, content accurate, no HTML leakage, no metadata bleed, no truncation. Today this requires manually visiting source pages, comparing fields by eye, copying corrections into a conversation, and iterating. A single university can take 30+ minutes of human review time.

The QA Review Tool provides a browser-based side-by-side comparison view: scraped fields on the left, the rendered source page on the right. The reviewer marks fields correct or incorrect, edits values inline, and saves corrections directly to the database. Per-university approval tracking lets the reviewer focus on unapproved scrapers, and a conflict-flagging system ensures corrections are never silently overwritten by subsequent re-scrapes.

There are 35 universities in the scraper registry. One (buffalo) has been fully approved. The remaining 34 require QA review. Source pages vary from static HTML to JavaScript SPAs (Flintbox), requiring server-side rendering for iframe embedding.

---

## 2. Goals

- **QA throughput:** Reduce per-university review time from 30+ minutes to under 10 minutes for a 10-document sample.
- **Data safety:** Zero silent overwrites of human corrections. Re-scrapes that conflict with corrections shall be flagged for review.
- **Completion tracking:** Clear visibility into which universities have been approved and which remain.
- **Source fidelity:** Source pages render correctly in the review iframe, including JavaScript SPAs (Flintbox).

### What Success Looks Like

The reviewer opens `/qa`, sees a list of unapproved universities, picks one, and is presented with 10 representative technologies. For each, the left panel shows scraped fields and the right panel shows the live source page. The reviewer scans each field, marks it correct or incorrect, edits incorrect values, and saves. After reviewing the sample, the reviewer approves the university. On next visit, that university is hidden by default. If a scraper is later fixed and re-run, any field that was manually corrected but now differs from the new scrape is flagged as a conflict rather than silently overwritten.

---

## 3. User Stories

### US-1: Side-by-side review

**As a** QA reviewer, **I want to** see scraped data alongside the rendered source page, **so that** I can visually verify extraction accuracy without switching between browser tabs.

**Acceptance Criteria:**
- [ ] Left panel (40% width) displays all `raw_data` fields with values
- [ ] Right panel (60% width) displays the source page in an iframe
- [ ] Source page renders correctly for static HTML sites
- [ ] Source page renders correctly for Flintbox SPAs (JavaScript-rendered via Playwright)
- [ ] Fallback "Open in new tab" link shown if rendering fails
- [ ] Source URL displayed above the iframe

### US-2: Inline correction

**As a** QA reviewer, **I want to** mark fields as correct/incorrect and edit incorrect values inline, **so that** I can fix data without leaving the review interface.

**Acceptance Criteria:**
- [ ] Each field has OK/Fix toggle buttons
- [ ] Clicking Fix expands an editable textarea pre-filled with current value
- [ ] Array fields display as bullet lists; "Toggle bullets" button adds/removes `- ` prefixes
- [ ] Save button appears when 1+ fields marked incorrect
- [ ] Save persists corrections to `raw_data` via PATCH API
- [ ] After save, corrected fields flip to "correct" status

### US-3: 10-document sample loading

**As a** QA reviewer, **I want** exactly 10 technologies loaded per university for review, **so that** I get a representative sample without triggering full scrapes.

**Acceptance Criteria:**
- [ ] Sample loading makes at most 10 detail-page API calls per university (plus 1 list call for Flintbox)
- [ ] Sample is selected from existing database records
- [ ] Sample is deterministic (same 10 each time for a given university, until re-seeded)
- [ ] A "Refresh sample" action re-scrapes the same 10 technologies' detail pages and updates the DB
- [ ] Loading progress is shown during sample refresh

### US-4: University approval tracking

**As a** QA reviewer, **I want to** mark a university as approved and filter the list to show only unapproved universities, **so that** I can focus on remaining work.

**Acceptance Criteria:**
- [ ] University list shows approval status (approved/unapproved) per university
- [ ] "Approve" button always available (no minimum review gate)
- [ ] "Unapproved only" toggle (default ON) filters the university list
- [ ] Approval status persists in the database
- [ ] Approval can be revoked
- [ ] `tasks/completed_scrapers.md` is the initial source; on first `/qa` page load, if `university_qa_status` table is empty, seed it from the file

### US-5: Correction persistence and conflict detection

**As a** QA reviewer, **I want** my corrections to never be silently overwritten by re-scrapes, **so that** I don't have to redo manual work.

**Acceptance Criteria:**
- [ ] When a correction is saved, the field name and corrected value are recorded in a `qa_corrections` ledger
- [ ] On re-scrape (bulk_insert_technologies), if a corrected field's new scraped value differs from the correction, the conflict is flagged
- [ ] Conflicted technologies appear in a "Conflicts" section of the QA page
- [ ] Reviewer can resolve conflicts by accepting the new scrape or keeping the correction
- [ ] Fields with no conflict are updated normally by re-scrapes

### US-6: Navigation between technologies

**As a** QA reviewer, **I want** prev/next navigation within the sample set, **so that** I can review all 10 without returning to the list.

**Acceptance Criteria:**
- [ ] Prev/Next buttons navigate between the 10-document sample
- [ ] Current position shown (e.g., "3/10")
- [ ] Navigation preserves field review state for already-reviewed technologies
- [ ] Browser confirm dialog warns if navigating away with unsaved corrections

---

## 4. Functional Requirements

### Source Page Rendering

- **FR-1:** Static HTML source pages shall be proxied via `GET /api/proxy?url=<encoded_url>` and served in an iframe with `sandbox="allow-same-origin"`.

- **FR-2:** JavaScript SPA pages (Flintbox and similar) shall be rendered server-side using Playwright. The proxy endpoint shall first fetch the page with aiohttp; if the response body contains SPA indicators (e.g., "You need to enable JavaScript", empty `<div id="root">`, or body under 500 chars), it shall fall back to Playwright rendering. This response-inspection approach adapts to new SPA sites without maintaining a hardcoded list.

- **FR-3:** Playwright rendering shall run in a thread pool (`asyncio.to_thread()`) with a semaphore limiting to 1 concurrent browser instance. Rendering shall have a 15-second timeout. On timeout or error, the iframe shall display an "Open in new tab" fallback link.

- **FR-4:** Rendered pages shall be cached in-memory (dict keyed by URL, TTL 30 minutes). Cache is lost on server restart, which is acceptable since source pages are always re-fetchable.

### Sample Management

- **FR-5:** Each university shall have a fixed QA sample of up to 10 technology IDs stored in the `qa_samples` table. The sample is created via explicit POST and persists until refreshed. Universities with fewer than 10 technologies get a partial sample (UI shows count). Sample creation is a separate POST, not auto-created on GET.

- **FR-6:** "Refresh sample" shall:
  1. Select 10 technology IDs from the DB for the university (first 10 by `id` for determinism)
  2. For each, call the scraper's `scrape_technology_detail()` method (exactly 10 API calls)
  3. Merge detail data into existing `raw_data`, apply cleaning pipeline
  4. Update the DB records
  5. NOT overwrite fields that have QA corrections (per FR-10)

### Approval Tracking

- **FR-7:** University approval status shall be stored in a new `university_qa_status` table (see Section 7 Data for schema).

- **FR-8:** API endpoints for approval:
  - `PUT /api/qa/universities/{code}/approve` -- Set status to `approved`
  - `PUT /api/qa/universities/{code}/unapprove` -- Revert to `pending`
  - `GET /api/qa/universities` -- List all with approval status and tech counts

### Correction Persistence and Conflict Detection

- **FR-9:** QA corrections shall be recorded in a new `qa_corrections` table (see Section 7 Data for schema). Unique constraint on `(technology_id, field_name)` -- latest correction wins via upsert.

- **FR-10:** `bulk_insert_technologies()` shall, before updating `raw_data`:
  1. Query `qa_corrections` for the technology
  2. For each corrected field, compare the new scraped value to the corrected value
  3. If they match: no conflict, allow the update
  4. If they differ: flag as conflict (add to `qa_conflicts` table), keep the corrected value in `raw_data`

- **FR-11:** Conflict resolution shall be available in the QA review page. Conflicted fields show both the correction and the new scraped value, with "Keep correction" / "Accept new" buttons. "Accept new" deletes the correction record (the field is no longer protected from future re-scrapes). "Keep correction" re-applies the correction to `raw_data` and deletes the conflict record.

- **FR-12:** Conflict comparison shall use strict JSON equality. Any difference between the corrected value and new scraped value constitutes a conflict. No whitespace normalization or array reordering.

- **FR-13:** If a third re-scrape runs before a conflict is resolved, the `new_scraped_value` in the existing conflict row shall be updated (upsert on unique constraint). Only one active conflict per field at a time.

- **FR-14:** Tables shall be created via SQLAlchemy `Base.metadata.create_all()`, matching the existing pattern in `db.init_db()`. No separate migration tool.

---

## 5. Non-Goals (Out of Scope)

- **Automated QA checks:** No automated detection of HTML leakage, truncation, or metadata bleed. The tool is human-review only.
- **Scraper code fixes:** Fixing individual scraper parsing bugs is tracked separately in `tasks/scraper_fixes_roadmap.md`.
- **Multi-user support:** No authentication, no reviewer attribution, no concurrent review handling.
- **Full re-scrape triggering:** The tool does not trigger full university scrapes. Only 10-document sample refreshes.
- **Frontend rendering of raw_data:** The QA tool shows raw field values, not the formatted display from `parseRawData.ts`.
- **Bulk operations:** No "approve all" or "mark all correct" across multiple technologies.
- **Mobile/responsive layout:** The side-by-side layout assumes desktop-width screens (1280px+).
- **History/audit trail:** Beyond the corrections ledger, no version history of field changes.

---

## 6. Design Considerations

### User Interface

```
+-------------------------------------------------------------------+
| QA Review                                                         |
+-------------------------------------------------------------------+
| [University Dropdown v] [Unapproved only: ON] [Refresh Sample]    |
+-------------------------------------------------------------------+
| Tech list (10 items)                                              |
| > Title 1                                    tech_id    status    |
| > Title 2                                    tech_id    status    |
| ...                                                               |
+-------------------------------------------------------------------+
```

```
+-------------------------------------------------------------------+
| QA Review > stanford / S-12345                    [3/10] [< >]    |
+-------------------------------------------------------------------+
| Scraped Fields (40%)      | Source Page (60%)                     |
|                           |                                       |
| [abstract]         [OK|Fix]  |  +-----------------------------+  |
| Content here...           |  | (rendered source page)        |  |
|                           |  |                               |  |
| [advantages]       [OK|Fix]  |  |                               |  |
| - Item 1                  |  |                               |  |
| - Item 2                  |  |                               |  |
|                           |  +-----------------------------+  |
| [Save 2 Corrections]     |  [Open in tab]                    |
+-------------------------------------------------------------------+
```

### User Experience

**Journey 1: First-time QA for a university**
1. Open `/qa`. See list of 34 unapproved universities.
2. Select "stanford". System checks for existing QA sample.
3. No sample exists -- system prompts "Load 10 sample technologies?"
4. User confirms. System fetches 10 detail pages (progress shown). Sample stored.
5. Tech list shows 10 technologies. Click first one.
6. Side-by-side view loads. Source page renders in iframe.
7. Review each field. Mark correct or fix incorrect ones. Save.
8. Click "Next" to move to technology 2/10. Repeat.
9. After reviewing all 10, return to list. Click "Approve University".
10. Stanford moves to approved status.

**Journey 2: Post-scraper-fix re-verification**
1. Scraper code for stanford is fixed. Full re-scrape runs.
2. Open `/qa`. Stanford shows "2 conflicts" badge.
3. Click stanford. Conflicts section shows 2 technologies with differing fields.
4. For each conflict: see corrected value vs new scraped value side by side.
5. Accept new value (scraper fix worked) or keep correction (scraper still wrong).
6. Conflicts resolved. Note: conflicts do NOT auto-revoke approval. Conflict badges appear but the reviewer decides if re-review is warranted.

**Loading States:**
- Sample refresh: spinner with "Fetching detail pages... (3/10)"
- Source page rendering: skeleton placeholder in iframe until loaded
- Save: button shows "Saving..." with disabled state

**Error States:**
- Source page render failure: "Could not render page. Open in new tab" with link
- API failure: toast notification with retry button
- Sample refresh failure: error message with individual technology failures listed

---

## 7. Technical Considerations

### Architecture

**New backend files:**
- `src/api/routes/qa.py` -- QA-specific API routes (approval, sample management, conflicts)

**Modified backend files:**
- `src/api/routes/technologies.py` (213 lines) -- Add Playwright rendering to proxy endpoint
- `src/api/main.py` (101 lines) -- Register qa_router
- `src/database.py` (975 lines) -- Add QA models, correction/conflict logic, modify bulk_insert

**Modified frontend files:**
- `web/src/pages/QAPage.tsx` (199 lines) -- Add approval UI, sample management, conflict badges, unapproved filter
- `web/src/pages/QAReviewPage.tsx` (419 lines) -- Add conflict resolution UI
- `web/src/api/client.ts` (131 lines) -- Add QA API methods
- `web/src/api/types.ts` (159 lines) -- Add QA types

### Data

New tables:

```sql
CREATE TABLE university_qa_status (
    id SERIAL PRIMARY KEY,
    university VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending' or 'approved'
    approved_at TIMESTAMP WITH TIME ZONE,
    notes TEXT
);

CREATE TABLE qa_samples (
    id SERIAL PRIMARY KEY,
    university VARCHAR(100) NOT NULL,
    technology_id INTEGER NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(university, technology_id)
);

CREATE TABLE qa_corrections (
    id SERIAL PRIMARY KEY,
    technology_id INTEGER NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    corrected_value JSONB NOT NULL,
    original_scraped_value JSONB,
    corrected_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(technology_id, field_name)
);

CREATE TABLE qa_conflicts (
    id SERIAL PRIMARY KEY,
    technology_id INTEGER NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    corrected_value JSONB NOT NULL,
    new_scraped_value JSONB NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(technology_id, field_name)
);
```

### APIs

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/qa/universities` | List universities with approval status, tech counts, conflict counts |
| `PUT` | `/api/qa/universities/{code}/approve` | Mark university as approved |
| `PUT` | `/api/qa/universities/{code}/unapprove` | Revert university to pending |
| `GET` | `/api/qa/samples/{university}` | Get existing sample (404 if none exists) |
| `POST` | `/api/qa/samples/{university}` | Create 10-tech sample for university |
| `POST` | `/api/qa/samples/{university}/refresh` | Re-scrape sample detail pages (synchronous, up to 60s) |
| `GET` | `/api/qa/conflicts/{university}` | List unresolved conflicts |
| `POST` | `/api/qa/conflicts/{id}/resolve` | Resolve a conflict (body: `{"resolution": "keep_correction" \| "accept_new"}`) |
| `GET` | `/api/proxy?url=...` | Proxy/render source page (existing, enhanced with Playwright) |
| `PATCH` | `/api/technologies/{uuid}/raw-data` | Save corrections (existing; every PATCH is recorded in qa_corrections) |

### Performance

- Playwright page render: target under 15 seconds per page, cached for 30 minutes
- Sample refresh (10 detail fetches): target under 60 seconds total
- QA page list load: under 500ms
- Correction save: under 200ms

---

## 8. Security and Privacy

### Authentication & Authorization

No authentication required. This is a local development tool.

### Input Validation

- Proxy URL parameter: validate URL format, restrict to known university base URLs to prevent SSRF
- PATCH raw-data: validate field names are strings under 100 chars, values are JSON-serializable
- University code: validate against SCRAPERS registry

### Sensitive Data

No sensitive data handled. Technology data is publicly available on university websites.

---

## 9. Testing Strategy

### Unit Tests

**Backend (pytest):**
- `qa_corrections` insert/update/query
- `bulk_insert_technologies` conflict detection (corrected field changed vs unchanged)
- Conflict resolution (keep vs accept)
- Sample creation and retrieval

### Integration Tests

- Full flow: save correction -> re-scrape -> verify conflict detected
- Approval status persists across server restarts

### Edge Cases

- University with 0 technologies in DB (duke): sample creation returns empty, message shown
- Technology deleted between sample creation and review
- Correction saved for a field that no longer exists after re-scrape
- Proxy timeout for slow-loading pages
- Concurrent saves to same technology (last write wins)

---

## 10. Dependencies and Assumptions

### Dependencies

**Existing dependencies (no changes):**
- **Playwright** (>=1.41.0) -- Already in pyproject.toml. Used for SPA rendering.
- **aiohttp** -- Already used for proxy endpoint.
- **SQLAlchemy** -- Already used for all DB operations.
- **React Router** -- Already used for frontend routing.

### Assumptions

- Playwright browsers are installed in the development environment (`playwright install chromium`)
- All Flintbox sites use the same SPA framework and can be rendered with a single Playwright strategy
- 10 technologies is a sufficient sample size for QA validation of a scraper
- The reviewer has a desktop-width screen (1280px+)

### Known Constraints

- Playwright adds memory overhead (~200MB per browser instance). Only one instance should be active at a time.
- Some source pages may have anti-bot protections that block Playwright rendering.
- Flintbox API rate limits may affect sample refresh if called too frequently.

---

## 11. Success Metrics

### Quantitative Metrics

| Metric | Target | How to Measure |
|---|---|---|
| Universities approved | 35/35 | Count in university_qa_status table |
| QA time per university | Under 10 minutes | Stopwatch during review sessions |
| Corrections overwritten | 0 | Count of corrections lost to re-scrapes |
| Source pages rendered successfully | 90%+ | Track proxy 200 vs error responses |

### Qualitative Metrics

| Metric | How to Assess |
|---|---|
| Reviewer confidence in data | Reviewer reports trust in scraped data after QA pass |
| Workflow friction | Reviewer does not need to leave the QA interface during review |

---

## 12. Implementation Order

| Phase | Scope | Risk Level | Verification |
|---|---|---|---|
| **Phase 1** | DB models (qa_corrections, qa_samples, university_qa_status, qa_conflicts), QA API routes, correction recording on PATCH | Low | Unit tests for DB operations |
| **Phase 2** | Sample management (deterministic selection, detail-page-only refresh with 10-call limit) | Medium | Verify exactly 10 API calls per refresh via logging |
| **Phase 3** | Playwright proxy rendering for Flintbox SPAs, caching | Medium | Verify Flintbox pages render in iframe |
| **Phase 4** | Frontend: approval UI, unapproved filter, sample management, conflict badges | Low | Manual walkthrough of full QA journey |
| **Phase 5** | Conflict detection in bulk_insert_technologies, conflict resolution UI | Medium | Integration test: correct -> re-scrape -> verify conflict |

---

## Design Decisions (Resolved)

- **Sample selection:** Deterministic (first 10 by ID). Re-seeding not supported in v1.
- **Approval auto-revoke on conflict:** No. Conflicts show badges but do not revoke approval.
- **Proxy cache:** In-memory, 30-minute TTL. Lost on restart is acceptable.
- **Conflict resolution:** Side-by-side (corrected vs new). No character-level diff in v1.
- **Correction storage type:** JSONB for type fidelity.
- **Conflict comparison:** Strict JSON equality. No normalization.
- **Conflict resolution effect:** "Accept new" deletes correction record (field unprotected). "Keep correction" deletes conflict record.
- **SPA detection:** Response inspection (check for JS-required indicators), not hardcoded list.
- **Sample refresh:** Synchronous HTTP request with progress. No async job queue.
- **PATCH recording:** Every PATCH to raw-data is recorded in qa_corrections.
- **Approval gate:** None. Approve button always available.
- **Unsaved changes:** Browser confirm dialog on navigation with dirty state.
- **Status enum:** `pending` and `approved` only.
- **Playwright execution:** `asyncio.to_thread()` with semaphore (1 concurrent).
- **Partial samples:** Accepted. Universities with <10 techs get what's available.
- **Table creation:** SQLAlchemy `Base.metadata.create_all()`.

## Open Questions

**Q1: [OPTIONAL] For conflict resolution, should there be a character-level diff view, or is side-by-side sufficient for v2?**

**Q2: [OPTIONAL] Should there be an option to get a fresh random sample for broader coverage beyond the fixed first-10?**
