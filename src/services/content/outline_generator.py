"""
Content Outline Generator

Generates research-supported content outlines for topics.
"""

import logging
from typing import List, Optional
from datetime import datetime

from src.models.content_intelligence import (
    ContentTopic, ResearchResult, ContentOutline, OutlineSection,
    ContentType, HookType, PainPoint
)

logger = logging.getLogger(__name__)


class OutlineGenerator:
    """Generate research-supported content outlines"""
    
    def __init__(self):
        self.section_templates = self._load_section_templates()
        logger.info("OutlineGenerator initialized")
    
    def _load_section_templates(self) -> dict:
        """Load templates for different content types"""
        return {
            ContentType.PROBLEM_STATEMENT: {
                'word_count': 400,
                'key_points_template': [
                    'Describe the problem context',
                    'Explain impact on target audience',
                    'Present supporting data/statistics',
                    'Highlight urgency or consequences'
                ]
            },
            ContentType.SOLUTION: {
                'word_count': 600,
                'key_points_template': [
                    'Present the solution approach',
                    'Explain step-by-step implementation',
                    'Include best practices and tips',
                    'Address common objections'
                ]
            },
            ContentType.COMPARISON: {
                'word_count': 500,
                'key_points_template': [
                    'Present comparison criteria',
                    'Compare options side-by-side',
                    'Highlight pros and cons',
                    'Provide recommendations'
                ]
            },
            ContentType.BEST_PRACTICES: {
                'word_count': 500,
                'key_points_template': [
                    'List key best practices',
                    'Explain why each matters',
                    'Provide implementation examples',
                    'Include common mistakes to avoid'
                ]
            },
            ContentType.CASE_STUDY: {
                'word_count': 600,
                'key_points_template': [
                    'Introduce the case subject',
                    'Describe the challenge faced',
                    'Explain the solution implemented',
                    'Present results and metrics',
                    'Extract key lessons learned'
                ]
            },
            ContentType.DATA_ANALYSIS: {
                'word_count': 500,
                'key_points_template': [
                    'Present data overview',
                    'Explain methodology',
                    'Highlight key findings',
                    'Provide interpretation',
                    'Suggest actionable insights'
                ]
            },
            ContentType.FAQ: {
                'word_count': 400,
                'key_points_template': [
                    'Question 1 with detailed answer',
                    'Question 2 with detailed answer',
                    'Question 3 with detailed answer',
                    'Question 4 with detailed answer'
                ]
            },
            ContentType.CTA: {
                'word_count': 200,
                'key_points_template': [
                    'Summarize key benefits',
                    'Present clear call-to-action',
                    'Address final objections',
                    'Create sense of urgency'
                ]
            }
        }
    
    async def generate_outline(
        self,
        topic: ContentTopic,
        research: Optional[ResearchResult] = None
    ) -> ContentOutline:
        """
        Generate a research-supported content outline
        
        Args:
            topic: The content topic
            research: Optional research results (uses topic.research_result if not provided)
            
        Returns:
            ContentOutline with structured sections
        """
        if research is None:
            research = topic.research_result
        
        logger.info(f"Generating outline for topic: {topic.title}")
        
        # Generate hook
        hook, hook_type = self._generate_hook(topic, research)
        
        # Build sections
        sections = []
        order = 0
        
        # 1. Introduction/Problem section
        if research and research.pain_points:
            section = self._create_problem_section(research.pain_points[0], order)
            sections.append(section)
            order += 1
        
        # 2. Solution sections based on topic angle
        solution_sections = self._create_solution_sections(topic, research, order)
        sections.extend(solution_sections)
        order += len(solution_sections)
        
        # 3. Comparison section (if competitive research available)
        if research and research.competitor_insights:
            section = self._create_comparison_section(research, order)
            sections.append(section)
            order += 1
        
        # 4. Best practices section
        if topic.business_intent > 0.6:
            section = self._create_best_practices_section(topic, research, order)
            sections.append(section)
            order += 1
        
        # 5. Case study section (if data available)
        if research and (research.statistics or research.expert_quotes):
            section = self._create_data_section(research, order)
            sections.append(section)
            order += 1
        
        # 6. FAQ section for high-intent topics
        if topic.business_intent > 0.5:
            section = self._create_faq_section(topic, research, order)
            sections.append(section)
            order += 1
        
        # Calculate totals
        total_word_count = sum(s.estimated_word_count for s in sections)
        estimated_read_time = max(5, total_word_count // 250)  # ~250 wpm reading speed
        
        # Determine conclusion type based on business intent
        conclusion_type = "cta" if topic.business_intent > 0.7 else "summary"
        
        outline = ContentOutline(
            title=topic.title,
            hook=hook,
            hook_type=hook_type,
            sections=sections,
            conclusion_type=conclusion_type,
            target_word_count=total_word_count,
            estimated_read_time=estimated_read_time
        )
        
        logger.info(f"Generated outline with {len(sections)} sections, ~{total_word_count} words")
        return outline
    
    def _generate_hook(
        self,
        topic: ContentTopic,
        research: Optional[ResearchResult]
    ) -> tuple[str, HookType]:
        """Generate an engaging hook based on research"""
        
        # Priority 1: Data-driven hook if statistics available
        if research and research.statistics:
            stat = research.statistics[0]
            value = stat.get('value', '')
            subject = stat.get('subject', topic.industry)
            action = stat.get('action', 'are affected')
            hook = f"{value}% of {subject} {action}: Here's what our research reveals"
            return hook, HookType.DATA
        
        # Priority 2: Problem-focused hook
        if research and research.pain_points:
            pain = research.pain_points[0]
            hook = f"The hidden cost of {pain.category}: A {topic.industry} analysis"
            return hook, HookType.PROBLEM
        
        # Priority 3: Question hook
        if topic.angle:
            hook = f"Is {topic.angle} actually hurting your business?"
            return hook, HookType.QUESTION
        
        # Priority 4: How-to hook
        hook = f"How to master {topic.title}: A comprehensive guide"
        return hook, HookType.HOW_TO
    
    def _create_problem_section(
        self,
        pain_point: PainPoint,
        order: int
    ) -> OutlineSection:
        """Create a problem statement section"""
        template = self.section_templates[ContentType.PROBLEM_STATEMENT]
        
        return OutlineSection(
            title=f"The {pain_point.category} Challenge",
            content_type=ContentType.PROBLEM_STATEMENT,
            key_points=[
                f"Understanding {pain_point.category.lower()} in context",
                f"Impact: {pain_point.description}",
                f"Severity level: {pain_point.severity:.0%}",
                f"Frequency: {pain_point.frequency}"
            ],
            research_support=[{
                'type': 'pain_point',
                'category': pain_point.category,
                'severity': pain_point.severity,
                'evidence': pain_point.evidence,
                'quotes': pain_point.quotes[:2] if pain_point.quotes else []
            }],
            estimated_word_count=template['word_count'],
            order=order
        )
    
    def _create_solution_sections(
        self,
        topic: ContentTopic,
        research: Optional[ResearchResult],
        start_order: int
    ) -> List[OutlineSection]:
        """Create solution-focused sections"""
        sections = []
        template = self.section_templates[ContentType.SOLUTION]
        
        # Create 2-3 solution sections based on topic complexity
        solutions = [
            {
                'title': f"Strategic Approach to {topic.title}",
                'focus': 'overview'
            },
            {
                'title': f"Implementation Best Practices",
                'focus': 'practical'
            }
        ]
        
        if topic.business_intent > 0.7:
            solutions.append({
                'title': f"ROI Optimization Techniques",
                'focus': 'advanced'
            })
        
        research_support = None
        if research and research.content_gaps:
            research_support = [{
                'type': 'content_gap',
                'topic': gap.topic,
                'opportunity_score': gap.opportunity_score
            } for gap in research.content_gaps[:2]]
        
        for i, solution in enumerate(solutions):
            section = OutlineSection(
                title=solution['title'],
                content_type=ContentType.SOLUTION,
                key_points=template['key_points_template'].copy(),
                research_support=research_support,
                estimated_word_count=template['word_count'],
                order=start_order + i
            )
            sections.append(section)
        
        return sections
    
    def _create_comparison_section(
        self,
        research: ResearchResult,
        order: int
    ) -> OutlineSection:
        """Create a market comparison section"""
        template = self.section_templates[ContentType.COMPARISON]
        
        # Build comparison from competitor insights
        competitors = [ci.competitor for ci in research.competitor_insights[:3]]
        
        research_support = [{
            'type': 'competitor_insight',
            'competitor': ci.competitor,
            'strengths': ci.strengths[:2],
            'weaknesses': ci.weaknesses[:2],
            'missing_elements': ci.missing_elements[:2]
        } for ci in research.competitor_insights[:3]]
        
        return OutlineSection(
            title="Market Comparison & Analysis",
            content_type=ContentType.COMPARISON,
            key_points=[
                f"Comparison criteria for {', '.join(competitors)}",
                "Strengths and weaknesses analysis",
                "Gap identification and opportunities",
                "Strategic recommendations"
            ],
            research_support=research_support,
            estimated_word_count=template['word_count'],
            order=order
        )
    
    def _create_best_practices_section(
        self,
        topic: ContentTopic,
        research: Optional[ResearchResult],
        order: int
    ) -> OutlineSection:
        """Create a best practices section"""
        template = self.section_templates[ContentType.BEST_PRACTICES]
        
        research_support = None
        if research and research.expert_quotes:
            research_support = [{
                'type': 'expert_quote',
                'quote': quote.get('text', ''),
                'source': quote.get('source', 'Industry Expert')
            } for quote in research.expert_quotes[:3]]
        
        return OutlineSection(
            title=f"Best Practices for {topic.title}",
            content_type=ContentType.BEST_PRACTICES,
            key_points=template['key_points_template'].copy(),
            research_support=research_support,
            estimated_word_count=template['word_count'],
            order=order
        )
    
    def _create_data_section(
        self,
        research: ResearchResult,
        order: int
    ) -> OutlineSection:
        """Create a data analysis or case study section"""
        
        if research.statistics:
            template = self.section_templates[ContentType.DATA_ANALYSIS]
            content_type = ContentType.DATA_ANALYSIS
            title = "Key Data & Insights"
            
            research_support = [{
                'type': 'statistic',
                'data': stat
            } for stat in research.statistics[:5]]
        else:
            template = self.section_templates[ContentType.CASE_STUDY]
            content_type = ContentType.CASE_STUDY
            title = "Real-World Application"
            
            research_support = [{
                'type': 'expert_insight',
                'quote': quote
            } for quote in research.expert_quotes[:3]]
        
        return OutlineSection(
            title=title,
            content_type=content_type,
            key_points=template['key_points_template'].copy(),
            research_support=research_support,
            estimated_word_count=template['word_count'],
            order=order
        )
    
    def _create_faq_section(
        self,
        topic: ContentTopic,
        research: Optional[ResearchResult],
        order: int
    ) -> OutlineSection:
        """Create an FAQ section"""
        template = self.section_templates[ContentType.FAQ]
        
        # Generate FAQ questions based on pain points and topic
        questions = [
            f"What is {topic.title}?",
            f"Why is {topic.title} important for {topic.target_audience}?",
            f"How can I implement {topic.title} effectively?",
            f"What are common mistakes to avoid with {topic.title}?"
        ]
        
        if research and research.pain_points:
            questions.append(f"How do I address {research.pain_points[0].category} challenges?")
        
        return OutlineSection(
            title=f"Frequently Asked Questions",
            content_type=ContentType.FAQ,
            key_points=questions,
            research_support=None,
            estimated_word_count=template['word_count'],
            order=order
        )
