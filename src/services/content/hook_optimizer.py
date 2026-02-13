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

logger = logging.getLogger(__name__)


class HookOptimizer:
    """Generate optimized titles with multiple hook variants"""
    
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
        logger.info("HookOptimizer initialized")
    
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
    
    def _generate_title_for_hook(
        self,
        topic: ContentTopic,
        research: ResearchResult,
        hook_type: HookType
    ) -> tuple[str, str]:
        """Generate a title for a specific hook type"""
        
        templates = self.title_templates.get(hook_type, [])
        if not templates:
            return topic.title, "Fallback title"
        
        template = random.choice(templates)
        
        # Build context for template filling
        context = self._build_template_context(topic, research, hook_type)
        
        try:
            title = template.format(**context)
        except KeyError:
            # Fallback if template variables missing
            title = self._generate_fallback_title(topic, hook_type)
        
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
    
    def _generate_fallback_title(self, topic: ContentTopic, hook_type: HookType) -> str:
        """Generate a fallback title if template fails"""
        fallbacks = {
            HookType.DATA: f"Data-Driven Insights: {topic.title}",
            HookType.PROBLEM: f"Solving the {topic.title} Challenge",
            HookType.HOW_TO: f"How to Master {topic.title}",
            HookType.QUESTION: f"Is {topic.title} Right for You?",
            HookType.STORY: f"The {topic.title} Success Story",
            HookType.CONTROVERSY: f"Rethinking {topic.title}: A New Perspective"
        }
        return fallbacks.get(hook_type, topic.title)
    
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
        strategy: str = "ctr"  # "ctr", "balanced", "experimental"
    ) -> OptimizedTitle:
        """
        Select the best title based on strategy
        
        Args:
            variants: List of title variants
            strategy: Selection strategy (ctr, balanced, experimental)
            
        Returns:
            The selected OptimizedTitle
        """
        if not variants:
            raise ValueError("No variants provided")
        
        if strategy == "ctr":
            # Pure CTR optimization
            return max(variants, key=lambda x: x.expected_ctr)
        
        elif strategy == "balanced":
            # Balance CTR with variety
            # Prefer data or problem hooks if CTR is close
            best_ctr = max(variants, key=lambda x: x.expected_ctr)
            
            for variant in variants:
                if variant.hook_type in [HookType.DATA, HookType.PROBLEM]:
                    if variant.expected_ctr >= best_ctr.expected_ctr * 0.95:
                        return variant
            
            return best_ctr
        
        elif strategy == "experimental":
            # Try less common hook types occasionally
            uncommon_hooks = [HookType.CONTROVERSY, HookType.STORY]
            for variant in variants:
                if variant.hook_type in uncommon_hooks:
                    return variant
            return max(variants, key=lambda x: x.expected_ctr)
        
        else:
            return max(variants, key=lambda x: x.expected_ctr)
