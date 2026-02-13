"""
Research Assistant

Real-time research support during content writing.
Provides section-level research, citations, and claim verification.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

from src.models.content_intelligence import (
    OutlineSection, ContentType, ResearchResult, ResearchSource
)

logger = logging.getLogger(__name__)


class CitationFormat(str, Enum):
    """Citation style formats"""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"


class SectionResearch(BaseModel):
    """Research data for a specific content section"""
    data_points: List[Dict[str, Any]] = []
    quotes: List[Dict[str, str]] = []
    examples: List[Dict[str, Any]] = []
    verifications: List[Dict[str, Any]] = []
    sources: List[ResearchSource] = []
    
    class Config:
        arbitrary_types_allowed = True


class Citation(BaseModel):
    """Formatted citation"""
    text: str
    url: Optional[str] = None
    type: str  # "article", "report", "expert", etc.
    format: CitationFormat


class ResearchAssistant:
    """Real-time research support during content writing"""
    
    def __init__(self, research_result: Optional[ResearchResult] = None):
        self.research_result = research_result
        self.claim_patterns = self._load_claim_patterns()
        logger.info("ResearchAssistant initialized")
    
    def _load_claim_patterns(self) -> List[re.Pattern]:
        """Load regex patterns for identifying claims in text"""
        return [
            re.compile(r'\d+\s*%'),  # Percentage claims
            re.compile(r'\$[\d,]+'),  # Dollar amount claims
            re.compile(r'(study|research|survey|report)\s+(shows|found|reveals)', re.I),
            re.compile(r'(according to|based on)\s+([^.]+)', re.I),
            re.compile(r'(\d+)\s+(percent|times|fold|years?)'),  # Statistical claims
        ]
    
    async def research_section(
        self,
        section_outline: OutlineSection,
        existing_content: str = ""
    ) -> SectionResearch:
        """
        Research support for specific section
        
        Args:
            section_outline: The section outline to research
            existing_content: Optional existing content to verify
            
        Returns:
            SectionResearch with supporting data
        """
        logger.info(f"Researching section: {section_outline.title}")
        
        research = SectionResearch()
        
        # Find supporting data based on content type
        if section_outline.content_type == ContentType.SOLUTION:
            research.data_points = await self._find_supporting_data(
                section_outline.title,
                section_outline.key_points
            )
        
        # Find expert quotes for problem/comparison sections
        if section_outline.content_type in [ContentType.PROBLEM_STATEMENT, ContentType.COMPARISON]:
            research.quotes = await self._find_expert_quotes(
                section_outline.key_points
            )
        
        # Find case studies for solution/best practices sections
        if section_outline.content_type in [ContentType.SOLUTION, ContentType.BEST_PRACTICES]:
            research.examples = await self._find_case_studies(
                section_outline.title
            )
        
        # Verify claims in existing content
        if existing_content:
            research.verifications = await self._verify_claims(existing_content)
        
        # Build sources list from research result
        if self.research_result and self.research_result.sources:
            research.sources = self._select_relevant_sources(
                section_outline,
                self.research_result.sources
            )
        
        logger.info(f"Section research complete: {len(research.data_points)} data points, {len(research.quotes)} quotes")
        return research
    
    async def _find_supporting_data(
        self,
        section_title: str,
        key_points: List[str]
    ) -> List[Dict[str, Any]]:
        """Find supporting data points for a section"""
        data_points = []
        
        if not self.research_result:
            return data_points
        
        # Extract statistics relevant to the section
        if self.research_result.statistics:
            for stat in self.research_result.statistics[:3]:
                if self._is_relevant_to_section(stat, section_title, key_points):
                    data_points.append({
                        'type': 'statistic',
                        'value': stat.get('value'),
                        'metric': stat.get('metric'),
                        'subject': stat.get('subject'),
                        'context': stat.get('context', ''),
                        'relevance': 'high'
                    })
        
        # Add trend data if available
        if self.research_result.trend_data:
            trend = self.research_result.trend_data
            data_points.append({
                'type': 'trend',
                'topic': trend.topic,
                'direction': trend.trend_direction,
                'growth_rate': trend.growth_rate,
                'relevance': 'medium'
            })
        
        return data_points
    
    async def _find_expert_quotes(
        self,
        key_points: List[str]
    ) -> List[Dict[str, str]]:
        """Find expert quotes relevant to key points"""
        quotes = []
        
        if not self.research_result:
            return quotes
        
        # Use quotes from research result
        if self.research_result.expert_quotes:
            for quote in self.research_result.expert_quotes[:3]:
                quotes.append({
                    'text': quote.get('text', ''),
                    'source': quote.get('source', 'Industry Expert'),
                    'title': quote.get('title', ''),
                    'relevance': 'high'
                })
        
        # Generate contextual quotes from pain point evidence
        if self.research_result.pain_points:
            for pain in self.research_result.pain_points[:2]:
                if pain.quotes:
                    for q in pain.quotes[:1]:
                        quotes.append({
                            'text': q,
                            'source': f'{pain.category} Research',
                            'title': f'{pain.severity:.0%} severity reported',
                            'relevance': 'medium'
                        })
        
        return quotes
    
    async def _find_case_studies(
        self,
        section_title: str
    ) -> List[Dict[str, Any]]:
        """Find relevant case studies and examples"""
        examples = []
        
        if not self.research_result:
            return examples
        
        # Use competitor insights as industry examples
        if self.research_result.competitor_insights:
            for comp in self.research_result.competitor_insights[:2]:
                examples.append({
                    'type': 'competitor_case',
                    'company': comp.competitor,
                    'strengths': comp.strengths[:3],
                    'lessons': f"Demonstrates effective {section_title.lower()} approach",
                    'relevance': 'high'
                })
        
        # Create examples from content gaps
        if self.research_result.content_gaps:
            for gap in self.research_result.content_gaps[:2]:
                examples.append({
                    'type': 'opportunity',
                    'topic': gap.topic,
                    'gap_type': gap.gap_type,
                    'approach': gap.suggested_approach,
                    'opportunity_score': gap.opportunity_score,
                    'relevance': 'medium'
                })
        
        return examples
    
    async def _verify_claims(self, content: str) -> List[Dict[str, Any]]:
        """Verify claims in content against research data"""
        verifications = []
        
        if not self.research_result:
            return verifications
        
        # Find potential claims in content
        claims = self._extract_claims(content)
        
        for claim in claims:
            verification = {
                'claim': claim['text'],
                'type': claim['type'],
                'status': 'unverified',
                'supporting_evidence': [],
                'suggestion': None
            }
            
            # Check against available data
            if claim['type'] == 'statistic' and self.research_result.statistics:
                # Try to match with known statistics
                for stat in self.research_result.statistics:
                    if self._claims_match(claim, stat):
                        verification['status'] = 'verified'
                        verification['supporting_evidence'].append(stat)
                        break
                
                if verification['status'] == 'unverified':
                    verification['suggestion'] = 'Consider citing a source for this statistic'
            
            elif claim['type'] == 'attribution' and self.research_result.expert_quotes:
                # Check if attributed to known expert
                verification['status'] = 'needs_review'
                verification['suggestion'] = 'Verify attribution against research sources'
            
            verifications.append(verification)
        
        return verifications
    
    def _extract_claims(self, content: str) -> List[Dict[str, Any]]:
        """Extract potential claims from content"""
        claims = []
        
        sentences = re.split(r'[.!?]+', content)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check for percentage claims
            if self.claim_patterns[0].search(sentence):
                claims.append({
                    'text': sentence,
                    'type': 'statistic'
                })
            
            # Check for research attributions
            elif self.claim_patterns[2].search(sentence):
                claims.append({
                    'text': sentence,
                    'type': 'attribution'
                })
            
            # Check for dollar amounts
            elif self.claim_patterns[1].search(sentence):
                claims.append({
                    'text': sentence,
                    'type': 'financial'
                })
        
        return claims
    
    def _claims_match(self, claim: Dict, stat: Dict) -> bool:
        """Check if a claim matches available statistics"""
        claim_text = claim['text'].lower()
        
        # Check if statistic value appears in claim
        stat_value = str(stat.get('value', ''))
        if stat_value and stat_value in claim_text:
            return True
        
        # Check if metric appears
        metric = stat.get('metric', '').lower()
        if metric and metric in claim_text:
            return True
        
        return False
    
    def _is_relevant_to_section(
        self,
        data: Dict,
        section_title: str,
        key_points: List[str]
    ) -> bool:
        """Check if data is relevant to section topic"""
        section_lower = section_title.lower()
        
        # Check data subject against section
        subject = data.get('subject', '').lower()
        if subject and subject in section_lower:
            return True
        
        # Check against key points
        for point in key_points:
            point_lower = point.lower()
            if subject and subject in point_lower:
                return True
            metric = data.get('metric', '').lower()
            if metric and metric in point_lower:
                return True
        
        return True  # Default to including if uncertain
    
    def _select_relevant_sources(
        self,
        section_outline: OutlineSection,
        sources: List[ResearchSource]
    ) -> List[ResearchSource]:
        """Select most relevant sources for the section"""
        # Sort by credibility and return top 3
        sorted_sources = sorted(
            sources,
            key=lambda s: s.credibility_score,
            reverse=True
        )
        return sorted_sources[:3]
    
    async def generate_citations(
        self,
        research_data: SectionResearch,
        format: CitationFormat = CitationFormat.APA
    ) -> List[Citation]:
        """
        Format citations according to style guide
        
        Args:
            research_data: Section research data
            format: Citation format (APA, MLA, Chicago)
            
        Returns:
            List of formatted citations
        """
        citations = []
        
        for source in research_data.sources:
            if format == CitationFormat.APA:
                citation_text = self._format_apa(source)
            elif format == CitationFormat.MLA:
                citation_text = self._format_mla(source)
            elif format == CitationFormat.CHICAGO:
                citation_text = self._format_chicago(source)
            else:
                citation_text = self._format_apa(source)
            
            citations.append(Citation(
                text=citation_text,
                url=source.url,
                type=source.type,
                format=format
            ))
        
        return citations
    
    def _format_apa(self, source: ResearchSource) -> str:
        """Format citation in APA style"""
        year = source.publish_date.year if source.publish_date else 'n.d.'
        return f"{source.name} ({year}). {source.type.replace('_', ' ').title()}. Retrieved from {source.url or 'Source'}"
    
    def _format_mla(self, source: ResearchSource) -> str:
        """Format citation in MLA style"""
        year = source.publish_date.year if source.publish_date else 'n.d.'
        return f"\"{source.type.replace('_', ' ').title()}.\" {source.name}, {year}."
    
    def _format_chicago(self, source: ResearchSource) -> str:
        """Format citation in Chicago style"""
        year = source.publish_date.year if source.publish_date else 'n.d.'
        return f"{source.name}. \"{source.type.replace('_', ' ').title()}.\" Accessed {datetime.now().strftime('%B %d, %Y')}. {source.url or ''}"
    
    async def suggest_improvements(
        self,
        section_outline: OutlineSection,
        research: SectionResearch
    ) -> List[str]:
        """Suggest improvements based on available research"""
        suggestions = []
        
        # Check for missing data
        if section_outline.content_type == ContentType.SOLUTION and not research.data_points:
            suggestions.append("Consider adding supporting statistics or data points")
        
        # Check for missing quotes in problem sections
        if section_outline.content_type == ContentType.PROBLEM_STATEMENT and not research.quotes:
            suggestions.append("Adding expert quotes would strengthen the problem statement")
        
        # Check for missing examples
        if section_outline.content_type in [ContentType.SOLUTION, ContentType.BEST_PRACTICES] and not research.examples:
            suggestions.append("Include real-world examples or case studies for credibility")
        
        # Check verification status
        unverified = [v for v in research.verifications if v['status'] == 'unverified']
        if unverified:
            suggestions.append(f"{len(unverified)} claims need verification or citation")
        
        return suggestions
