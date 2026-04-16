"""
Search Intent Analyzer
Analyzes real user search intent from keywords to generate meaningful content
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class UserIntent(str, Enum):
    """Real user search intents"""
    PROBLEM_SOLVING = "problem_solving"  # "how to fix", "why does"
    COMPARISON = "comparison"  # "vs", "versus", "compared to"
    SPECIFICATION = "specification"  # "what is", "properties of"
    BUYING_GUIDE = "buying_guide"  # "best for", "which to choose"
    TECHNICAL_DEEP_DIVE = "technical"  # specific technical terms


@dataclass
class IntentSignal:
    """Signal indicating user intent"""
    keyword: str
    intent: UserIntent
    confidence: float  # 0-1
    semantic_context: List[str]  # Related terms that indicate this intent


@dataclass
class ContentRouteSignal:
    """Deterministic routing result for the article lane."""
    keyword: str
    content_lane: str
    confidence: float
    search_stage: str
    signal_scores: Dict[str, float]
    reasons: List[str]


class SearchIntentAnalyzer:
    """Analyzes search intent from keywords"""

    PRODUCT_HEAD_PATTERN = re.compile(
        r"\b(?:\d+(?:\.\d+)?\s*(?:ml|l|oz|g)\s+)?"
        r"(?:fine mist spray bottle|spray bottle|foam bottle|pump bottle|dropper bottle|"
        r"lotion bottle|bottle|jar|container|tube|sprayer|pump|foamer)\b",
        re.IGNORECASE,
    )
    COMMERCIAL_TERMS = {
        "supplier", "suppliers", "wholesale", "manufacturer", "manufacturers", "factory",
        "moq", "quote", "quotes", "lead time", "lead-time", "customization", "custom",
        "audit", "sample", "samples", "bulk", "oem", "odm", "price", "pricing",
        "shipment", "shipping", "packaging", "qc", "quality control"
    }
    TRAFFIC_TERMS = {
        "vs", "versus", "difference", "compare", "comparison", "application", "applications",
        "use case", "use cases", "for", "best", "material", "materials", "compatibility",
        "problem", "problems", "risk", "risks", "mistake", "mistakes", "choose", "selection",
        "fit", "tradeoff", "trade-offs", "tradeoffs", "why", "how to", "prevent", "avoid"
    }
    DECISION_STAGE_TERMS = {
        "supplier", "wholesale", "manufacturer", "moq", "quote", "lead time", "lead-time",
        "customization", "audit", "sample", "samples", "price", "pricing", "bulk"
    }
    CONSIDERATION_STAGE_TERMS = {
        "best", "compare", "comparison", "vs", "versus", "material", "materials", "choose",
        "selection", "fit", "application", "applications", "for", "difference"
    }
    AWARENESS_STAGE_TERMS = {
        "why", "problem", "problems", "risk", "risks", "mistake", "mistakes", "prevent",
        "avoid", "compatible", "compatibility"
    }

    INTENT_PATTERNS = {
        UserIntent.PROBLEM_SOLVING: ["fix", "prevent", "solve", "cracking", "issue", "problem", "repair"],
        UserIntent.COMPARISON: ["vs", "versus", "compared", "difference", "better"],
        UserIntent.SPECIFICATION: ["properties", "specifications", "resistance", "characteristics", "data"],
        UserIntent.BUYING_GUIDE: ["buy", "supplier", "wholesale", "quote", "cost", "price", "choose", "selection", "manufacturer", "moq"],
        UserIntent.TECHNICAL_DEEP_DIVE: ["analysis", "mechanism", "process", "structure"],
    }

    SEMANTIC_EXPANSIONS = {
        "pipe": ["fitting", "connection", "installation", "pressure rating", "diameter"],
        "plastic": ["polymer", "resin", "material", "compound"],
        "HDPE": ["high density polyethylene", "PE100", "PE80"],
        "resistance": ["durability", "performance", "stability"],
    }

    def analyze_intent(self, keyword: str, related_keywords: List[str] = None) -> IntentSignal:
        """Analyze the real user intent behind a keyword"""
        keyword_lower = self._normalize_keyword(keyword)
        related = [k.lower() for k in (related_keywords or [])]
        all_text = keyword_lower + " " + " ".join(related)

        scores = {}
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = sum(1 for p in patterns if p in all_text)
            if score > 0:
                scores[intent] = score

        if not scores:
            intent = UserIntent.SPECIFICATION
            confidence = 0.5
        else:
            intent = max(scores, key=scores.get)
            confidence = min(0.9, 0.6 + (scores[intent] * 0.1))

        context = [word for word in re.split(r"\s+", keyword_lower) if len(word) > 2]

        return IntentSignal(
            keyword=keyword,
            intent=intent,
            confidence=confidence,
            semantic_context=context
        )

    def route_content_lane(
        self,
        keyword: str,
        catalog_context: Optional[Dict[str, object]] = None,
        related_keywords: Optional[List[str]] = None,
    ) -> ContentRouteSignal:
        """Route the keyword into traffic-entry or procurement-conversion."""
        normalized_keyword = self._normalize_keyword(keyword)
        combined_text = " ".join(
            part for part in [normalized_keyword, " ".join((related_keywords or []))] if part
        ).lower()
        catalog_context = catalog_context or {}

        product_head = self._is_product_head_query(normalized_keyword)
        catalog_support = bool(
            catalog_context.get("supporting_products")
            or catalog_context.get("target_category_name")
            or catalog_context.get("target_tag_name")
            or catalog_context.get("primary_taxonomy_name")
        )
        search_stage = self._infer_search_stage(combined_text, catalog_context, product_head)
        intent_signal = self.analyze_intent(keyword, related_keywords=related_keywords or [])

        commercial_score = 0.1
        traffic_score = 0.1
        reasons: List[str] = []

        commercial_hits = self._term_hits(combined_text, self.COMMERCIAL_TERMS)
        traffic_hits = self._term_hits(combined_text, self.TRAFFIC_TERMS)

        commercial_score += commercial_hits * 0.16
        traffic_score += traffic_hits * 0.12

        if intent_signal.intent == UserIntent.BUYING_GUIDE:
            commercial_score += 0.24
            reasons.append("intent=buying_guide")
        elif intent_signal.intent == UserIntent.COMPARISON:
            traffic_score += 0.22
            reasons.append("intent=comparison")
        elif intent_signal.intent in {UserIntent.PROBLEM_SOLVING, UserIntent.TECHNICAL_DEEP_DIVE, UserIntent.SPECIFICATION}:
            traffic_score += 0.18
            reasons.append(f"intent={intent_signal.intent.value}")

        if product_head:
            commercial_score += 0.22
            reasons.append("product_head_query")
        if catalog_support:
            commercial_score += 0.14
            reasons.append("catalog_support")

        page_type = str(catalog_context.get("page_type") or "")
        if page_type == "wholesale_faq":
            commercial_score += 0.16
            reasons.append("page_type=wholesale_faq")
        elif page_type in {"spec_comparison", "category_support", "product_selection"}:
            traffic_score += 0.06

        if search_stage == "decision":
            commercial_score += 0.2
            reasons.append("stage=decision")
        elif search_stage == "consideration":
            traffic_score += 0.12
            reasons.append("stage=consideration")
        else:
            traffic_score += 0.08
            reasons.append("stage=awareness")

        if product_head and catalog_support and commercial_score >= traffic_score - 0.12:
            lane = "procurement_conversion"
            reasons.append("product_head_default_to_procurement")
        elif commercial_score >= traffic_score:
            lane = "procurement_conversion"
        else:
            lane = "traffic_entry"

        confidence = min(0.95, 0.55 + abs(commercial_score - traffic_score) * 0.45)
        return ContentRouteSignal(
            keyword=keyword,
            content_lane=lane,
            confidence=round(confidence, 3),
            search_stage=search_stage,
            signal_scores={
                "commercial": round(commercial_score, 3),
                "traffic": round(traffic_score, 3),
                "product_head": 1.0 if product_head else 0.0,
                "catalog_support": 1.0 if catalog_support else 0.0,
            },
            reasons=reasons,
        )

    def generate_intent_based_title(self, intent_signal: IntentSignal) -> str:
        """Generate title based on actual user intent, not templates"""
        keyword = self._normalize_keyword(intent_signal.keyword)
        intent = intent_signal.intent
        context = intent_signal.semantic_context
        keyword_title = self._smart_title(keyword)
        primary_subject = self._extract_primary_subject(keyword)

        if intent == UserIntent.PROBLEM_SOLVING:
            problem = next((c for c in context if c in ["cracking", "issue", "failure"]), context[0] if context else "issue")
            condition = next((c for c in context if c in ["cold", "weather", "temperature"]), "")
            condition_text = f" in {condition.title()} Weather" if condition else ""
            if primary_subject:
                return f"{keyword_title}: Root Causes, Failure Triggers, and Prevention Steps"
            return f"Preventing {problem.title()}{condition_text}: Root Causes and Solutions"

        elif intent == UserIntent.COMPARISON:
            parts = re.split(r"\s+vs\s+|\s+versus\s+", keyword)
            if len(parts) == 2:
                material1, material2 = parts[0].strip(), parts[1].strip()
                use_case = " ".join([c for c in context if c not in material1.lower().split() + material2.lower().split()])
                if use_case:
                    return f"{self._smart_title(material1)} vs {self._smart_title(material2)} for {use_case.title()}: Performance, Cost, and Trade-Offs"
                return f"{self._smart_title(material1)} vs {self._smart_title(material2)}: Performance, Cost, and Use-Case Comparison"
            return f"{keyword_title}: Detailed Comparison and Selection Criteria"

        elif intent == UserIntent.SPECIFICATION:
            words = keyword.lower().split()
            material = self._smart_title(words[0]) if words else keyword_title
            prop_words = [w for w in words[1:] if w in ["chemical", "resistance", "properties", "strength"]]
            prop_phrase = " ".join(prop_words).title() if prop_words else "Properties"
            return f"{material} {prop_phrase}: Technical Data, Performance Limits, and Application Fit"

        elif intent == UserIntent.BUYING_GUIDE:
            if any(term in keyword for term in ["supplier", "manufacturer"]):
                return f"{keyword_title}: MOQ, Lead Time, Certifications, and Audit Questions"
            if "wholesale" in keyword or "bulk" in keyword:
                return f"{keyword_title}: Pricing Factors, MOQ, Quality Checks, and Supplier Shortlisting"
            if "choose" in keyword or "selection" in keyword:
                return f"{keyword_title}: Evaluation Criteria, Red Flags, and Quote Comparison"
            return f"{keyword_title}: Buyer Checklist, Cost Drivers, and Supplier Evaluation"

        elif intent == UserIntent.TECHNICAL_DEEP_DIVE:
            return f"{keyword_title}: Mechanisms, Test Methods, and Design Implications"

        return f"{keyword_title}: Technical Analysis and Decision Framework"

    def _normalize_keyword(self, keyword: str) -> str:
        """Normalize noisy keyword phrases without changing their meaning."""
        normalized = re.sub(r"[_-]+", " ", keyword.lower())
        normalized = re.sub(r"\s+", " ", normalized).strip(" :,-")
        return normalized

    def _term_hits(self, text: str, terms: set[str]) -> int:
        return sum(1 for term in terms if term in text)

    def _is_product_head_query(self, keyword: str) -> bool:
        return bool(self.PRODUCT_HEAD_PATTERN.search(keyword))

    def _infer_search_stage(
        self,
        text: str,
        catalog_context: Dict[str, object],
        product_head: bool,
    ) -> str:
        """Infer awareness / consideration / decision using deterministic term groups."""
        if any(term in text for term in self.DECISION_STAGE_TERMS):
            return "decision"
        if product_head and catalog_context.get("supporting_products"):
            return "decision"
        if any(term in text for term in self.CONSIDERATION_STAGE_TERMS):
            return "consideration"
        if any(term in text for term in self.AWARENESS_STAGE_TERMS):
            return "awareness"
        if product_head:
            return "decision"
        return "consideration"

    def _extract_primary_subject(self, keyword: str) -> str:
        """Extract the most likely product or material phrase."""
        parts = [part for part in re.split(r"\b(in|for|with|without|vs|versus)\b", keyword) if part]
        subject = parts[0].strip() if parts else keyword.strip()
        return subject

    def _smart_title(self, text: str) -> str:
        """Convert a keyword phrase to readable title case while preserving acronyms."""
        words = []
        for raw_word in text.split():
            upper_word = raw_word.upper()
            if upper_word in {"HDPE", "LDPE", "PET", "PVC", "MOQ", "FDA", "OEM", "ODM"}:
                words.append(upper_word)
            elif len(raw_word) <= 3 and raw_word.isupper():
                words.append(raw_word)
            else:
                words.append(raw_word.capitalize())
        return " ".join(words)

    def expand_semantic_keywords(self, keyword: str, max_expansions: int = 5) -> List[str]:
        """Expand keywords based on semantic context"""
        expanded = []
        keyword_lower = keyword.lower()

        for base_term, expansions in self.SEMANTIC_EXPANSIONS.items():
            if base_term.lower() in keyword_lower:
                for expansion in expansions[:max_expansions]:
                    expanded_kw = keyword_lower.replace(base_term.lower(), expansion)
                    if expanded_kw != keyword_lower:
                        expanded.append(expanded_kw)

        return expanded[:max_expansions]
