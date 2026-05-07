"""Shared title and internal-link policy for generated content."""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup


MAX_TOTAL_INTERNAL_LINKS = 5
MIN_CONTEXTUAL_INTERNAL_LINKS = 0
ALLOW_ZERO_CONTEXTUAL_LINKS = True
MIN_CONTEXTUAL_LINK_RELEVANCE = 0.72

_GENERIC_PROCUREMENT_TERMS = {
    "moq",
    "lead time",
    "supplier",
    "suppliers",
    "sample",
    "samples",
    "quote",
    "quotes",
}
_TITLE_MODIFIER_TERMS = {
    "audit",
    "benchmarks",
    "buyer",
    "capacity",
    "checklist",
    "closure",
    "comparison",
    "criteria",
    "fit",
    "formula",
    "material",
    "policy",
    "questions",
    "risk",
    "risks",
    "selection",
    "shortlist",
    "spec",
    "specs",
    "tradeoff",
    "tradeoffs",
}


def _site_base_url(site_base_url: Optional[str] = None) -> str:
    if site_base_url:
        return site_base_url
    try:
        from src.config import settings

        return settings.wordpress_url or ""
    except Exception:
        return ""


def _normalized_host(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_internal_link(url: str, site_base_url: Optional[str] = None) -> bool:
    """Return whether a URL counts against the article internal-link budget."""
    href = (url or "").strip()
    if not href or href.startswith("#"):
        return False
    if re.match(r"^(?:mailto|tel|javascript):", href, flags=re.IGNORECASE):
        return False

    parsed = urlparse(href)
    if not parsed.scheme and not parsed.netloc:
        return True
    if parsed.scheme and parsed.scheme.lower() not in {"http", "https"}:
        return False

    base = _site_base_url(site_base_url)
    if not base:
        return False
    return _normalized_host(href) == _normalized_host(base)


def normalize_link_target(url: str, site_base_url: Optional[str] = None) -> str:
    """Normalize link targets for duplicate/self-link checks."""
    href = (url or "").strip()
    if not href:
        return ""
    parsed = urlparse(href)
    if not parsed.scheme and not parsed.netloc:
        return parsed.path.rstrip("/").lower() or "/"
    host = _normalized_host(href)
    path = parsed.path.rstrip("/").lower() or "/"
    return f"{host}{path}"


def count_internal_links(html: str, site_base_url: Optional[str] = None) -> int:
    soup = BeautifulSoup(html or "", "html.parser")
    return sum(1 for a in soup.find_all("a", href=True) if is_internal_link(a.get("href", ""), site_base_url))


def remaining_internal_link_budget(current: int | str, site_base_url: Optional[str] = None) -> int:
    used = count_internal_links(current, site_base_url) if isinstance(current, str) else int(current or 0)
    return max(0, MAX_TOTAL_INTERNAL_LINKS - used)


def _opportunity_relevance(opportunity: Any) -> float:
    if isinstance(opportunity, dict):
        value = opportunity.get("relevance_score", 0)
    else:
        value = getattr(opportunity, "relevance_score", 0)
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return score / 100 if score > 1 else score


def filter_link_opportunities(
    opportunities: Iterable[Any],
    *,
    current_html: str = "",
    site_base_url: Optional[str] = None,
    source_url: Optional[str] = None,
    min_relevance: float = MIN_CONTEXTUAL_LINK_RELEVANCE,
) -> list[Any]:
    """Return relevant, deduplicated opportunities within the remaining link budget."""
    remaining = remaining_internal_link_budget(current_html, site_base_url)
    if remaining <= 0:
        return []

    existing_targets = set()
    soup = BeautifulSoup(current_html or "", "html.parser")
    for a in soup.find_all("a", href=True):
        if is_internal_link(a.get("href", ""), site_base_url):
            existing_targets.add(normalize_link_target(a.get("href", ""), site_base_url))

    source_target = normalize_link_target(source_url or "", site_base_url)
    selected = []
    seen = set(existing_targets)
    for item in sorted(list(opportunities or []), key=_opportunity_relevance, reverse=True):
        target_url = item.get("target_url", "") if isinstance(item, dict) else getattr(item, "target_url", "")
        normalized = normalize_link_target(target_url, site_base_url)
        if not target_url or not is_internal_link(target_url, site_base_url):
            continue
        if normalized in seen or (source_target and normalized == source_target):
            continue
        if _opportunity_relevance(item) < min_relevance:
            continue
        selected.append(item)
        seen.add(normalized)
        if len(selected) >= remaining:
            break
    return selected


def _link_priority(href: str, text: str, index: int, site_base_url: Optional[str]) -> tuple[int, int]:
    target = normalize_link_target(href, site_base_url)
    label = f"{target} {text}".lower()
    if any(token in label for token in ("category", "/category/", "tag", "/tag/", "product", "/product/")):
        return (0, index)
    if any(token in label for token in ("quote", "sample", "shortlist", "browse", "compare")):
        return (1, index)
    return (2, index)


def arbitrate_internal_links(
    html: str,
    *,
    site_base_url: Optional[str] = None,
    source_url: Optional[str] = None,
) -> str:
    """Prune final HTML to the canonical internal-link budget while preserving text."""
    soup = BeautifulSoup(html or "", "html.parser")
    internal_links = [a for a in soup.find_all("a", href=True) if is_internal_link(a.get("href", ""), site_base_url)]
    if not internal_links:
        return str(soup)

    source_target = normalize_link_target(source_url or "", site_base_url)
    keep_ids = set()
    seen_targets = set()
    candidates = []
    for index, link in enumerate(internal_links):
        href = link.get("href", "")
        normalized = normalize_link_target(href, site_base_url)
        if source_target and normalized == source_target:
            continue
        if normalized in seen_targets:
            continue
        seen_targets.add(normalized)
        candidates.append((link, _link_priority(href, link.get_text(" ", strip=True), index, site_base_url)))

    for link, _ in sorted(candidates, key=lambda item: item[1])[:MAX_TOTAL_INTERNAL_LINKS]:
        keep_ids.add(id(link))

    for link in internal_links:
        if id(link) not in keep_ids:
            link.unwrap()
    return str(soup)


def has_generic_procurement_tail(title: str) -> bool:
    """Detect low-value title tails made mostly of procurement field labels."""
    if ":" not in (title or ""):
        return False
    tail = title.split(":", 1)[1].lower()
    hits = [term for term in _GENERIC_PROCUREMENT_TERMS if term in tail]
    modifier_hits = [term for term in _TITLE_MODIFIER_TERMS if term in tail]
    segments = [segment.strip() for segment in re.split(r",| and | & ", tail) if segment.strip()]
    return len(hits) >= 2 and len(modifier_hits) == 0 and len(segments) <= 4


def title_quality_penalty(title: str) -> float:
    return 0.65 if has_generic_procurement_tail(title) else 1.0
