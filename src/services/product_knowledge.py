"""
Product knowledge extraction and topic-to-catalog matching helpers.

This module turns WordPress category/product payloads into structured
commercial context that can be injected into topic selection and writing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


MATERIAL_PATTERNS = [
    "pet", "petg", "hdpe", "ldpe", "pp", "ps", "glass", "aluminum", "acrylic"
]

CLOSURE_PATTERNS = [
    "spray", "sprayer", "trigger sprayer", "pump", "lotion pump", "cap",
    "flip top", "disc top", "dropper", "roller", "mist sprayer", "foamer"
]

USE_CASE_PATTERNS = [
    "cosmetic", "skincare", "personal care", "essential oil", "pharmaceutical",
    "food", "beverage", "laboratory", "cleaning", "household"
]

CERTIFICATION_PATTERNS = [
    "fda", "iso", "sgs", "reach", "rohs", "bpa free", "food grade"
]

CUSTOMIZATION_PATTERNS = [
    "custom", "customized", "private label", "logo", "screen printing",
    "hot stamping", "labeling", "label", "color matching", "frosted"
]

CAPACITY_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?(ml|l|oz)\b", re.IGNORECASE)
NECK_FINISH_RE = re.compile(r"\b(\d{2,3}/\d{2,3}|\d{2,3}-\d{2,3}|\d{2,3}mm)\b", re.IGNORECASE)
MOQ_RE = re.compile(r"\bmoq\b[^0-9]{0,20}(\d[\d,]*)", re.IGNORECASE)
LEAD_TIME_RE = re.compile(
    r"\b(?:lead\s*time|delivery\s*time|production\s*time)\b[^0-9]{0,20}(\d+\s*(?:-|to)?\s*\d*\s*(?:days?|weeks?))",
    re.IGNORECASE,
)


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _extract_first_match(pattern: re.Pattern[str], text: str) -> Optional[str]:
    match = pattern.search(text or "")
    if not match:
        return None
    return match.group(1).strip()


def _extract_terms(text: str, patterns: Sequence[str]) -> List[str]:
    lowered = text.lower()
    matches = []
    for pattern in patterns:
        if pattern in lowered:
            matches.append(pattern.upper() if pattern.isupper() else pattern)
    return matches


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]{3,}", (text or "").lower())


def _slugify(text: str) -> str:
    """Convert a term name into a WordPress-like slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug


def _looks_like_attribute_term(term_name: str) -> bool:
    """Identify tag-style terms like materials, closures, applications, or specs."""
    lowered = (term_name or "").lower()
    patterns = (
        MATERIAL_PATTERNS
        + CLOSURE_PATTERNS
        + USE_CASE_PATTERNS
        + CERTIFICATION_PATTERNS
        + CUSTOMIZATION_PATTERNS
    )
    if any(pattern in lowered for pattern in patterns):
        return True
    if CAPACITY_RE.search(lowered):
        return True
    return len(lowered.split()) <= 3


@dataclass
class CategoryInsight:
    """Structured representation of a category or taxonomy term."""

    id: Optional[int]
    name: str
    slug: str = ""
    url: Optional[str] = None
    description: str = ""
    product_count: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "url": self.url,
            "description": self.description,
            "product_count": self.product_count,
            "tags": list(self.tags),
        }


@dataclass
class ProductInsight:
    """Structured representation of a product-like entry."""

    id: Optional[int]
    name: str
    slug: str = ""
    url: Optional[str] = None
    excerpt: str = ""
    category_names: List[str] = field(default_factory=list)
    tag_names: List[str] = field(default_factory=list)
    material: Optional[str] = None
    capacity: Optional[str] = None
    neck_finish: Optional[str] = None
    closure_type: Optional[str] = None
    use_case: Optional[str] = None
    moq: Optional[str] = None
    lead_time: Optional[str] = None
    customization: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    target_industries: List[str] = field(default_factory=list)

    def descriptor(self) -> str:
        parts = [self.capacity, self.material, self.name]
        return " ".join(part for part in parts if part).strip()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "url": self.url,
            "excerpt": self.excerpt,
            "category_names": list(self.category_names),
            "tag_names": list(self.tag_names),
            "material": self.material,
            "capacity": self.capacity,
            "neck_finish": self.neck_finish,
            "closure_type": self.closure_type,
            "use_case": self.use_case,
            "moq": self.moq,
            "lead_time": self.lead_time,
            "customization": list(self.customization),
            "certifications": list(self.certifications),
            "target_industries": list(self.target_industries),
        }


