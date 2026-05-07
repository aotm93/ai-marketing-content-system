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
from src.services.content.content_policy import has_generic_procurement_tail, title_quality_penalty

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
        "which is better?",
        "moq, lead time, supplier",
        "moq, lead time, and supplier",
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
    PROCUREMENT_SIGNALS = {
        "supplier", "suppliers", "moq", "lead time", "sample", "samples",
        "audit", "quote", "quotes", "qc", "quality", "quality control",
        "customization", "certification", "certifications", "shipment", "packaging"
    }
    TRAFFIC_SIGNALS = {
        "vs", "versus", "application", "applications", "material", "materials",
        "problem", "problems", "risk", "risks", "fit", "selection", "choose",
        "comparison", "compare", "tradeoff", "tradeoffs", "use case", "use cases"
    }
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
        rebuilt = self._strip_trailing_connectors(rebuilt)
        if has_generic_procurement_tail(rebuilt):
            subject = rebuilt.split(":", 1)[0].strip()
            rebuilt = self._fit_colon_title(subject, "MOQ and Lead Time Risks", keyword)
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
            "Supplier Benchmarks": "Supplier Benchmarks",
            "Selection Criteria": "Selection Signals",
            "Supplier Questions": "Quote Questions",
            "Performance Data": "Performance",
            "The Questions Buyers Should Ask": "Buyer Questions",
            "Common Buying Mistakes": "Buying Mistakes",
            "Supplier Mistakes To Avoid": "Supplier Risks",
            "Supplier Mistakes to Avoid": "Supplier Risks",
            "Trade-Offs": "Tradeoffs",
            "Hidden Tradeoffs": "Tradeoffs",
            "Selection Logic": "Selection Logic",
        }
        tail_text = self._remove_repeated_tokens(tail.strip(" ,-"))
        for source, target in shortcuts.items():
            tail_text = tail_text.replace(source, target)

        segments = [segment.strip() for segment in tail_text.split(",") if segment.strip()]
        if len(segments) > 3:
            segments = segments[:3]
        compact = ", ".join(segments)

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
        content_lane = catalog_context.get("content_lane", "procurement_conversion")
        search_stage = catalog_context.get("search_stage")
        serp_role = catalog_context.get("serp_role")

        subject = self._keyword_title(topic.title)
        category_title = self._keyword_title(primary_target) if primary_target else None
        product = supporting_products[0] if supporting_products else {}
        product_name = self._keyword_title(product.get("name", "")) if product.get("name") else None
        spec_terms = self._extract_spec_terms(product, topic.title)
        buyer_angle = self._derive_buyer_angle(decision_questions, page_type)
        hook_tail = self._catalog_tail_for_hook(
            hook_type,
            page_type,
            buyer_angle,
            spec_terms,
            content_lane,
            search_stage,
            topic.title,
            serp_role,
        )

        if page_type == "wholesale_faq":
            title = f"{subject}: {hook_tail}"
            rationale = "Lane-aware wholesale title using supplier criteria" if content_lane == "procurement_conversion" else "Lane-aware search-entry title using scenario-driven framing"
            return title, rationale

        if page_type == "product_selection":
            if category_title:
                title = f"{subject} for {category_title}: {hook_tail}"
            else:
                title = f"{subject}: {hook_tail}"
            rationale = "Lane-aware product selection title aligned to scenario fit and buyer criteria"
            return title, rationale

        if page_type == "spec_comparison":
            title = f"{subject}: {hook_tail}"
            rationale = "Lane-aware comparison title emphasizing trade-offs or buying criteria"
            return title, rationale

        if page_type == "category_support":
            focus = hook_tail
            category_subject_score = (
                self.title_matcher.calculate_match_score(category_title, topic.title)
                if category_title
                else 0.0
            )
            if category_title and category_title.lower() not in subject.lower() and category_subject_score >= 0.6:
                title = f"{category_title}: {focus}"
            else:
                title = f"{subject}: {focus}"
            rationale = "Lane-aware category support title aligned to browsing or shortlist intent"
            return title, rationale

        if product_name and hook_type in {HookType.DATA, HookType.QUESTION}:
            title = f"{subject}: {hook_tail}"
            rationale = "Lane-aware product title using route-specific decision framing"
            return title, rationale

        return None

    def _catalog_tail_for_hook(
        self,
        hook_type: HookType,
        page_type: Optional[str],
        buyer_angle: Optional[str],
        spec_terms: Optional[str],
        content_lane: str,
        search_stage: Optional[str],
        topic_title: str,
        serp_role: Optional[str],
    ) -> str:
        """Choose a hook-sensitive tail for catalog-backed titles."""
        procurement_defaults = {
            "wholesale_faq": {
                HookType.DATA: "Supplier Benchmarks, MOQ Drivers, and Packaging Specs",
                HookType.PROBLEM: "Supplier Risks, Sample Delays, and QC Gaps",
                HookType.HOW_TO: "Supplier Shortlisting, Sampling Steps, and Quote Checks",
                HookType.QUESTION: "Which Supplier Checks, MOQ Terms, and Lead-Time Risks Matter?",
                HookType.STORY: "Buyer Lessons, Quote Gaps, and Sampling Risks",
                HookType.CONTROVERSY: "Low MOQ Claims, Hidden Costs, and Audit Tradeoffs",
            },
            "product_selection": {
                HookType.DATA: "Specification Checks, MOQ Drivers, and Supplier Fit",
                HookType.PROBLEM: "Selection Risks, Spec Mismatch, and QC Gaps",
                HookType.HOW_TO: "Supplier Evaluation, Sample Steps, and Shortlist Criteria",
                HookType.QUESTION: "Which Specs, Supplier Terms, and Sampling Rules Matter?",
                HookType.STORY: "Buyer Lessons, Spec Gaps, and Supplier Tradeoffs",
                HookType.CONTROVERSY: "Spec Assumptions, Hidden Costs, and Better Criteria",
            },
            "spec_comparison": {
                HookType.DATA: "Comparison Benchmarks, Supplier Risks, and Buying Thresholds",
                HookType.PROBLEM: "Spec Risks, Cost Gaps, and Shortlist Mistakes",
                HookType.HOW_TO: "Comparison Criteria, Sample Checks, and Quote Variables",
                HookType.QUESTION: "Which Spec Wins for Cost, Lead Time, and Supplier Fit?",
                HookType.STORY: "Comparison Lessons, QC Risks, and Buyer Takeaways",
                HookType.CONTROVERSY: "Spec Assumptions, Hidden Costs, and Real Tradeoffs",
            },
            "category_support": {
                HookType.DATA: "Range Benchmarks, Supplier Filters, and Shortlist Criteria",
                HookType.PROBLEM: "Selection Mistakes, Supplier Gaps, and Better Options",
                HookType.HOW_TO: "Shortlisting Steps, Supplier Checks, and Sample Planning",
                HookType.QUESTION: "Which Options Fit Your Product, MOQ, and Supplier Needs?",
                HookType.STORY: "Buyer Lessons, Shortlisting Tips, and Sampling Risks",
                HookType.CONTROVERSY: "Category Assumptions, Hidden Costs, and Better Criteria",
            },
        }
        traffic_defaults = {
            "wholesale_faq": {
                HookType.DATA: "Use Cases, Packaging Constraints, and Selection Signals",
                HookType.PROBLEM: "Application Risks, Fit Gaps, and Better Scenarios",
                HookType.HOW_TO: "Use-Case Fit, Material Choice, and Selection Steps",
                HookType.QUESTION: "Which Packaging Option Fits Your Formula and Usage?",
                HookType.STORY: "Scenario Lessons, Fit Gaps, and Better Options",
                HookType.CONTROVERSY: "Common Assumptions, Fit Risks, and Better Criteria",
            },
            "product_selection": {
                HookType.DATA: "Material Fit, Closure Match, and Use-Case Triggers",
                HookType.PROBLEM: "Mismatch Risks, Use-Case Gaps, and Better Options",
                HookType.HOW_TO: "Application Fit, Material Choice, and Selection Logic",
                HookType.QUESTION: "Which Specs Fit the Formula, Closure, and Usage?",
                HookType.STORY: "Use-Case Lessons, Fit Risks, and Better Options",
                HookType.CONTROVERSY: "Selection Assumptions, Fit Risks, and Better Criteria",
            },
            "spec_comparison": {
                HookType.DATA: "Performance Tradeoffs, Application Fit, and Selection Signals",
                HookType.PROBLEM: "Failure Risks, Fit Gaps, and Comparison Mistakes",
                HookType.HOW_TO: "Comparison Logic, Material Fit, and Use-Case Selection",
                HookType.QUESTION: "Which Spec Wins for Stability, Fit, and Formula Needs?",
                HookType.STORY: "Comparison Lessons, Fit Risks, and Scenario Takeaways",
                HookType.CONTROVERSY: "Spec Assumptions, Use-Case Gaps, and Better Criteria",
            },
            "category_support": {
                HookType.DATA: "Application Paths, Material Choices, and Fit Signals",
                HookType.PROBLEM: "Selection Mistakes, Fit Risks, and Better Scenarios",
                HookType.HOW_TO: "Application Fit, Material Choice, and Product Selection",
                HookType.QUESTION: "Which Option Fits Your Formula, Package, and Usage?",
                HookType.STORY: "Scenario Lessons, Shortlisting Signals, and Better Options",
                HookType.CONTROVERSY: "Category Assumptions, Fit Risks, and Better Criteria",
            },
        }

        if content_lane == "procurement_conversion":
            return self._procurement_tail_for_hook(
                hook_type=hook_type,
                page_type=page_type,
                buyer_angle=buyer_angle,
                spec_terms=spec_terms,
                defaults=procurement_defaults,
                serp_role=serp_role,
            )
        return self._traffic_tail_for_hook(
            hook_type=hook_type,
            page_type=page_type,
            spec_terms=spec_terms,
            defaults=traffic_defaults,
            search_stage=search_stage,
            topic_title=topic_title,
            serp_role=serp_role,
        )

    def _procurement_tail_for_hook(
        self,
        hook_type: HookType,
        page_type: Optional[str],
        buyer_angle: Optional[str],
        spec_terms: Optional[str],
        defaults: Dict[str, Dict[HookType, str]],
        serp_role: Optional[str],
    ) -> str:
        page_defaults = defaults.get(page_type or "", {})
        role_defaults = {
            "supplier_evaluation": {
                HookType.DATA: "Supplier Fit, Quote Checks, and Audit Signals",
                HookType.PROBLEM: "Supplier Risks, Red Flags, and Audit Gaps",
                HookType.HOW_TO: "Supplier Shortlisting, Quote Review, and Audit Steps",
                HookType.QUESTION: "Which Supplier Checks, Quote Terms, and Audit Questions Matter?",
            },
            "procurement_faq": {
                HookType.DATA: "MOQ, Lead Time, and Buying Questions",
                HookType.PROBLEM: "MOQ Gaps, Sample Risks, and Shipping Delays",
                HookType.HOW_TO: "MOQ Checks, Sample Steps, and Procurement Criteria",
                HookType.QUESTION: "Which MOQ, Lead-Time, and Sampling Questions Matter?",
            },
        }
        base = buyer_angle or spec_terms
        if base:
            base_lower = base.lower()
            if "moq" in base_lower and "lead time" in base_lower:
                compact = {
                    HookType.DATA: "MOQ, Lead Time, Supplier Benchmarks",
                    HookType.PROBLEM: "MOQ, Lead Time, Buying Risks",
                    HookType.HOW_TO: "MOQ, Samples, Supplier Shortlisting",
                    HookType.QUESTION: "MOQ, Lead Time, Buyer Questions",
                    HookType.STORY: "MOQ, Samples, Buyer Lessons",
                    HookType.CONTROVERSY: "MOQ, Lead Time, Hidden Tradeoffs",
                }
                return compact.get(hook_type, "MOQ, Lead Time, Supplier Fit")
            mappings = {
                HookType.DATA: "Supplier Benchmarks",
                HookType.PROBLEM: "Buying Risks",
                HookType.HOW_TO: "Supplier Shortlisting",
                HookType.QUESTION: "Quote Questions",
                HookType.STORY: "Buyer Lessons",
                HookType.CONTROVERSY: "Hidden Tradeoffs",
            }
            return f"{base} and {mappings.get(hook_type, 'Buyer Criteria')}"
        if serp_role in role_defaults:
            return role_defaults[serp_role].get(hook_type, "Supplier Fit, Quote Checks, and Buying Criteria")
        return page_defaults.get(hook_type, "Supplier Fit, Quote Checks, and Buying Criteria")

    def _traffic_tail_for_hook(
        self,
        hook_type: HookType,
        page_type: Optional[str],
        spec_terms: Optional[str],
        defaults: Dict[str, Dict[HookType, str]],
        search_stage: Optional[str],
        topic_title: str,
        serp_role: Optional[str],
    ) -> str:
        role_defaults = {
            "material_comparison": {
                HookType.DATA: "Material Tradeoffs, Formula Fit, and Selection Signals",
                HookType.PROBLEM: "Material Risks, Compatibility Gaps, and Better Options",
                HookType.HOW_TO: "Material Comparison, Compatibility, and Selection Logic",
                HookType.QUESTION: "Which Material Fits Stability, Feel, and Packaging Needs?",
            },
            "application_fit": {
                HookType.DATA: "Application Fit, Material Choice, and Selection Signals",
                HookType.PROBLEM: "Use-Case Risks, Fit Gaps, and Better Options",
                HookType.HOW_TO: "Application Fit, Use Cases, and Selection Logic",
                HookType.QUESTION: "Which Option Fits the Formula, Usage, and Packaging Goal?",
            },
            "spec_selection": {
                HookType.DATA: "Capacity, Closure Fit, and Selection Signals",
                HookType.PROBLEM: "Spec Mismatch Risks, Fit Gaps, and Better Options",
                HookType.HOW_TO: "Spec Selection, Capacity Fit, and Closure Logic",
                HookType.QUESTION: "Which Specs Fit Capacity, Closure, and Usage Needs?",
            },
            "problem_risk": {
                HookType.DATA: "Failure Risks, Fit Gaps, and Decision Signals",
                HookType.PROBLEM: "Leak Risks, Mismatch Problems, and Better Choices",
                HookType.HOW_TO: "Risk Checks, Mismatch Prevention, and Selection Logic",
                HookType.QUESTION: "Which Risks Matter Before You Shortlist This Option?",
            },
        }
        if serp_role in role_defaults:
            return role_defaults[serp_role].get(hook_type, "Application Fit, Material Choice, and Selection Logic")
        page_defaults = defaults.get(page_type or "", {})
        search_angle = self._derive_search_angle(topic_title, spec_terms, page_type, search_stage)
        if search_angle:
            mappings = {
                HookType.DATA: "Selection Signals",
                HookType.PROBLEM: "Fit Risks",
                HookType.HOW_TO: "Selection Logic",
                HookType.QUESTION: "Use-Case Questions",
                HookType.STORY: "Scenario Lessons",
                HookType.CONTROVERSY: "Tradeoffs",
            }
            return f"{search_angle} and {mappings.get(hook_type, 'Use-Case Fit')}"
        return page_defaults.get(hook_type, "Application Fit, Material Choice, and Selection Logic")

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

    def _derive_search_angle(
        self,
        topic_title: str,
        spec_terms: Optional[str],
        page_type: Optional[str],
        search_stage: Optional[str],
    ) -> Optional[str]:
        """Build a search-oriented angle for traffic-entry titles."""
        title_lower = topic_title.lower()
        parts = []

        if " vs " in f" {title_lower} " or " versus " in f" {title_lower} ":
            parts.extend(["Material Tradeoffs", "Use-Case Fit"])
        if any(term in title_lower for term in ["application", "applications", "for "]):
            parts.append("Application Fit")
        if any(term in title_lower for term in ["material", "glass", "pet", "hdpe", "pp"]):
            parts.append("Material Choice")
        if any(term in title_lower for term in ["problem", "risk", "mistake", "leak", "mismatch", "compatib"]):
            parts.append("Failure Risks")
        if any(term in title_lower for term in ["essential oil", "serum", "formula", "filling", "usage"]):
            parts.append("Formula Match")
        if spec_terms and "MOQ" not in spec_terms:
            parts.append(spec_terms.replace(" and Buying Fit", "").replace(", and Fit", ""))
        if search_stage == "awareness" and "Failure Risks" not in parts:
            parts.append("Failure Risks")
        if search_stage == "decision" and "Selection Signals" not in parts:
            parts.append("Selection Signals")

        if not parts:
            defaults = {
                "category_support": "Application Fit, Material Choice",
                "product_selection": "Use-Case Fit, Material Choice",
                "spec_comparison": "Performance Tradeoffs, Use-Case Fit",
                "wholesale_faq": "Application Fit, Packaging Constraints",
            }
            base = defaults.get(page_type or "")
            if base:
                parts.append(base)

        deduped = []
        for part in parts:
            normalized = part.lower().strip()
            if normalized and normalized not in {item.lower() for item in deduped}:
                deduped.append(part)

        if not deduped:
            return "Application Fit and Material Choice"
        if len(deduped) == 1:
            return deduped[0]
        return f"{deduped[0]}, {deduped[1]}"
    
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
        target_keyword: str = None,
        content_lane: Optional[str] = None,
        serp_role: Optional[str] = None,
    ) -> OptimizedTitle:
        """
        Select the best title based on strategy

        Args:
            variants: List of title variants
            strategy: Selection strategy (ctr, balanced, experimental)
            target_keyword: Optional keyword to match against
            content_lane: Optional lane hint (traffic_entry / procurement_conversion)
            serp_role: Optional SERP role hint for strict fallback generation

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
                if content_lane:
                    effective_ctr *= 1 + self._lane_fit_score(variant.title, content_lane) * 0.12
                effective_ctr *= title_quality_penalty(variant.title)
                scored_variants.append((variant, effective_ctr, match_score))
        else:
            scored_variants = [
                (
                    variant,
                    variant.expected_ctr
                    * (1 + (self._lane_fit_score(variant.title, content_lane) * 0.12 if content_lane else 0))
                    * title_quality_penalty(variant.title),
                    1.0,
                )
                for variant in variants
            ]

        eligible_variants = [
            item for item in scored_variants
            if item[2] >= self.MIN_ACCEPTABLE_MATCH
        ]
        if not eligible_variants and target_keyword:
            return self._build_strict_fallback_variant(target_keyword, content_lane, serp_role)
        eligible_variants = eligible_variants or scored_variants

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

    def _lane_fit_score(self, title: str, content_lane: Optional[str]) -> float:
        """Measure whether a title's language matches the requested lane."""
        if not content_lane:
            return 0.0

        title_lower = title.lower()
        if content_lane == "procurement_conversion":
            terms = self.PROCUREMENT_SIGNALS
        else:
            terms = self.TRAFFIC_SIGNALS

        hits = sum(1 for term in terms if term in title_lower)
        return min(1.0, hits / 4)

    def _build_strict_fallback_variant(
        self,
        target_keyword: str,
        content_lane: Optional[str],
        serp_role: Optional[str],
    ) -> OptimizedTitle:
        """Use a strict query-preserving fallback when all variants mismatch the keyword."""
        keyword_title = self._keyword_title(target_keyword)
        procurement_titles = {
            "supplier_evaluation": f"{keyword_title}: Supplier Fit, Samples, and Quote Criteria",
            "procurement_faq": f"{keyword_title}: Sample Policy, Quote Criteria, and Timing Risks",
        }
        traffic_titles = {
            "material_comparison": f"{keyword_title}: Tradeoffs, Fit, and Selection Criteria",
            "application_fit": f"{keyword_title}: Application Fit, Use Cases, and Selection Logic",
            "spec_selection": f"{keyword_title}: Specs, Compatibility, and Selection Criteria",
            "problem_risk": f"{keyword_title}: Risks, Mismatches, and Better Choices",
        }

        if content_lane == "procurement_conversion":
            title = procurement_titles.get(serp_role or "", f"{keyword_title}: Supplier Evaluation and Buying Criteria")
            hook_type = HookType.DATA
        else:
            title = traffic_titles.get(serp_role or "", f"{keyword_title}: Application Fit and Selection Criteria")
            hook_type = HookType.HOW_TO

        return OptimizedTitle(
            title=self._finalize_title(title, target_keyword),
            hook_type=hook_type,
            expected_ctr=0.035,
            rationale="Strict query-preserving fallback because generated variants did not match the target keyword closely enough.",
            test_variant="Z",
        )
