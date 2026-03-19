"""Parsing utilities for Flintbox platform data.

Stateless functions for cleaning HTML, detecting metadata, parsing
embedded section markers, and normalizing text fields from Flintbox API responses.
"""

import re

from bs4 import BeautifulSoup


# ── Regex patterns ──────────────────────────────────────────────────────────

_METADATA_PATTERNS = re.compile(
    r"(Contact\s*:|Inventors?\s*:|Technology Category|Case Manager|"
    r"Contact Information|Case Number|Case #|USU Ref\.|USU Department)",
    re.IGNORECASE,
)

_SECTION_MARKERS = re.compile(
    r"(?:Market\s+Applications?\s*:?|Features,?\s+Benefits?\s*(?:&|and)\s*Advantages?\s*:?|"
    r"Benefits?\s*:|Reference\s+Number\s*:?|"
    r"Technology\s+(?:Overview|Applications?|Advantages?)\s*:?|"
    r"Potential\s+Applications?\s*:?|Advantages?\s*:|"
    r"Background\s*(?:&amp;|&)\s*Unmet\s+Need\s*:?|"
    r"Publications?\s*:|Patents?\s*:|"
    r"Technology\s*:(?!\s*(?:Overview|Applications?|Advantages?)))",
    re.IGNORECASE,
)

_HEADING_STRIP_RE = re.compile(
    r"\s*(?:"
    r"Background\s*(?:&amp;|&|and)\s*Unmet\s+Need"
    r"|Features,?\s+Benefits?\s*(?:&amp;|&|and)\s*Advantages?"
    r"|Market\s+Applications?"
    r"|Potential\s+Applications?"
    r"|Technology\s+(?:Overview|Applications?|Advantages?)"
    r")\s*:?\s*$",
    re.IGNORECASE,
)


# ── Public functions ────────────────────────────────────────────────────────

