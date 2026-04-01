"""
Hook & Title Optimizer

Generates optimized titles with multiple hook types and CTR estimation.
"""

import logging
import random
import re
from typing import List, Optional, Dict, Any
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
    MAX_SEO_TITLE_LENGTH = 68
    MAX_SUBJECT_WORDS = 8
    MIN_SUBJECT_LENGTH = 20
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

    COMMERCIAL_TITLE_TERMS = [
        "moq", "lead time", "sample", "samples", "supplier", "quote",
        "customization", "material", "capacity", "closure", "qc",
        "certifications", "audit", "checklist"
    ]
    KEY_SUBJECT_TERMS = {
        "bottle", "bottles", "jar", "jars", "container", "containers", "tube", "tubes",
        "spray", "pump", "foamer", "foam", "dropper", "lotion", "supplier", "wholesale",
        "manufacturer", "packaging"
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
        count: int = 5,
        catalog_context: Optional[Dict[str, Any]] = None
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
            title, rationale = self._generate_title_for_hook(topic, research, hook_type, catalog_context)
            expected_ctr = self._estimate_ctr(hook_type, topic, research, title, catalog_context)
            
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
        count: int = 5,
        catalog_context: Optional[Dict[str, Any]] = None
    ) -> List[OptimizedTitle]:
        """Synchronous version for testing"""
        variants = []
        research = topic.research_result
        hook_types = list(HookType)[:count]

        for i, hook_type in enumerate(hook_types):
            title, rationale = self._generate_title_for_hook(topic, research, hook_type, catalog_context)
            expected_ctr = self._estimate_ctr(hook_type, topic, research, title, catalog_context)

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
        hook_type: HookType,
        catalog_context: Optional[Dict[str, Any]] = None
    ) -> tuple[str, str]:
        """Generate a title for a specific hook type using intent analysis"""
        intent_signal = self.intent_analyzer.analyze_intent(
            topic.title,
            related_keywords=[topic.angle] if topic.angle else []
        )

        catalog_title = self._generate_catalog_anchored_title(
            topic=topic,
            hook_type=hook_type,
            intent_signal=intent_signal,
            catalog_context=catalog_context or {},
        )
        if catalog_title:
            title, rationale = catalog_title
            return self._finalize_title(title, topic.title), rationale

        # Use intent analyzer for PROBLEM and HOW_TO hooks
        if hook_type in [HookType.PROBLEM, HookType.HOW_TO]:
            title = self.intent_analyzer.generate_intent_based_title(intent_signal)
            rationale = f"Intent-based title for {intent_signal.intent.value} (confidence: {intent_signal.confidence:.0%})"
            return self._finalize_title(title, topic.title), rationale

        # Use templates for DATA and other hooks
        templates = self.title_templates.get(hook_type, [])
        if not templates:
            return topic.title, "Fallback title"

        template = random.choice(templates)
        context = self._build_template_context(topic, research, hook_type)

        try:
            title = template.format(**context)
        except KeyError:
            title = self._generate_fallback_title(topic, hook_type, research, intent_signal)

        if self._should_replace_generated_title(title, topic.title):
            title = self._generate_fallback_title(topic, hook_type, research, intent_signal)
            rationale = (
                f"Keyword-anchored fallback for {hook_type.value} hook to preserve query intent "
                f"({intent_signal.intent.value}, confidence: {intent_signal.confidence:.0%})"
            )
            return self._finalize_title(title, topic.title), rationale

        rationale = self._generate_rationale(hook_type, context)
        return self._finalize_title(title, topic.title), rationale

    def _finalize_title(self, title: str, keyword: str) -> str:
        """Normalize repetitive tokens and keep title length within SEO-friendly bounds."""
        cleaned = re.sub(r"\s+", " ", (title or "").strip())
        cleaned = self._remove_repeated_tokens(cleaned)

        if ":" in cleaned:
            subject, tail = cleaned.split(":", 1)
            subject = self._compact_subject(subject, keyword)
            tail = self._shorten_tail(tail)
            rebuilt = self._fit_colon_title(subject, tail, keyword)
        else:
            rebuilt = self._compact_subject(cleaned, keyword)

        rebuilt = self._strip_trailing_connectors(rebuilt)
        if len(rebuilt) > self.MAX_SEO_TITLE_LENGTH:
            rebuilt = self._truncate_title(rebuilt, self.MAX_SEO_TITLE_LENGTH)
        return self._strip_trailing_connectors(rebuilt)

    def _remove_repeated_tokens(self, text: str) -> str:
        """Remove repeated words like '30ml PET 30ml ...' while preserving useful connectors."""
        tokens = text.split()
        seen = set()
        keep_repeat = {"and", "&", "for", "to", "vs", "with", "or"}
        deduped = []
        for token in tokens:
            normalized = token.lower().strip(",.;:()[]{}")
            if normalized and normalized not in keep_repeat and normalized in seen:
                continue
            deduped.append(token)
            if normalized:
                seen.add(normalized)
        return " ".join(deduped)

    def _compact_subject(self, subject: str, keyword: str) -> str:
        """Prefer a compact keyword-led subject when the generated subject is bloated."""
        subject = subject.strip(" ,-")
        if len(subject.split()) <= self.MAX_SUBJECT_WORDS and len(subject) <= 44:
            return subject

        source = keyword or subject
        tokens = source.split()
        important = []
        fallback = []
        for token in tokens:
            normalized = token.lower().strip(",.;:()[]{}")
            if not normalized:
                continue
            if token not in fallback:
                fallback.append(token)
            if re.match(r"^\d+(?:\.\d+)?(?:ml|l|oz|g)$", normalized):
                important.append(token)
                continue
            if normalized.upper() in {"HDPE", "LDPE", "PET", "PVC", "MOQ", "FDA", "OEM", "ODM"}:
                important.append(token.upper())
                continue
            if normalized in self.KEY_SUBJECT_TERMS:
                important.append(token)

        compact_tokens = []
        for token in important + fallback:
            normalized = token.lower().strip(",.;:()[]{}")
            if normalized and normalized not in {t.lower().strip(",.;:()[]{}") for t in compact_tokens}:
                compact_tokens.append(token)
            if len(compact_tokens) >= self.MAX_SUBJECT_WORDS:
                break

        compact_subject = " ".join(compact_tokens) if compact_tokens else subject
        return self._keyword_title(compact_subject).strip()

    def _fit_colon_title(self, subject: str, tail: str, keyword: str) -> str:
        """Keep the differentiating tail intact by shrinking the subject first."""
        subject = self._strip_trailing_connectors(subject)
        tail = self._strip_trailing_connectors(tail)
        if not tail:
            return subject

        rebuilt = f"{subject}: {tail}"
        if len(rebuilt) <= self.MAX_SEO_TITLE_LENGTH:
            return rebuilt

        subject_budget = max(self.MIN_SUBJECT_LENGTH, self.MAX_SEO_TITLE_LENGTH - len(tail) - 2)
        subject = self._compact_subject_to_budget(subject, keyword, subject_budget)
        rebuilt = f"{subject}: {tail}"
        if len(rebuilt) <= self.MAX_SEO_TITLE_LENGTH:
            return rebuilt

        tail_budget = max(18, self.MAX_SEO_TITLE_LENGTH - len(subject) - 2)
        tail = self._shorten_tail(tail, max_length=tail_budget)
        rebuilt = f"{subject}: {tail}" if tail else subject

        if len(rebuilt) > self.MAX_SEO_TITLE_LENGTH:
            rebuilt = self._truncate_title(rebuilt, self.MAX_SEO_TITLE_LENGTH)
        return rebuilt

    def _compact_subject_to_budget(self, subject: str, keyword: str, max_length: int) -> str:
        """Shrink long product subjects before sacrificing the title tail."""
        if len(subject) <= max_length:
            return subject

        source = keyword or subject
        tokens = []
        for raw_token in source.split():
            normalized = raw_token.lower().strip(",.;:()[]{}")
            if not normalized:
                continue
            if normalized in {"white", "black", "clear", "empty", "container", "containers"}:
                continue
            if normalized not in {item.lower().strip(",.;:()[]{}") for item in tokens}:
                tokens.append(raw_token)

        compact_tokens = []
        for token in tokens:
            candidate = self._keyword_title(" ".join(compact_tokens + [token])).strip()
            if compact_tokens and len(candidate) > max_length:
                break
            compact_tokens.append(token)

        if compact_tokens:
            subject = self._keyword_title(" ".join(compact_tokens)).strip()

        if len(subject) > max_length:
            subject = self._truncate_title(subject, max_length)
        return subject

    def _shorten_tail(self, tail: str, max_length: int = 34) -> str:
        """Compress long tails so titles stay readable in SERP snippets."""
        shortcuts = {
            "Buyer Benchmarks": "Buyer Checks",
            "Selection Criteria": "Selection Guide",
            "Supplier Questions": "Supplier Checks",
            "Performance Data": "Performance",
            "The Questions Buyers Should Ask": "Buyer Questions",
            "Common Buying Mistakes": "Buying Mistakes",
            "Supplier Mistakes To Avoid": "Supplier Risks",
            "Supplier Mistakes to Avoid": "Supplier Risks",
            "Trade-Offs": "Tradeoffs",
        }
        tail_text = self._remove_repeated_tokens(tail.strip(" ,-"))
        for source, target in shortcuts.items():
            tail_text = tail_text.replace(source, target)

        tail_lower = tail_text.lower()
        if "moq" in tail_lower and "lead time" in tail_lower:
            if "question" in tail_lower:
                tail_text = "MOQ, Lead Time, Buyer Questions"
            elif "risk" in tail_lower or "mistake" in tail_lower:
                tail_text = "MOQ, Lead Time, Supplier Risks"
            elif "lesson" in tail_lower:
                tail_text = "MOQ, Lead Time, Buyer Lessons"
            elif "ordering" in tail_lower or "sample" in tail_lower or "step" in tail_lower:
                tail_text = "MOQ, Lead Time, Ordering Steps"
            elif "claim" in tail_lower:
                tail_text = "MOQ, Lead Time, Supplier Claims"
            else:
                tail_text = "MOQ, Lead Time, Buyer Checks"

        segments = [segment.strip() for segment in tail_text.split(",") if segment.strip()]
        if len(segments) > 3:
            segments = segments[:3]
        compact = ", ".join(segments)

        if "buyer checks" in compact.lower() and len(compact) > max_length:
            essentials = []
            if "moq" in compact.lower():
                essentials.append("MOQ")
            if "lead time" in compact.lower():
                essentials.append("Lead Time")
            essentials.append("Buyer Checks")
            compact = ", ".join(essentials)

        if len(compact) > max_length:
            compact = self._truncate_title(compact, max_length)
        return self._strip_trailing_connectors(compact)

    def _truncate_title(self, title: str, max_length: int) -> str:
        """Trim title at word boundaries and avoid punctuation tails."""
        if len(title) <= max_length:
            return self._strip_trailing_connectors(title)
        trimmed = title[:max_length].rsplit(" ", 1)[0].strip(",;:- ")
        trimmed = trimmed or title[:max_length].strip(",;:- ")
        return self._strip_trailing_connectors(trimmed)

    def _strip_trailing_connectors(self, text: str) -> str:
        """Remove dangling trailing joiners left behind by aggressive shortening."""
        cleaned = (text or "").strip(" ,;:-")
        while cleaned:
            updated = re.sub(r"(?:\s+(?:and|or|for|to|with|vs))$", "", cleaned, flags=re.IGNORECASE).strip(" ,;:-")
            if updated == cleaned:
                break
            cleaned = updated
        return cleaned

    def _generate_catalog_anchored_title(
        self,
        topic: ContentTopic,
        hook_type: HookType,
        intent_signal,
        catalog_context: Dict[str, Any],
    ) -> Optional[tuple[str, str]]:
        """Generate titles anchored to category/product/buyer context."""
        if not catalog_context:
            return None

        page_type = catalog_context.get("page_type")
        target_category = catalog_context.get("target_category_name")
        target_tag = catalog_context.get("target_tag_name")
        primary_target = (
            catalog_context.get("primary_taxonomy_name")
            or target_category
            or target_tag
        )
        supporting_products = catalog_context.get("supporting_products") or []
        decision_questions = catalog_context.get("decision_questions") or []

        subject = self._keyword_title(topic.title)
        category_title = self._keyword_title(primary_target) if primary_target else None
        product = supporting_products[0] if supporting_products else {}
        product_name = self._keyword_title(product.get("name", "")) if product.get("name") else None
        spec_terms = self._extract_spec_terms(product, topic.title)
        buyer_angle = self._derive_buyer_angle(decision_questions, page_type)
        hook_tail = self._catalog_tail_for_hook(hook_type, page_type, buyer_angle, spec_terms)

        if page_type == "wholesale_faq":
            title = f"{subject}: {hook_tail}"
            return title, "Catalog-backed wholesale FAQ title using supplier decision criteria"

        if page_type == "product_selection":
            if category_title:
                title = f"{subject} for {category_title}: {hook_tail}"
            else:
                title = f"{subject}: {hook_tail}"
            return title, "Catalog-backed product selection title using category fit and buyer criteria"

        if page_type == "spec_comparison":
            title = f"{subject}: {hook_tail}"
            return title, "Catalog-backed comparison title emphasizing specs and trade-offs"

        if page_type == "category_support":
            focus = hook_tail
            if category_title and category_title.lower() not in subject.lower():
                title = f"{category_title}: {focus}"
            else:
                title = f"{subject}: {focus}"
            return title, "Catalog-backed category support title aligned to browsing and shortlist intent"

        if product_name and hook_type in {HookType.DATA, HookType.QUESTION}:
            title = f"{subject}: {hook_tail}"
            return title, "Catalog-backed commercial title using product example and buyer questions"

        return None

    def _catalog_tail_for_hook(
        self,
        hook_type: HookType,
        page_type: Optional[str],
        buyer_angle: Optional[str],
        spec_terms: Optional[str],
    ) -> str:
        """Choose a hook-sensitive tail for catalog-backed titles."""
        defaults = {
            "wholesale_faq": {
                HookType.DATA: "MOQ, Lead Time, and Buyer Checks",
                HookType.PROBLEM: "MOQ, Lead Time, and Supplier Mistakes to Avoid",
                HookType.HOW_TO: "Samples, MOQ, and Ordering Steps",
                HookType.QUESTION: "Supplier Checks, MOQ, and Lead Time",
                HookType.STORY: "Buyer Lessons, MOQ, and Ordering Risks",
                HookType.CONTROVERSY: "Supplier Claims, MOQ, and Real Tradeoffs",
            },
            "product_selection": {
                HookType.DATA: "Material, Capacity, and Closure Fit",
                HookType.PROBLEM: "Selection Mistakes, Fit Risks, and Better Options",
                HookType.HOW_TO: "Material, Capacity, and Closure Selection",
                HookType.QUESTION: "Which Specs Fit, and Which Ones Fail?",
                HookType.STORY: "Buyer Lessons, Fit Risks, and Selection Criteria",
                HookType.CONTROVERSY: "Assumptions, Fit Risks, and Better Criteria",
            },
            "spec_comparison": {
                HookType.DATA: "Specs, Performance, and Buyer Tradeoffs",
                HookType.PROBLEM: "Spec Risks, Tradeoffs, and Selection Mistakes",
                HookType.HOW_TO: "Spec Comparison and Selection Criteria",
                HookType.QUESTION: "Which Spec Wins for Performance, Cost, and Fit?",
                HookType.STORY: "Comparison Lessons, Fit Risks, and Buyer Takeaways",
                HookType.CONTROVERSY: "Spec Assumptions and Real Tradeoffs",
            },
            "category_support": {
                HookType.DATA: "Product Types, Material Options, and Buyer Checks",
                HookType.PROBLEM: "Selection Mistakes, Category Gaps, and Better Options",
                HookType.HOW_TO: "Product Types, Material Options, and Buyer Checklist",
                HookType.QUESTION: "Which Options Fit Your Product and Budget?",
                HookType.STORY: "Buyer Lessons, Shortlisting Tips, and Better Options",
                HookType.CONTROVERSY: "Category Assumptions and Better Buying Criteria",
            },
        }

        page_defaults = defaults.get(page_type or "", {})
        fallback = buyer_angle or spec_terms or "Buyer Checklist and Selection Criteria"

        if hook_type == HookType.DATA and buyer_angle:
            return f"{buyer_angle} and Buyer Checks"
        if hook_type == HookType.PROBLEM and buyer_angle:
            return f"{buyer_angle} and Supplier Risks"
        if hook_type == HookType.QUESTION and buyer_angle:
            return f"{buyer_angle} and Buyer Questions"
        if hook_type == HookType.HOW_TO and buyer_angle:
            return f"{buyer_angle} and Ordering Steps"
        if hook_type == HookType.STORY and buyer_angle:
            return f"{buyer_angle} and Buyer Lessons"
        if hook_type == HookType.CONTROVERSY and buyer_angle:
            return f"{buyer_angle} and Supplier Claims"

        return page_defaults.get(hook_type, fallback)

    def _extract_spec_terms(self, product: Dict[str, Any], topic_title: str) -> Optional[str]:
        """Build a short spec-focused tail from product or topic context."""
        terms = []
        for key in ("capacity", "material", "closure_type", "neck_finish"):
            value = product.get(key)
            if value:
                normalized = self._keyword_title(str(value))
                if normalized not in terms:
                    terms.append(normalized)

        topic_lower = topic_title.lower()
        if "moq" in topic_lower and "MOQ" not in terms:
            terms.append("MOQ")
        if "lead time" in topic_lower and "Lead Time" not in terms:
            terms.append("Lead Time")

        if len(terms) >= 3:
            return ", ".join(terms[:3]) + ", and Fit"
        if len(terms) == 2:
            return f"{terms[0]}, {terms[1]}, and Buyer Fit"
        if len(terms) == 1:
            return f"{terms[0]} and Buying Fit"
        return None

    def _derive_buyer_angle(self, decision_questions: List[str], page_type: Optional[str]) -> Optional[str]:
        """Compress mapped buyer questions into title-friendly angle text."""
        if not decision_questions:
            defaults = {
                "wholesale_faq": "MOQ, Lead Time, Samples, and Customization",
                "product_selection": "Material, Capacity, and Closure Selection",
                "spec_comparison": "Specs, Trade-Offs, and Selection Criteria",
                "category_support": "Product Types, Material Options, and Buyer Checklist",
            }
            return defaults.get(page_type or "")

        question_text = " ".join(decision_questions).lower()
        parts = []
        if "moq" in question_text:
            parts.append("MOQ")
        if "lead time" in question_text:
            parts.append("Lead Time")
        if "sample" in question_text:
            parts.append("Samples")
        if "certification" in question_text or "compliance" in question_text:
            parts.append("Certifications")
        if "closure" in question_text or "neck finish" in question_text:
            parts.append("Closure Fit")
        if "material" in question_text:
            parts.append("Material Selection")
        if "capacity" in question_text:
            parts.append("Capacity Fit")
        if "supplier" in question_text or "audit" in question_text:
            parts.append("Supplier Checks")

        if not parts:
            return None
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return f"{parts[0]} and {parts[1]}"
        return ", ".join(parts[:2]) + f", and {parts[2]}"
    
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
        research: Optional[ResearchResult] = None,
        intent_signal=None
    ) -> str:
        """Generate a fallback title if template fails"""
        keyword_title = self.intent_analyzer.generate_intent_based_title(intent_signal) if intent_signal else topic.title
        data_fallback = f"{self._keyword_title(topic.title)}: Cost, Performance, and Buyer Checks"
        if hook_type == HookType.DATA and research and research.statistics:
            stat = research.statistics[0]
            stat_value = stat.get("value")
            stat_subject = self._keyword_title(str(stat.get("subject", "buyers")))
            stat_metric = self._keyword_title(str(stat.get("metric", "performance")))
            if stat_value is not None:
                data_fallback = f"{self._keyword_title(topic.title)}: {stat_value}% of {stat_subject} Report {stat_metric}"

        fallbacks = {
            HookType.DATA: data_fallback,
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
        research: ResearchResult,
        title: Optional[str] = None,
        catalog_context: Optional[Dict[str, Any]] = None
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

        commercial_boost = 0
        if title:
            title_lower = title.lower()
            commercial_signal_count = sum(1 for term in self.COMMERCIAL_TITLE_TERMS if term in title_lower)
            commercial_boost += min(0.012, commercial_signal_count * 0.003)

        if catalog_context:
            if catalog_context.get("target_category_name"):
                commercial_boost += 0.003
            if catalog_context.get("target_tag_name"):
                commercial_boost += 0.003
            if catalog_context.get("supporting_products"):
                commercial_boost += 0.004
            if catalog_context.get("decision_questions"):
                commercial_boost += 0.003

        # Calculate final CTR
        estimated_ctr = base_ctr + intent_boost + research_score + differentiation_boost + commercial_boost
        
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
