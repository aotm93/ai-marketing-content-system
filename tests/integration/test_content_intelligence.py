"""
Integration tests for Content Intelligence Layer

Tests the complete research-to-content pipeline.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.services.content_intelligence import ContentIntelligenceService, ValueScorer, TopicGenerator
from src.services.research.cache import ResearchCache
from src.services.content.outline_generator import OutlineGenerator
from src.services.content.hook_optimizer import HookOptimizer
from src.services.content.research_assistant import ResearchAssistant, CitationFormat
from src.models.content_intelligence import (
    ContentTopic, ResearchResult, ResearchContext, PainPoint,
    TrendData, CompetitorInsight, ContentGap, ResearchSource,
    HookType, ContentOutline, ContentType
)


class TestContentIntelligenceIntegration:
    """Integration tests for the complete Content Intelligence pipeline"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        return Mock()
    
    @pytest.fixture
    def sample_research_result(self):
        """Create a sample research result for testing"""
        return ResearchResult(
            trend_data=TrendData(
                topic="packaging automation",
                trend_direction="rising",
                growth_rate=23.5,
                related_topics=["sustainable packaging", "smart packaging"]
            ),
            pain_points=[
                PainPoint(
                    description="High packaging costs",
                    category="Cost Management",
                    severity=0.8,
                    frequency="common",
                    evidence="67% of companies report cost as top concern",
                    quotes=["Our packaging costs have risen 30% this year"]
                )
            ],
            content_gaps=[
                ContentGap(
                    topic="sustainable automation",
                    current_coverage="Surface level",
                    gap_type="depth",
                    opportunity_score=0.85,
                    suggested_approach="Deep technical guide"
                )
            ],
            competitor_insights=[
                CompetitorInsight(
                    competitor="Competitor A",
                    strengths=["Good SEO", "Fast loading"],
                    weaknesses=["Thin content", "No data"],
                    missing_elements=["case studies", "statistics"]
                )
            ],
            statistics=[
                {"value": 67, "subject": "companies", "metric": "cost concern", "context": "annual survey"}
            ],
            expert_quotes=[
                {"text": "Automation is the future", "source": "Industry Expert", "title": "CEO"}
            ],
            timestamp=datetime.now(),
            sources=[
                ResearchSource(name="Packaging Weekly", credibility_score=0.9, type="industry_report")
            ]
        )
    
    @pytest.fixture
    def sample_content_topic(self, sample_research_result):
        """Create a sample content topic"""
        return ContentTopic(
            title="How to Reduce Packaging Costs Through Automation",
            slug="reduce-packaging-costs-automation",
            angle="Data-driven cost reduction strategies",
            hook_type=HookType.DATA,
            business_intent=0.85,
            trend_score=0.75,
            competition_score=0.4,
            differentiation_score=0.8,
            brand_alignment_score=0.9,
            value_score=0.82,
            research_sources=[
                ResearchSource(name="Industry Report 2026", credibility_score=0.9, type="industry_report")
            ],
            research_result=sample_research_result,
            industry="packaging",
            target_audience="operations_managers",
            content_format="guide",
            estimated_difficulty="medium"
        )
    
    @pytest.mark.asyncio
    async def test_complete_pipeline(self, mock_db, sample_content_topic):
        """Test the complete pipeline from research to outline"""
        # Arrange
        cache = ResearchCache(db=mock_db)
        service = ContentIntelligenceService(mock_db, cache)
        outline_generator = OutlineGenerator()
        hook_optimizer = HookOptimizer()
        
        # Act - Generate outline from topic
        outline = await outline_generator.generate_outline(
            topic=sample_content_topic,
            research=sample_content_topic.research_result
        )
        
        # Assert
        assert outline is not None
        assert outline.title == sample_content_topic.title
        assert len(outline.sections) > 0
        assert outline.hook is not None
        assert outline.target_word_count >= 1500
        
    @pytest.mark.asyncio
    async def test_cache_hit_scenario(self, mock_db):
        """Test cache hit returns cached data without API calls"""
        # Arrange
        cache = ResearchCache(db=mock_db)
        cached_data = {
            "topics": ["topic1", "topic2"],
            "timestamp": datetime.now().isoformat()
        }
        await cache.set("test_key", cached_data, ttl=3600)
        
        # Act
        result = await cache.get("test_key")
        
        # Assert
        assert result is not None
        assert result["topics"] == ["topic1", "topic2"]
        stats = cache.get_stats()
        assert stats["memory_hits"] == 1
    
    @pytest.mark.asyncio
    async def test_cache_miss_scenario(self, mock_db):
        """Test cache miss generates new data"""
        # Arrange
        cache = ResearchCache(db=mock_db)
        
        # Act
        result = await cache.get("nonexistent_key")
        
        # Assert
        assert result is None
        stats = cache.get_stats()
        assert stats["misses"] == 1
    
    @pytest.mark.asyncio
    async def test_value_scoring_accuracy(self, sample_content_topic):
        """Test value scoring produces expected scores"""
        # Arrange
        scorer = ValueScorer()
        
        # Act
        score = scorer.score(sample_content_topic)
        
        # Assert
        assert 0 <= score <= 1
        assert score > 0.5  # Good topic should have decent score
        
        # Verify weighted calculation
        expected_score = (
            sample_content_topic.business_intent * 0.30 +
            sample_content_topic.trend_score * 0.25 +
            (1 - sample_content_topic.competition_score) * 0.20 +
            sample_content_topic.differentiation_score * 0.15 +
            sample_content_topic.brand_alignment_score * 0.10
        )
        assert abs(score - expected_score) < 0.01
    
    @pytest.mark.asyncio
    async def test_hook_generation_variety(self, sample_content_topic):
        """Test that multiple hook types are generated"""
        # Arrange
        optimizer = HookOptimizer()
        
        # Act
        titles = await optimizer.generate_optimized_titles(
            sample_content_topic,
            count=5
        )
        
        # Assert
        assert len(titles) == 5
        hook_types = [t.hook_type for t in titles]
        assert len(set(hook_types)) >= 3  # At least 3 different types
        
        # All should have CTR estimates
        for title in titles:
            assert 0 <= title.expected_ctr <= 1
            assert len(title.rationale) > 10
    
    @pytest.mark.asyncio
    async def test_research_assistant_section_support(self, sample_content_topic):
        """Test research assistant provides section-level research"""
        # Arrange
        assistant = ResearchAssistant(sample_content_topic.research_result)
        
        from src.models.content_intelligence import OutlineSection
        section = OutlineSection(
            title="Cost Reduction Strategies",
            content_type=ContentType.SOLUTION,
            key_points=["Identify cost centers", "Implement automation", "Measure ROI"],
            order=1
        )
        
        # Act
        research = await assistant.research_section(section)
        
        # Assert
        assert research is not None
        assert len(research.data_points) > 0 or len(research.quotes) > 0
    
    @pytest.mark.asyncio
    async def test_citation_formatting(self, sample_content_topic):
        """Test citation formatting in different styles"""
        # Arrange
        assistant = ResearchAssistant()
        from src.services.content.research_assistant import SectionResearch
        
        research = SectionResearch(
            sources=sample_content_topic.research_sources
        )
        
        # Act - APA format
        apa_citations = await assistant.generate_citations(research, CitationFormat.APA)
        
        # Act - MLA format
        mla_citations = await assistant.generate_citations(research, CitationFormat.MLA)
        
        # Assert
        assert len(apa_citations) > 0
        assert len(mla_citations) > 0
        assert apa_citations[0].text != mla_citations[0].text  # Different formats
    
    @pytest.mark.asyncio
    async def test_outline_structure_logic(self, sample_content_topic):
        """Test that outline has logical structure"""
        # Arrange
        generator = OutlineGenerator()
        
        # Act
        outline = await generator.generate_outline(
            sample_content_topic,
            sample_content_topic.research_result
        )
        
        # Assert - Structure checks
        section_types = [s.content_type for s in outline.sections]
        
        # Should have problem or introduction first
        assert section_types[0] in [ContentType.PROBLEM_STATEMENT, ContentType.SOLUTION]
        
        # Should have at least one solution section
        assert ContentType.SOLUTION in section_types
        
        # Word count should be reasonable
        assert 1000 <= outline.target_word_count <= 5000
        
        # Reading time estimate should make sense
        expected_read_time = outline.target_word_count // 250
        assert abs(outline.estimated_read_time - expected_read_time) <= 2