def clean_html_text(raw_text: str) -> str:
    """Strip HTML tags and decode common HTML entities."""
    cleaned = re.sub(r"<[^>]+>", " ", raw_text)
    cleaned = cleaned.replace("&nbsp;", " ").replace("&amp;", "&")
    cleaned = cleaned.replace("&lt;", "<").replace("&gt;", ">")
    cleaned = cleaned.replace("&quot;", '"')
    cleaned = re.sub(r"[·•]\s*", "- ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_metadata(text: str) -> bool:
    """Check if text is internal metadata rather than narrative content."""
    if not text:
        return False
    cleaned = re.sub(r"<[^>]+>", " ", text).strip()
    return bool(_METADATA_PATTERNS.search(cleaned))


def clean_html_field(raw: str) -> str:
    """Clean an HTML string into plain text, preserving paragraph structure.

    Extracts list items as newline-separated text, converts <br>/<p> tags
    to newlines, and strips non-breaking spaces and bullet markers.
    """
    if "<" in raw:
        soup = BeautifulSoup(raw, "html.parser")
        items = [li.get_text(strip=True) for li in soup.find_all("li") if li.get_text(strip=True)]
        if items:
            raw = "\n".join(f"- {item}" for item in items)
        else:
            for br_tag in soup.find_all("br"):
                br_tag.replace_with("\n")
            for p_tag in soup.find_all("p"):
                p_tag.append("\n\n")
            raw = soup.get_text(separator="")
    raw = raw.replace('\xa0', ' ').replace('&nbsp;', ' ')
    raw = re.sub(r'[·•]\s*', '- ', raw)
    # Collapse single newlines (line-wrapping artifacts) to spaces,
    # but preserve double newlines (paragraph boundaries from <p> tags)
    raw = re.sub(r'(?<!\n)\n(?!\n)', ' ', raw)
    raw = re.sub(r'[ \t]+', ' ', raw)
    lines = [line.strip() for line in raw.split('\n')]
    return '\n'.join(line for line in lines if line)


def parse_embedded_sections(abstract_html: str) -> dict:
    """Parse abstracts that contain embedded section markers.

    Detects section headings like "Market Applications:", "Benefits:",
    "Background & Unmet Need:", etc. within a single HTML field and splits
    them into separate keyed fields.

    Returns a dict with keys like: abstract, market_application, benefit,
    background, solution, ip_text, publications_html, etc.
    Only populated if markers are found; otherwise returns {"abstract": abstract_html}.
    """
    if not abstract_html:
        return {"abstract": abstract_html}

    plain = re.sub(r"<[^>]+>", " ", abstract_html)
    if not _SECTION_MARKERS.search(plain):
        return {"abstract": abstract_html}

    tag = r"(?:</?(?:p|strong|b|br|em|h[1-6])\s*/?>[\s\n]*)*"
    section_re = re.compile(
        tag
        + r"(?:"
        + r"(?P<abstract>Abstract\s*:\s*)"
        + r"|(?P<market>(?:Market|Technology|Potential)\s+Applications?\s*:?\s*)"
        + r"|(?P<solution>Technology\s*:\s*(?!\s*(?:Overview|Applications?|Advantages?)))"
        + r"|(?P<benefit>"
        +   r"Features,?\s+Benefits?\s*(?:&amp;|&|and)\s*Advantages?\s*:?\s*"
        +   r"|Technology\s+Advantages?\s*:?\s*"
        +   r"|Advantages?\s*:\s*"
        + r")"
        + r"|(?P<background>Background\s*(?:&amp;|&)\s*Unmet\s+Need\s*:?\s*)"
        + r"|(?P<overview>Technology\s+Overview\s*:?\s*)"
        + r"|(?P<ip>Intellectual\s+Property\s*:?\s*)"
        + r"|(?P<patents>(?<=\>)Patents?\s*:\s*)"
        + r"|(?P<pubs>Publications?\s*:\s*)"
        + r"|(?P<dev>Development(?:al)?\s+Stage\s*:?\s*)"
        + r"|(?P<researcher>Researchers?\s*\(?\s*s?\s*\)?\s*:\s*)"
        + r"|(?P<keywords>Key\s*[Ww]ords?\s*:\s*)"
        + r"|(?P<refnum>Reference\s+Number\s*:?\s*)"
        + r")"
        + tag,
        re.IGNORECASE,
    )

    sections: list[tuple[str, int, int]] = []
    for m in section_re.finditer(abstract_html):
        name = next((k for k, v in m.groupdict().items() if v), "unknown")
        sections.append((name, m.end(), m.start()))

    result: dict = {}

    if not sections:
        result["abstract"] = abstract_html
        return result

    # Text before the first section marker
    before = abstract_html[:sections[0][2]].strip()
    before = re.sub(r"(?:</?(?:p|strong|b|br|em)\s*/?>[\s\n]*)+$", "", before).strip()
    if before:
        before_plain = re.sub(r"<[^>]+>", " ", before).strip()
        before_plain = _HEADING_STRIP_RE.sub("", before_plain).strip()
        if before_plain:
            before = _HEADING_STRIP_RE.sub("", before).strip()
            before = re.sub(r"(?:</?(?:p|strong|b|br|em)\s*/?>[\s\n]*)+$", "", before).strip()
        if before:
            result["abstract"] = before

    # Extract content for each section
    for idx, (name, content_start, _) in enumerate(sections):
        content_end = sections[idx + 1][2] if idx + 1 < len(sections) else len(abstract_html)
        content = abstract_html[content_start:content_end].strip()
        content = re.sub(r"(?:</?(?:p|strong|b|br|em)\s*/?>[\s\n]*)+$", "", content).strip()
        if not content:
            continue

        if name == "abstract":
            result.setdefault("abstract", content)
        elif name == "background":
            result["background"] = content
        elif name == "overview":
            result["abstract"] = content
        elif name == "solution":
            result["solution"] = content
        elif name == "market":
            result["market_application"] = content
        elif name == "benefit":
            result["benefit"] = content
        elif name == "patents":
            result["patents"] = content
            if "ip_text" not in result:
                result["ip_text"] = content
        elif name == "pubs":
            result["publications_html"] = content
        elif name == "refnum":
            result["reference_number"] = content
        elif name == "ip":
            result["ip_text"] = content
        elif name == "dev":
            result["development_stage"] = content
        elif name == "researcher":
            result["researchers_html"] = content
        elif name == "keywords":
            result["keywords_html"] = content

    # Clean HTML from list-style fields
    for key in ("market_application", "benefit", "background", "solution", "ip_text",
                 "development_stage", "researchers_html", "keywords_html"):
        raw = result.get(key)
        if not raw:
            continue
        soup = BeautifulSoup(raw, "html.parser")
        items = [li.get_text(strip=True) for li in soup.find_all("li") if li.get_text(strip=True)]
        if items:
            result[key] = "\n".join(f"- {item}" for item in items)
        else:
            result[key] = soup.get_text(separator=" ", strip=True)
        result[key] = result[key].replace('\xa0', ' ').replace('&nbsp;', ' ')

    return result