@dataclass
class CatalogMatch:
    """Best-effort mapping from a topic to category/product context."""

    page_type: str
    target_category_name: Optional[str] = None
    target_category_slug: Optional[str] = None
    target_category_url: Optional[str] = None
    target_tag_name: Optional[str] = None
    target_tag_slug: Optional[str] = None
    target_tag_url: Optional[str] = None
    primary_taxonomy_type: Optional[str] = None
    primary_taxonomy_name: Optional[str] = None
    primary_taxonomy_slug: Optional[str] = None
    primary_taxonomy_url: Optional[str] = None
    supporting_products: List[Dict[str, Any]] = field(default_factory=list)
    supporting_tags: List[str] = field(default_factory=list)
    decision_questions: List[str] = field(default_factory=list)
    commercial_facts: List[str] = field(default_factory=list)


class ProductKnowledgeExtractor:
    """Extract structured product and category context from WordPress payloads."""

    def build_category_insights(self, categories: Sequence[Dict[str, Any]]) -> List[CategoryInsight]:
        insights: List[CategoryInsight] = []
        for item in categories or []:
            insights.append(
                CategoryInsight(
                    id=item.get("id"),
                    name=item.get("name", ""),
                    slug=item.get("slug", ""),
                    url=item.get("link") or item.get("url"),
                    description=_clean_html(item.get("description", "")),
                    product_count=item.get("count", 0) or 0,
                )
            )
        return [insight for insight in insights if insight.name]

    def extract_product_insight(
        self,
        item: Dict[str, Any],
        category_lookup: Optional[Dict[int, CategoryInsight]] = None,
        tag_lookup: Optional[Dict[int, str]] = None,
    ) -> ProductInsight:
        title = _clean_html(item.get("title", {}).get("rendered", item.get("title", "")))
        content = _clean_html(item.get("content", {}).get("rendered", item.get("content", "")))
        excerpt = _clean_html(item.get("excerpt", {}).get("rendered", item.get("excerpt", "")))
        combined = " ".join(part for part in [title, excerpt, content] if part)

        category_ids = item.get("product_cat") or item.get("categories") or []
        tag_ids = item.get("product_tag") or item.get("tags") or []
        category_names = [
            category_lookup[cat_id].name
            for cat_id in category_ids
            if category_lookup and cat_id in category_lookup
        ]
        tag_names = [
            tag_lookup[tag_id]
            for tag_id in tag_ids
            if tag_lookup and tag_id in tag_lookup
        ]

        material = next((m.upper() if len(m) <= 4 else m.title() for m in MATERIAL_PATTERNS if m in combined.lower()), None)
        capacity = _extract_first_match(CAPACITY_RE, combined)
        if capacity:
            unit_match = CAPACITY_RE.search(combined)
            if unit_match:
                capacity = f"{unit_match.group(1)}{unit_match.group(2).lower()}"

        closure = next((term.title() for term in CLOSURE_PATTERNS if term in combined.lower()), None)
        use_case = next((term.title() for term in USE_CASE_PATTERNS if term in combined.lower()), None)

        customization = [term.title() for term in _extract_terms(combined, CUSTOMIZATION_PATTERNS)]
        certifications = [term.upper() if len(term) <= 4 else term.title() for term in _extract_terms(combined, CERTIFICATION_PATTERNS)]
        target_industries = [term.title() for term in _extract_terms(combined, USE_CASE_PATTERNS)]

        return ProductInsight(
            id=item.get("id"),
            name=title,
            slug=item.get("slug", ""),
            url=item.get("link") or item.get("permalink"),
            excerpt=excerpt,
            category_names=category_names,
            tag_names=tag_names,
            material=material,
            capacity=capacity,
            neck_finish=_extract_first_match(NECK_FINISH_RE, combined),
            closure_type=closure,
            use_case=use_case,
            moq=_extract_first_match(MOQ_RE, combined),
            lead_time=_extract_first_match(LEAD_TIME_RE, combined),
            customization=customization,
            certifications=certifications,
            target_industries=target_industries,
        )


