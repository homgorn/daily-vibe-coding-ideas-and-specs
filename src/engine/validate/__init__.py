"""Validation: 5 agents + SEO/GEO checker + link checker + legal check.

Rule: publication without all green checks is impossible.
Agents: data, text, image, video, post + seo_geo + links + legal + generation.
"""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from engine.spec import FALLBACK_MARKER as SPEC_FALLBACK_MARKER

ROOT = Path(__file__).resolve().parents[3]

TRUSTED_DOMAINS = {
    "wikipedia.org", "en.wikipedia.org", "ru.wikipedia.org",
    "arxiv.org", "mdn.io", "developer.mozilla.org",
    "w3.org", "www.w3.org", "specs.w3.org",
    "github.com", "docs.github.com", "api.github.com",
    "openai.com", "docs.openai.com", "platform.openai.com",
    "anthropic.com", "docs.anthropic.com",
    "vercel.com", "nextjs.org", "docs.python.org",
    "docs.rs", "crates.io", "npmjs.com",
    "stackoverflow.com", "news.ycombinator.com",
    "gov", "edu", "ieee.org", "acm.org",
    "cloudflare.com", "developers.cloudflare.com",
}

FRONTMATTER_REQUIRED = ["title", "tags", "origin", "viability_score"]


@dataclass
class ValidationResult:
    agent: str
    passed: bool
    score: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    artifact_path: str
    artifact_type: str
    results: list[ValidationResult] = field(default_factory=list)
    passed: bool = False

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def summary(self) -> dict:
        return {
            "artifact": self.artifact_path,
            "type": self.artifact_type,
            "passed": self.all_passed,
            "agents": [
                {"agent": r.agent, "passed": r.passed, "score": r.score,
                 "errors": r.errors, "warnings": r.warnings}
                for r in self.results
            ],
        }


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter from markdown."""
    if not content.startswith("---"):
        return {}, content
    try:
        end = content.index("---", 3)
        fm_text = content[3:end].strip()
        body = content[end + 3:].strip()
    except ValueError:
        return {}, content

    fm = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if value.startswith("[") and value.endswith("]"):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
        elif value in ("true", "false"):
            value = value == "true"
        elif value.isdigit():
            value = int(value)
        fm[key] = value
    return fm, body


def extract_urls(text: str) -> list[str]:
    """Extract all URLs from text."""
    url_pattern = re.compile(r"https?://[^\s\)\]\>\"\'\,\;\)]+")
    urls = url_pattern.findall(text)
    # Strip trailing punctuation
    return list(set(u.rstrip(".,;:!?") for u in urls))


def check_data_agent(content: str, fm: dict) -> ValidationResult:
    """Data agent: verifies factual claims have citations, no invented data."""
    errors = []
    warnings = []

    # Check for Cited: block or sources
    has_citation = bool(re.search(r"Cited:|## Cited Sources|\[source:\d+\]|\[\d+\]", content, re.IGNORECASE))
    if not has_citation:
        warnings.append("No citation block found (Cited: or ## Cited Sources)")

    # Check for suspicious invented patterns
    suspicious = [
        (r"\b\d{1,3}(?:\.\d)?% (?:of|growth|increase)", "Percentage claim without source"),
        (r"\$\d+(?:\.\d+)?[BMK] (?:market|revenue|valuation)", "Money figure without source"),
        (r"according to (?:a )?study", "Vague study reference"),
    ]
    for pattern, msg in suspicious:
        if re.search(pattern, content, re.IGNORECASE):
            # Only warn if no citation nearby
            if not has_citation:
                warnings.append(msg)

    # Frontmatter viability check
    if "viability_score" in fm:
        score = fm["viability_score"]
        if isinstance(score, (int, float)) and not (0 <= score <= 100):
            errors.append(f"viability_score out of range 0-100: {score}")

    passed = len(errors) == 0
    score = max(0, 1.0 - len(warnings) * 0.1)
    return ValidationResult("data", passed, score, errors, warnings)


def check_text_agent(content: str, fm: dict) -> ValidationResult:
    """Text agent: verifies structure, frontmatter, readability."""
    errors = []
    warnings = []

    # Frontmatter required fields
    for req in FRONTMATTER_REQUIRED:
        if req not in fm:
            errors.append(f"Missing required frontmatter field: {req}")

    # Check title length
    title = fm.get("title", "")
    if title and len(title) > 70:
        warnings.append(f"Title too long: {len(title)} chars (max 70)")

    # Check content length
    if len(content) < 200:
        warnings.append(f"Content too short: {len(content)} chars")

    # Check for H1
    h1_count = len(re.findall(r"^# ", content, re.MULTILINE))
    if h1_count > 1:
        warnings.append(f"Multiple H1 headings: {h1_count}")
    if h1_count == 0 and not content.startswith("#"):
        warnings.append("No H1 heading found")

    # Check heading hierarchy
    headings = re.findall(r"^(#{1,6}) ", content, re.MULTILINE)
    prev_level = 0
    for h in headings:
        level = len(h)
        if level > prev_level + 1 and prev_level > 0:
            warnings.append(f"Skipped heading level: H{prev_level} -> H{level}")
        prev_level = level

    # Check for placeholder text
    placeholders = ["TODO", "TBD", "FIXME", "XXX", "Lorem ipsum", "auto-generated fallback"]
    for ph in placeholders:
        if ph.lower() in content.lower():
            warnings.append(f"Placeholder text found: {ph}")

    passed = len(errors) == 0
    score = max(0, 1.0 - len(warnings) * 0.15)
    return ValidationResult("text", passed, score, errors, warnings)


def check_image_agent(content: str, fm: dict) -> ValidationResult:
    """Image agent: verifies image references and OG image."""
    errors = []
    warnings = []

    # Check image references
    img_refs = re.findall(r"!\[.*?\]\((.*?)\)", content)
    for img in img_refs:
        if img.startswith("http"):
            # External image - just note it
            pass
        elif not img.startswith(("http", "data:")):
            # Local image - check existence
            img_path = ROOT / img
            if not img_path.exists():
                warnings.append(f"Image not found: {img}")

    # Check for og:image in frontmatter
    if "og_image" not in fm and "image" not in fm:
        warnings.append("No og_image/image in frontmatter")

    passed = len(errors) == 0
    score = max(0, 1.0 - len(warnings) * 0.2)
    return ValidationResult("image", passed, score, errors, warnings)


def check_video_agent(content: str, fm: dict) -> ValidationResult:
    """Video agent: verifies video references (for video artifacts)."""
    errors = []
    warnings = []

    video_refs = re.findall(r"(youtube\.com|youtu\.be|vimeo\.com|tiktok\.com)", content)
    if not video_refs and "video" in fm.get("origin", ""):
        warnings.append("No video references found for video artifact")

    passed = len(errors) == 0
    return ValidationResult("video", passed, 1.0, errors, warnings)


def check_post_agent(content: str, fm: dict) -> ValidationResult:
    """Post agent: verifies social media post constraints."""
    errors = []
    warnings = []

    title = fm.get("title", "")

    # Twitter/X limit
    if len(content) > 280 and "twitter" in content.lower():
        warnings.append(f"Content exceeds 280 chars for Twitter: {len(content)}")

    # Description length for meta
    desc = fm.get("description", "")
    if desc and not (120 <= len(desc) <= 160):
        warnings.append(f"Description length {len(desc)} (ideal 120-160)")

    passed = len(errors) == 0
    score = max(0, 1.0 - len(warnings) * 0.2)
    return ValidationResult("post", passed, score, errors, warnings)


def check_seo_geo(content: str, fm: dict) -> ValidationResult:
    """SEO/GEO checker: title, description, structure, schema."""
    errors = []
    warnings = []

    title = fm.get("title", "")
    desc = fm.get("description", "")

    # Title
    if not title:
        errors.append("Missing title")
    elif len(title) > 60:
        warnings.append(f"Title too long: {len(title)} (max 60)")

    # Description
    if not desc:
        warnings.append("Missing description (120-160 chars recommended)")
    elif not (120 <= len(desc) <= 160):
        warnings.append(f"Description length {len(desc)} (ideal 120-160)")

    # Keywords
    if "keywords" not in fm and "tags" not in fm:
        warnings.append("No keywords/tags in frontmatter")

    # Canonical
    if "canonical" not in fm:
        warnings.append("No canonical URL in frontmatter")

    # FAQ block for GEO
    has_faq = bool(re.search(r"## (FAQ|Q&A|Вопрос)", content, re.IGNORECASE))
    if not has_faq:
        warnings.append("No FAQ block (recommended for GEO/AEO)")

    # JSON-LD schema
    has_jsonld = '"@type"' in content or "schema.org" in content
    if not has_jsonld:
        warnings.append("No JSON-LD structured data (recommended)")

    # Single H1
    h1_count = len(re.findall(r"^# ", content, re.MULTILINE))
    if h1_count > 1:
        errors.append(f"Multiple H1 headings: {h1_count} (SEO violation)")

    passed = len(errors) == 0
    score = max(0, 1.0 - len(warnings) * 0.1)
    return ValidationResult("seo_geo", passed, score, errors, warnings)


def check_links(content: str, fm: dict, timeout: int = 10) -> ValidationResult:
    """Link checker: all external links must be alive."""
    errors = []
    warnings = []

    urls = extract_urls(content)
    if not urls:
        warnings.append("No links found in content")
        return ValidationResult("links", True, 0.8, errors, warnings)

    for url in urls[:20]:  # Limit to 20 links
        try:
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "DailyVibeEngine/0.1")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status >= 400:
                    errors.append(f"Broken link ({resp.status}): {url}")
        except urllib.error.HTTPError as e:
            if e.code in (403, 405, 429):
                # Some sites block HEAD, try GET
                try:
                    req = urllib.request.Request(url)
                    req.add_header("User-Agent", "DailyVibeEngine/0.1")
                    with urllib.request.urlopen(req, timeout=timeout):
                        pass
                except Exception:
                    warnings.append(f"Unreachable ({e.code}): {url}")
            else:
                errors.append(f"Broken link ({e.code}): {url}")
        except Exception as e:
            warnings.append(f"Link check failed: {url} — {type(e).__name__}")

    passed = len(errors) == 0
    score = max(0, 1.0 - len(errors) * 0.3 - len(warnings) * 0.05)
    return ValidationResult("links", passed, score, errors, warnings)


def check_legal(content: str, fm: dict) -> ValidationResult:
    """Legal check: disclaimers, copyright, compliance."""
    errors = []
    warnings = []

    # Investment disclaimers
    investment_keywords = ["investment", "investor", "pitch", "funding", "revenue projection"]
    if any(kw in content.lower() for kw in investment_keywords):
        has_disclaimer = bool(re.search(
            r"disclaimer|not financial advice|не является инвестиционной|DYOR",
            content, re.IGNORECASE
        ))
        if not has_disclaimer:
            errors.append("Investment content requires disclaimer")

    # AI content disclosure
    if "ai-generated" not in content.lower() and "generated by ai" not in content.lower():
        warnings.append("Consider AI content disclosure (EU AI Act)")

    # CC BY-NC-ND attribution
    if "cc by-nc-nd" not in content.lower() and "license" not in content.lower():
        warnings.append("No license notice found")

    # BMAD trademark
    if "bmad" in content.lower() and "™" not in content:
        warnings.append("BMAD referenced without trademark notice")

    passed = len(errors) == 0
    score = max(0, 1.0 - len(warnings) * 0.15)
    return ValidationResult("legal", passed, score, errors, warnings)


def validate_artifact(filepath: str | Path, artifact_type: str = "idea",
                      check_links_online: bool = False) -> ValidationReport:
    """Run all validation agents on an artifact."""
    filepath = Path(filepath)
    if not filepath.exists():
        report = ValidationReport(str(filepath), artifact_type)
        report.results.append(ValidationResult(
            "structure", False, 0, [f"File not found: {filepath}"]
        ))
        report.passed = False
        return report

    content = filepath.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(content)

    report = ValidationReport(str(filepath), artifact_type)

    # Generation gate: an artifact the generator failed to fill in must never
    # pass. Template filler reads exactly like a real spec on the surface, so
    # without this check the pipeline happily publishes empty analysis.
    if SPEC_FALLBACK_MARKER in content:
        report.results.append(ValidationResult(
            "generation", False, 0.0,
            [
                "Spec generation failed — body was never filled in "
                f"({SPEC_FALLBACK_MARKER}). Regenerate before publishing."
            ],
        ))

    # 5 core agents
    report.results.append(check_data_agent(content, fm))
    report.results.append(check_text_agent(content, fm))
    report.results.append(check_image_agent(content, fm))
    report.results.append(check_video_agent(content, fm))
    report.results.append(check_post_agent(content, fm))

    # SEO/GEO
    report.results.append(check_seo_geo(content, fm))

    # Links (offline mode by default)
    if check_links_online:
        report.results.append(check_links(content, fm))
    else:
        report.results.append(ValidationResult("links", True, 1.0, [], ["Offline mode — links not checked"]))

    # Legal
    report.results.append(check_legal(content, fm))

    report.passed = report.all_passed
    return report


def validate_all(directory: str | Path, artifact_type: str = "idea",
                 check_links_online: bool = False) -> list[ValidationReport]:
    """Validate all markdown files in a directory."""
    directory = Path(directory)
    reports = []
    for md_file in sorted(directory.glob("*.md")):
        reports.append(validate_artifact(md_file, artifact_type, check_links_online))
    return reports