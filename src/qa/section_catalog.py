"""UI section catalog for Migration QA.

Single source of truth mapping the UI sections rendered by `ContentSections`,
`SidePanel`, and `DiscoveryDrawer` to the underlying `raw_data` keys (or
top-level `technologies` columns) that feed them.

Consumed by:
  - `migration_audit.py` (AU-2): for DB-side coverage evaluation.
  - Playwright specs in `web/e2e/` (AU-4, AU-5): fixture file mirrors this
    catalog's section IDs; kept in sync by convention.
  - `matrix.py` (AU-9): as the column list in the gap matrix.

Shape tokens (closed set):
  array_of_strings, array_of_objects, newline_string, comma_string,
  html_string, plain_string, object

`surfaces` reflects the TARGET state after AU-8 lands: all non-assessment
sections should render on both drawer and detail. The audit measures
distance to this target, and Playwright assertions use it to know which
surface is expected to show each section.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Surface = Literal["drawer", "detail"]
ShapeToken = Literal[
    "array_of_strings",
    "array_of_objects",
    "newline_string",
    "comma_string",
    "html_string",
    "plain_string",
    "object",
]
SourceType = Literal["raw_data", "column"]


@dataclass(frozen=True)
class SectionSource:
    type: SourceType
    key: str
    accepted_shapes: tuple[ShapeToken, ...]


@dataclass(frozen=True)
class Section:
    id: str
    label: str
    sources: tuple[SectionSource, ...]
    surfaces: tuple[Surface, ...] = ("drawer", "detail")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "sources": [
                {"type": s.type, "key": s.key, "accepted_shapes": list(s.accepted_shapes)}
                for s in self.sources
            ],
            "surfaces": list(self.surfaces),
        }


def _rd(key: str, *shapes: ShapeToken) -> SectionSource:
    return SectionSource(type="raw_data", key=key, accepted_shapes=shapes)


def _col(key: str, *shapes: ShapeToken) -> SectionSource:
    return SectionSource(type="column", key=key, accepted_shapes=shapes)


CATALOG: tuple[Section, ...] = (
    # Content sections (in render order)
    Section("subtitle", "Subtitle", (_rd("subtitle", "plain_string", "html_string"),)),
    Section("summary", "Summary", (_rd("short_description", "plain_string", "html_string"),)),
    Section("abstract", "Abstract", (_rd("abstract", "plain_string", "html_string"),)),
    Section("overview", "Overview", (_rd("other", "html_string", "plain_string"),)),
    Section(
        "description",
        "Description",
        (_col("description", "plain_string", "newline_string", "html_string"),),
    ),
    Section(
        "technical_problem",
        "Technical Problem",
        (_rd("technical_problem", "plain_string", "html_string"),),
    ),
    Section("solution", "Solution", (_rd("solution", "plain_string", "html_string"),)),
    Section(
        "background", "Background", (_rd("background", "plain_string", "html_string"),)
    ),
    Section(
        "full_description",
        "Full Description",
        (_rd("full_description", "plain_string", "html_string"),),
    ),
    Section("benefits", "Benefits", (_rd("benefit", "html_string", "plain_string"),)),
    Section(
        "market_opportunity",
        "Market Opportunity",
        (
            _rd("market_application", "html_string", "plain_string"),
            _rd("market_opportunity", "html_string", "plain_string"),
        ),
    ),
    Section(
        "development_stage",
        "Development Stage",
        (_rd("development_stage", "plain_string", "html_string"),),
    ),
    Section(
        "trl",
        "Technology Readiness Level",
        (_rd("trl", "plain_string"),),
    ),
    Section(
        "key_points",
        "Key Points",
        (_rd("key_points", "array_of_strings", "newline_string"),),
    ),
    Section(
        "applications",
        "Applications",
        (_rd("applications", "array_of_strings", "plain_string", "newline_string"),),
    ),
    Section(
        "advantages",
        "Advantages",
        (_rd("advantages", "array_of_strings", "plain_string", "newline_string"),),
    ),
    Section(
        "technology_validation",
        "Technology Validation",
        (_rd("technology_validation", "array_of_strings", "newline_string"),),
    ),
    Section(
        "publications",
        "Publications",
        (_rd("publications", "array_of_objects", "array_of_strings", "html_string", "plain_string"),),
    ),
    Section(
        "ip_status",
        "IP Status",
        (
            _rd("ip_status", "plain_string", "html_string"),
            _rd("ip_number", "plain_string"),
            _rd("ip_text", "plain_string", "html_string"),
        ),
    ),

    # Side panel sections
    Section(
        "researchers",
        "Researchers",
        (_rd("researchers", "array_of_objects", "array_of_strings", "newline_string"),),
    ),
    Section(
        "inventors",
        "Inventors",
        (_rd("inventors", "array_of_strings", "newline_string", "comma_string"),),
    ),
    Section(
        "departments",
        "Departments",
        (_rd("client_departments", "array_of_strings", "newline_string"),),
    ),
    Section(
        "contacts",
        "Contacts",
        (
            _rd("contacts", "array_of_objects"),
            _rd("contact", "object"),
        ),
    ),
    Section(
        "classification",
        "Classification",
        (
            _col("top_field", "plain_string"),
            _col("subfield", "plain_string"),
        ),
    ),
    Section(
        "keywords",
        "Keywords",
        (_col("keywords", "array_of_strings"),),
    ),
    Section(
        "tags",
        "Tags",
        (_rd("flintbox_tags", "array_of_strings"),),
    ),
    Section(
        "documents",
        "Documents",
        (
            _rd("documents", "array_of_objects"),
            _rd("supporting_documents", "array_of_objects"),
            _rd("pdf_url", "plain_string"),
        ),
    ),
    Section(
        "licensing_contact",
        "Licensing Contact",
        (_rd("licensing_contact", "object"),),
    ),
    Section(
        "related_portfolio",
        "Related Technologies",
        (_rd("related_portfolio", "array_of_objects"),),
    ),
    Section(
        "source_link",
        "Source",
        (_col("url", "plain_string"),),
    ),
)


SECTION_IDS: tuple[str, ...] = tuple(s.id for s in CATALOG)


def catalog_as_dicts() -> list[dict]:
    """Serialize the catalog for JSON consumers."""
    return [s.to_dict() for s in CATALOG]
