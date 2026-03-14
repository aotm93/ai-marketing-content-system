"""
Search Intent Analyzer
Analyzes real user search intent from keywords to generate meaningful content
"""

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
        keyword_lower = keyword.lower()
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

        context = [word for word in keyword_lower.split() if len(word) > 3]

        return IntentSignal(
            keyword=keyword,
            intent=intent,
            confidence=confidence,
            semantic_context=context
        )

    def generate_intent_based_title(self, intent_signal: IntentSignal) -> str:
        """Generate title based on actual user intent, not templates"""
        keyword = intent_signal.keyword
        intent = intent_signal.intent
        context = intent_signal.semantic_context

        if intent == UserIntent.PROBLEM_SOLVING:
            problem = next((c for c in context if c in ["cracking", "issue", "failure"]), context[0] if context else "issue")
            condition = next((c for c in context if c in ["cold", "weather", "temperature"]), "")
            condition_text = f" in {condition.title()} Weather" if condition else ""
            return f"Preventing {problem.title()}{condition_text} in {keyword.split()[0].upper()}: Root Causes and Solutions"

        elif intent == UserIntent.COMPARISON:
            parts = keyword.split(" vs ")
            if len(parts) == 2:
                material1, rest = parts[0], parts[1]
                material2 = rest.split()[0]
                use_case = " ".join([c for c in context if c not in [material1.lower(), material2.lower()]])
                return f"{material1.upper()} vs {material2.upper()} for {use_case.title()}: Performance Analysis"
            return f"{keyword}: Detailed Comparison"

        elif intent == UserIntent.SPECIFICATION:
            words = keyword.lower().split()
            material = words[0].upper()
            prop_words = [w for w in words[1:] if w in ["chemical", "resistance", "properties", "strength"]]
            prop_phrase = " ".join(prop_words).title() if prop_words else "Properties"
            return f"{material} {prop_phrase}: Technical Data and Performance Metrics"

        return f"{keyword}: Technical Analysis"

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
