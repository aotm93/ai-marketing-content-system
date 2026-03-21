"""
Hook & Title Optimizer

Generates optimized titles with multiple hook types and CTR estimation.
"""

import logging
import random
from typing import List
from datetime import datetime

from src.models.content_intelligence import (
    ContentTopic, OptimizedTitle, HookType, ResearchResult
)
from src.services.content.intent_analyzer import SearchIntentAnalyzer, UserIntent
from src.services.content.title_matcher import TitleQueryMatcher

logger = logging.getLogger(__name__)


class HookOptimizer:
    """Generate optimized titles with multiple hook variants"""

    MIN_ACCEPTABLE_MATCH = 0.45
    GENERIC_PATTERNS = (
        "data-driven insights",
        "what you need to know",
        "ultimate guide",
        "top picks reviewed",
        "which is better?"
    )

    # CTR baseline estimates by hook type
    CTR_BASELINES = {
        HookType.DATA: 0.045,
        HookType.STORY: 0.052,
        HookType.PROBLEM: 0.048,
        HookType.QUESTION: 0.043,
        HookType.HOW_TO: 0.038,
        HookType.CONTROVERSY: 0.055
    }
    
    def __init__(self):
        self.title_templates = self._load_title_templates()
        self.intent_analyzer = SearchIntentAnalyzer()
        self.title_matcher = TitleQueryMatcher()
        logger.info("HookOptimizer initialized with SearchIntentAnalyzer and TitleQueryMatcher")
    
    def _load_title_templates(self) -> dict:
        """Load title templates by hook type"""
        return {
            HookType.DATA: [
                "{value}% of {subject} {action}: Here's What We Learned",
                "Study Reveals {value}% of {subject} {action}",
                "Data Shows {value}% {change} in {subject}",
                "The {value}% {metric} That Changes Everything",
                "Why {value}% of {subject} Are {action} (Data Analysis)"
            ],
            HookType.PROBLEM: [
                "The Hidden Cost of {problem}: A {industry} Analysis",
                "Why {problem} Is Costing You More Than You Think",
                "The {problem} Crisis: What {audience} Need to Know",
                "Are You Making This {problem} Mistake?",
                "How {problem} Is Hurting Your {metric}"
            ],
            HookType.HOW_TO: [
                "How to {solution} in {timeframe}: Step-by-Step Guide",
                "The Complete Guide to {solution} for {audience}",
                "How to {solution} Without {common_mistake}",
                "Master {solution}: {audience} Edition",
                "How We {achievement} Using {solution}"
            ],
            HookType.QUESTION: [
                "Is {misconception} Actually Hurting Your {metric}?",
                "Why Do {percentage} of {subject} Still {action}?",
                "Are You {action} The Right Way?",
                "What If {scenario} Could Transform Your {metric}?",
                "Is Your {subject} Ready for {change}?"
            ],
            HookType.STORY: [
                "How {company} {achievement} in Just {timeframe}",
                "The {company} Story: From {before} to {after}",
                "What {company} Taught Us About {topic}",
                "Inside {company}'s {achievement} Strategy",
                "How One {company} {achievement} Against All Odds"
            ],
            HookType.CONTROVERSY: [
                "Why {topic} Experts Disagree (And Who's Right)",
                "The {topic} Debate: {viewpoint1} vs {viewpoint2}",
                "Myth vs Reality: What You Know About {topic} Is Wrong",
                "Why We Stopped {common_practice} (And You Should Too)",
                "The Unpopular Truth About {topic}"
            ]
        }
    
    async def generate_optimized_titles(
        self,
        topic: ContentTopic,
        count: int = 5
    ) -> List[OptimizedTitle]:
        """
        Generate multiple title variants with CTR scoring
        
        Args:
            topic: The content topic
            count: Number of title variants to generate
            
        Returns:
            List of OptimizedTitle sorted by expected CTR
        """
        logger.info(f"Generating {count} optimized titles for: {topic.title}")
        
        variants = []
        research = topic.research_result
        
        # Generate one of each hook type up to count
        hook_types = list(HookType)[:count]
        
        for i, hook_type in enumerate(hook_types):
            title, rationale = self._generate_title_for_hook(topic, research, hook_type)
            expected_ctr = self._estimate_ctr(hook_type, topic, research)
            
            variant = OptimizedTitle(
                title=title,
                hook_type=hook_type,
                expected_ctr=expected_ctr,
                rationale=rationale,
                test_variant=chr(ord('A') + i)
            )
            variants.append(variant)
        
        # Sort by expected CTR (highest first)
        variants.sort(key=lambda x: x.expected_ctr, reverse=True)
        
        logger.info(f"Generated {len(variants)} title variants")
        return variants

    def generate_optimized_titles_sync(
        self,
        topic: ContentTopic,
        count: int = 5
    ) -> List[OptimizedTitle]:
        """Synchronous version for testing"""
        variants = []
        research = topic.research_result
        hook_types = list(HookType)[:count]

        for i, hook_type in enumerate(hook_types):
            title, rationale = self._generate_title_for_hook(topic, research, hook_type)
            expected_ctr = self._estimate_ctr(hook_type, topic, research)

            variant = OptimizedTitle(
                title=title,
                hook_type=hook_type,
                expected_ctr=expected_ctr,
                rationale=rationale,
                test_variant=chr(ord('A') + i)
            )
            variants.append(variant)

        variants.sort(key=lambda x: x.expected_ctr, reverse=True)
        return variants
    
    def _generate_title_for_hook(
        self,
        topic: ContentTopic,
        research: ResearchResult,
        hook_type: HookType
    ) -> tuple[str, str]:
        """Generate a title for a specific hook type using intent analysis"""
        intent_signal = self.intent_analyzer.analyze_intent(
            topic.title,
            related_keywords=[topic.angle] if topic.angle else []
        )

        # Use intent analyzer for PROBLEM and HOW_TO hooks
        if hook_type in [HookType.PROBLEM, HookType.HOW_TO]:
            title = self.intent_analyzer.generate_intent_based_title(intent_signal)
            rationale = f"Intent-based title for {intent_signal.intent.value} (confidence: {intent_signal.confidence:.0%})"
            return title, rationale

        # Use templates for DATA and other hooks
        templates = self.title_templates.get(hook_type, [])
        if not templates:
            return topic.title, "Fallback title"

        template = random.choice(templates)
        context = self._build_template_context(topic, research, hook_type)

        try:
            title = template.format(**context)
        except KeyError:
            title = self._generate_fallback_title(topic, hook_type, intent_signal)

        if self._should_replace_generated_title(title, topic.title):
            title = self._generate_fallback_title(topic, hook_type, intent_signal)
            rationale = (
                f"Keyword-anchored fallback for {hook_type.value} hook to preserve query intent "
                f"({intent_signal.intent.value}, confidence: {intent_signal.confidence:.0%})"
            )
            return title, rationale

        rationale = self._generate_rationale(hook_type, context)
        return title, rationale
    
    def _build_template_context(
        self,
        topic: ContentTopic,
        research: ResearchResult,
        hook_type: HookType
    ) -> dict:
        """Build context dictionary for title templates"""
        
        context = {
            'industry': topic.industry,
            'audience': topic.target_audience,
            'topic': topic.title,
            'metric': 'ROI' if topic.business_intent > 0.7 else 'performance',
            'timeframe': '30 days' if topic.estimated_difficulty == 'easy' else '6 months'
        }
        
        if hook_type == HookType.DATA and research and research.statistics:
            stat = research.statistics[0]
            context.update({
                'value': stat.get('value', '75'),
                'subject': stat.get('subject', topic.industry),
                'action': stat.get('action', 'are affected'),
                'change': stat.get('change', 'increase'),
                'metric': stat.get('metric', 'improvement')
            })
        
        elif hook_type == HookType.PROBLEM and research and research.pain_points:
            pain = research.pain_points[0]
            context.update({
                'problem': pain.category,
                'severity': f"{pain.severity:.0%}"
            })
        
        elif hook_type == HookType.HOW_TO:
            context.update({
                'solution': topic.angle or topic.title,
                'common_mistake': 'expensive trial and error',
                'achievement': 'doubled our results'
            })
        
        elif hook_type == HookType.QUESTION:
            context.update({
                'misconception': topic.angle or 'common practice',
                'percentage': '67',
                'subject': topic.industry,
                'action': 'struggle with this',
                'scenario': 'implementing this strategy',
                'change': 'the upcoming shift'
            })
        
        elif hook_type == HookType.STORY:
            context.update({
                'company': 'Industry Leader',
                'achievement': 'achieved 10x growth',
                'before': 'struggling',
                'after': 'thriving'
            })
        
        elif hook_type == HookType.CONTROVERSY:
            context.update({
                'viewpoint1': 'Traditional Approach',
                'viewpoint2': 'Modern Strategy',
                'common_practice': 'following the old playbook'
            })
        
        return context
    
    def _generate_fallback_title(
        self,
        topic: ContentTopic,
        hook_type: HookType,
        intent_signal=None
    ) -> str:
        """Generate a fallback title if template fails"""
        keyword_title = self.intent_analyzer.generate_intent_based_title(intent_signal) if intent_signal else topic.title
        fallbacks = {
            HookType.DATA: f"{self._keyword_title(topic.title)}: Cost, Performance Data, and Buyer Benchmarks",
            HookType.PROBLEM: keyword_title,
            HookType.HOW_TO: keyword_title,
            HookType.QUESTION: f"{self._keyword_title(topic.title)}: Key Questions, Trade-Offs, and Selection Criteria",
            HookType.STORY: f"{self._keyword_title(topic.title)}: Case Examples, Lessons, and Implementation Takeaways",
            HookType.CONTROVERSY: f"{self._keyword_title(topic.title)}: Common Assumptions, Risks, and Evidence-Based Trade-Offs"
        }
        return fallbacks.get(hook_type, topic.title)

    def _keyword_title(self, keyword: str) -> str:
        """Convert the raw keyword to a readable title while preserving acronyms."""
        words = []
        for raw_word in keyword.split():
            upper_word = raw_word.upper()
            if upper_word in {"HDPE", "LDPE", "PET", "PVC", "MOQ", "FDA", "OEM", "ODM"}:
                words.append(upper_word)
            else:
                words.append(raw_word.capitalize())
        return " ".join(words)

    def _should_replace_generated_title(self, title: str, keyword: str) -> bool:
        """Reject titles that are generic or weakly matched to the query."""
        title_lower = title.lower()
        if any(pattern in title_lower for pattern in self.GENERIC_PATTERNS):
            return True

        match_score = self.title_matcher.calculate_match_score(title, keyword)
        return match_score < self.MIN_ACCEPTABLE_MATCH
    
    def _generate_rationale(self, hook_type: HookType, context: dict) -> str:
        """Generate rationale for why this hook type works"""
        
        rationales = {
            HookType.DATA: f"Uses concrete data ({context.get('value', 'X')}%) to establish credibility and create urgency",
            HookType.PROBLEM: f"Addresses pain point ({context.get('problem', 'industry challenge')}) that resonates with target audience",
            HookType.HOW_TO: f"Promises actionable solution for {context.get('audience', 'readers')} seeking practical guidance",
            HookType.QUESTION: f"Creates curiosity gap about {context.get('misconception', 'common assumptions')}",
            HookType.STORY: f"Uses social proof and narrative to engage emotionally",
            HookType.CONTROVERSY: f"Challenges conventional wisdom to drive engagement through disagreement"
        }
        
        return rationales.get(hook_type, "Standard title format")
    
    def _estimate_ctr(
        self,
        hook_type: HookType,
        topic: ContentTopic,
        research: ResearchResult
    ) -> float:
        """
        Estimate expected CTR based on multiple factors
        
        Scoring factors:
        - Hook type baseline (base)
        - Business intent (+0.01 to +0.03)
        - Research quality/data available (+0.005 to +0.02)
        - Differentiation score (+0.005 to +0.015)
        """
        # Start with baseline
        base_ctr = self.CTR_BASELINES.get(hook_type, 0.04)
        
        # Adjust for business intent
        intent_boost = topic.business_intent * 0.02
        
        # Adjust for research quality
        research_score = 0
        if research:
            if research.statistics:
                research_score += 0.01
            if research.pain_points:
                research_score += 0.005
            if research.expert_quotes:
                research_score += 0.005
        
        # Adjust for differentiation
        differentiation_boost = topic.differentiation_score * 0.015
        
        # Calculate final CTR
        estimated_ctr = base_ctr + intent_boost + research_score + differentiation_boost
        
        # Cap at reasonable bounds
        estimated_ctr = max(0.02, min(0.08, estimated_ctr))
        
        return round(estimated_ctr, 4)
    
    async def select_best_title(
        self,
        variants: List[OptimizedTitle],
        strategy: str = "ctr",  # "ctr", "balanced", "experimental"
        target_keyword: str = None
    ) -> OptimizedTitle:
        """
        Select the best title based on strategy

        Args:
            variants: List of title variants
            strategy: Selection strategy (ctr, balanced, experimental)
            target_keyword: Optional keyword to match against

        Returns:
            The selected OptimizedTitle
        """
        if not variants:
            raise ValueError("No variants provided")

        scored_variants = []
        if target_keyword:
            for variant in variants:
                match_score = self.title_matcher.calculate_match_score(variant.title, target_keyword)
                effective_ctr = variant.expected_ctr * (1 + match_score * 0.2)
                if match_score < self.MIN_ACCEPTABLE_MATCH:
                    effective_ctr *= 0.6
                scored_variants.append((variant, effective_ctr, match_score))
        else:
            scored_variants = [(variant, variant.expected_ctr, 1.0) for variant in variants]

        eligible_variants = [
            item for item in scored_variants
            if item[2] >= self.MIN_ACCEPTABLE_MATCH
        ] or scored_variants

        if strategy == "ctr":
            # Pure CTR optimization
            return max(eligible_variants, key=lambda item: item[1])[0]

        elif strategy == "balanced":
            # Balance CTR with variety
            # Prefer data or problem hooks if CTR is close
            best_variant = max(eligible_variants, key=lambda item: item[1])

            for variant, effective_ctr, _ in eligible_variants:
                if variant.hook_type in [HookType.DATA, HookType.PROBLEM]:
                    if effective_ctr >= best_variant[1] * 0.95:
                        return variant

            return best_variant[0]

        elif strategy == "experimental":
            # Try less common hook types occasionally
            uncommon_hooks = [HookType.CONTROVERSY, HookType.STORY]
            for variant, _, _ in eligible_variants:
                if variant.hook_type in uncommon_hooks:
                    return variant
            return max(eligible_variants, key=lambda item: item[1])[0]
        
        else:
            return max(eligible_variants, key=lambda item: item[1])[0]
