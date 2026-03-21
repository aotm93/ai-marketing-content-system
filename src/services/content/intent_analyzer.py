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


class SearchIntentAnalyzer:
    """Analyzes search intent from keywords"""

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