class TestContentIntelligencePerformance:
    """Performance tests for Content Intelligence Layer"""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cache_hit_performance(self, mock_db):
        """Cache hit should be under 10ms"""
        import time
        
        # Arrange
        cache = ResearchCache(db=mock_db)
        await cache.set("perf_key", {"data": "test"}, ttl=3600)
        
        # Act
        start = time.time()
        for _ in range(100):
            await cache.get("perf_key")
        elapsed = time.time() - start
        
        avg_time = (elapsed / 100) * 1000  # Convert to ms
        
        # Assert
        assert avg_time < 10, f"Cache hit took {avg_time:.2f}ms, expected < 10ms"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_topic_generation_performance(self, mock_db):
        """Topic generation should complete under 2 seconds"""
        import time
        from unittest.mock import patch
        
        # Arrange
        cache = ResearchCache(db=mock_db)
        service = ContentIntelligenceService(mock_db, cache)
        
        # Mock orchestrator to avoid actual API calls
        with patch.object(service.orchestrator, 'conduct_research', new_callable=AsyncMock) as mock_research:
            mock_research.return_value = ResearchResult(
                pain_points=[],
                competitor_insights=[],
                timestamp=datetime.now()
            )
            
            # Act
            start = time.time()
            topics = await service.generate_high_value_topics(
                industry="packaging",
                audience="b2b",
                pain_points=["cost"]
            )
            elapsed = time.time() - start
            
            # Assert
            assert elapsed < 2, f"Topic generation took {elapsed:.2f}s, expected < 2s"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cache_hit_rate_target(self, mock_db):
        """Verify cache can achieve > 80% hit rate"""
        # Arrange
        cache = ResearchCache(db=mock_db)
        
        # Pre-populate cache
        for i in range(100):
            await cache.set(f"key_{i}", {"id": i}, ttl=3600)
        
        # Act - Access all keys multiple times
        for _ in range(5):
            for i in range(100):
                await cache.get(f"key_{i}")
        
        # Access some new keys (misses)
        for i in range(100, 120):
            await cache.get(f"key_{i}")
        
        # Assert
        stats = cache.get_stats()
        hit_rate = stats["hit_rate"]
        assert hit_rate > 0.8, f"Cache hit rate {hit_rate:.2%} below target of 80%"