class ProductCatalogMatcher:
    """Map keywords/topics to the best category and supporting products."""

    def match_topic(
        self,
        keyword: str,
        categories: Sequence[CategoryInsight],
        products: Sequence[ProductInsight],
        tags: Optional[Sequence[Any]] = None,
    ) -> CatalogMatch:
        page_type = self._infer_page_type(keyword)
        category, category_score = self._select_taxonomy_term(keyword, categories, products, taxonomy_type="category")
        tag_insights = self._normalize_term_insights(tags or [])
        tag, tag_score = self._select_taxonomy_term(keyword, tag_insights, products, taxonomy_type="tag")
        primary_term, primary_type = self._select_primary_target(
            category,
            category_score,
            tag,
            tag_score,
            keyword,
        )

        matched_products = self._select_products(
            keyword,
            products,
            category_name=category.name if category else None,
            tag_name=tag.name if tag else None,
        )

        supporting_tags = self._collect_tags(matched_products, tag_insights)
        decision_questions = self._build_decision_questions(page_type, primary_term, matched_products)
        commercial_facts = self._build_commercial_facts(primary_term, matched_products)

        return CatalogMatch(
            page_type=page_type,
            target_category_name=category.name if category else None,
            target_category_slug=category.slug if category else None,
            target_category_url=category.url if category else None,
            target_tag_name=tag.name if tag else None,
            target_tag_slug=tag.slug if tag else None,
            target_tag_url=tag.url if tag else None,
            primary_taxonomy_type=primary_type,
            primary_taxonomy_name=primary_term.name if primary_term else None,
            primary_taxonomy_slug=primary_term.slug if primary_term else None,
            primary_taxonomy_url=primary_term.url if primary_term else None,
            supporting_products=[product.to_dict() for product in matched_products],
            supporting_tags=supporting_tags,
            decision_questions=decision_questions,
            commercial_facts=commercial_facts,
        )

    def _infer_page_type(self, keyword: str) -> str:
        lowered = keyword.lower()
        if any(term in lowered for term in ["moq", "lead time", "quote", "price", "wholesale", "supplier", "manufacturer"]):
            return "wholesale_faq"
        if any(term in lowered for term in ["vs", "versus", "compare", "comparison", "difference"]):
            return "spec_comparison"
        if any(term in lowered for term in ["how to choose", "best", "selection", "choose", "for "]):
            return "product_selection"
        return "category_support"

    def _normalize_term_insights(self, terms: Sequence[Any]) -> List[CategoryInsight]:
        """Accept taxonomy terms as dataclasses, dicts, or plain strings."""
        normalized: List[CategoryInsight] = []
        for term in terms:
            if isinstance(term, CategoryInsight):
                normalized.append(term)
            elif isinstance(term, dict):
                name = term.get("name", "")
                if name:
                    normalized.append(
                        CategoryInsight(
                            id=term.get("id"),
                            name=name,
                            slug=term.get("slug", "") or _slugify(name),
                            url=term.get("url") or term.get("link"),
                            description=_clean_html(term.get("description", "")),
                            product_count=term.get("count", 0) or term.get("product_count", 0) or 0,
                        )
                    )
            elif isinstance(term, str) and term.strip():
                normalized.append(
                    CategoryInsight(
                        id=None,
                        name=term.strip(),
                        slug=_slugify(term),
                    )
                )
        return normalized

    def _select_taxonomy_term(
        self,
        keyword: str,
        terms: Sequence[CategoryInsight],
        products: Sequence[ProductInsight],
        taxonomy_type: str,
    ) -> tuple[Optional[CategoryInsight], int]:
        if not terms:
            return None, -1

        keyword_tokens = set(_tokenize(keyword))
        best_score = -1
        best_term = None

        for term in terms:
            term_tokens = set(_tokenize(" ".join([term.name, term.slug, term.description])))
            score = len(keyword_tokens & term_tokens)

            product_support = sum(
                1 for product in products
                if self._product_matches_taxonomy(product, term.name, taxonomy_type)
                and keyword_tokens & set(_tokenize(" ".join([product.descriptor(), " ".join(product.tag_names)])))
            )
            score += product_support

            if term.product_count:
                score += min(term.product_count, 6) // 3

            if score > best_score:
                best_score = score
                best_term = term

        if best_score <= 0:
            return terms[0], best_score
        return best_term, best_score

    def _select_primary_target(
        self,
        category: Optional[CategoryInsight],
        category_score: int,
        tag: Optional[CategoryInsight],
        tag_score: int,
        keyword: str,
    ) -> tuple[Optional[CategoryInsight], Optional[str]]:
        """Choose which taxonomy page should be treated as the primary landing page."""
        if tag and self._keyword_prefers_tag_page(keyword, tag, category, category_score, tag_score):
            return tag, "tag"
        if category and (category_score >= tag_score or not tag):
            return category, "category"
        if tag:
            return tag, "tag"
        return None, None

    def _keyword_prefers_tag_page(
        self,
        keyword: str,
        tag: CategoryInsight,
        category: Optional[CategoryInsight],
        category_score: int,
        tag_score: int,
    ) -> bool:
        """Prefer tag pages for attribute-led searches like PET, fine mist, or skincare."""
        keyword_lower = (keyword or "").lower()
        tag_tokens = set(_tokenize(" ".join([tag.name, tag.slug, tag.description])))
        category_tokens = set(_tokenize(" ".join([
            category.name if category else "",
            category.slug if category else "",
            category.description if category else "",
        ])))
        keyword_tokens = set(_tokenize(keyword_lower))

        tag_overlap = len(keyword_tokens & tag_tokens)
        category_overlap = len(keyword_tokens & category_tokens)
        attribute_like = _looks_like_attribute_term(tag.name)
        direct_tag_phrase = tag.name.lower() in keyword_lower or tag.slug.replace("-", " ") in keyword_lower

        if not attribute_like and not direct_tag_phrase:
            return False

        attribute_keyword_terms = [
            term for term in [tag.name.lower(), tag.slug.replace("-", " ")]
            if term and term in keyword_lower
        ]
        if direct_tag_phrase and attribute_keyword_terms:
            return True

        if tag_overlap > category_overlap:
            return True

        return direct_tag_phrase and tag_score >= max(category_score - 1, 1)

    def _product_matches_taxonomy(self, product: ProductInsight, term_name: str, taxonomy_type: str) -> bool:
        """Check whether a product belongs to the given category or tag."""
        if taxonomy_type == "tag":
            return term_name in product.tag_names
        return term_name in product.category_names

    def _select_products(
        self,
        keyword: str,
        products: Sequence[ProductInsight],
        category_name: Optional[str],
        tag_name: Optional[str] = None,
        limit: int = 3,
    ) -> List[ProductInsight]:
        if not products:
            return []

        keyword_tokens = set(_tokenize(keyword))
        scored: List[tuple[int, ProductInsight]] = []

        for product in products:
            text = " ".join([
                product.name,
                product.descriptor(),
                " ".join(product.category_names),
                " ".join(product.tag_names),
                product.use_case or "",
            ])
            score = len(keyword_tokens & set(_tokenize(text)))
            if category_name and category_name in product.category_names:
                score += 2
            if tag_name and tag_name in product.tag_names:
                score += 2
            if product.capacity:
                score += 1
            if product.material:
                score += 1
            if score > 0:
                scored.append((score, product))

        scored.sort(key=lambda item: item[0], reverse=True)
        if scored:
            return [product for _, product in scored[:limit]]

        if category_name:
            category_products = [product for product in products if category_name in product.category_names]
            if category_products:
                return category_products[:limit]

        if tag_name:
            tag_products = [product for product in products if tag_name in product.tag_names]
            if tag_products:
                return tag_products[:limit]

        return list(products[:limit])

    def _collect_tags(self, products: Sequence[ProductInsight], tags: Sequence[CategoryInsight]) -> List[str]:
        collected: List[str] = []
        for product in products:
            for tag in product.tag_names:
                if tag and tag not in collected:
                    collected.append(tag)
        for tag in tags:
            tag_name = tag.name if isinstance(tag, CategoryInsight) else str(tag)
            if tag_name and tag_name not in collected:
                collected.append(tag_name)
            if len(collected) >= 6:
                break
        return collected[:6]

    def _build_decision_questions(
        self,
        page_type: str,
        primary_term: Optional[CategoryInsight],
        products: Sequence[ProductInsight],
    ) -> List[str]:
        subject = primary_term.name if primary_term else "this packaging option"
        questions = [
            f"Which {subject} options fit the target application and filling process?",
            f"What MOQ, lead time, and customization constraints apply to {subject} sourcing?",
        ]

        if page_type in {"product_selection", "spec_comparison"}:
            questions.append(f"Which material, capacity, and closure combinations are the best fit for {subject}?")
        if any(product.certifications for product in products):
            questions.append(f"Which certifications or compliance requirements matter before ordering {subject}?")
        if any(product.neck_finish for product in products):
            questions.append(f"What neck finish or closure compatibility checks should buyers confirm for {subject}?")

        deduped: List[str] = []
        for question in questions:
            if question not in deduped:
                deduped.append(question)
        return deduped[:5]

    def _build_commercial_facts(
        self,
        primary_term: Optional[CategoryInsight],
        products: Sequence[ProductInsight],
    ) -> List[str]:
        facts: List[str] = []
        if primary_term and primary_term.product_count:
            facts.append(f"Catalog coverage: {primary_term.product_count} listed items in {primary_term.name}.")

        for product in products:
            descriptor = product.descriptor() or product.name
            if product.moq:
                facts.append(f"{descriptor} references MOQ {product.moq}.")
            if product.lead_time:
                facts.append(f"{descriptor} references lead time {product.lead_time}.")
            if product.customization:
                facts.append(f"{descriptor} supports customization: {', '.join(product.customization[:3])}.")
            if product.certifications:
                facts.append(f"{descriptor} highlights certifications: {', '.join(product.certifications[:3])}.")
            if product.neck_finish:
                facts.append(f"{descriptor} uses neck finish {product.neck_finish}.")
            if product.closure_type:
                facts.append(f"{descriptor} pairs with {product.closure_type}.")

        return facts[:8]
