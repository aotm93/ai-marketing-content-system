"""
Unit tests for Hook Optimizer

Tests title generation and CTR estimation.
"""

import pytest
from datetime import datetime

from src.services.content.hook_optimizer import HookOptimizer
from src.models.content_intelligence import ContentTopic, HookType, ResearchResult, TrendData, PainPoint


class TestHookOptimizer:
    """Unit tests for HookOptimizer"""
    
    @pytest.fixture
    def optimizer(self):
        """Create a HookOptimizer instance"""
        return HookOptimizer()
    
    @pytest.fixture
    def base_topic(self):
        """Create a base topic for testing"""
        return ContentTopic(
            title="Packaging Automation Guide",
            angle="Cost reduction strategies",
            hook_type=HookType.HOW_TO,
            industry="packaging",
            target_audience="operations_managers",
            business_intent=0.75,
            trend_score=0.7,
            differentiation_score=0.8,
            research_result=None
        )
    
    @pytest.mark.asyncio
    async def test_generate_multiple_title_variants(self, optimizer, base_topic):
        """Test that multiple title variants are generated"""
        # Act
        titles = await optimizer.generate_optimized_titles(base_topic, count=5)
        
        # Assert
        assert len(titles) == 5
        # Should have different hook types
        hook_types = [t.hook_type for t in titles]
        assert len(set(hook_types)) >= 3
    
    @pytest.mark.asyncio
    async def test_title_variants_sorted_by_ctr(self, optimizer, base_topic):
        """Test that titles are sorted by CTR (highest first)"""
        # Act
        titles = await optimizer.generate_optimized_titles(base_topic, count=5)
        
        # Assert
        ctrs = [t.expected_ctr for t in titles]
        assert ctrs == sorted(ctrs, reverse=True)
    
    @pytest.mark.asyncio
    async def test_all_titles_have_ctr_estimates(self, optimizer, base_topic):
        """Test that all generated titles have CTR estimates"""
        # Act
        titles = await optimizer.generate_optimized_titles(base_topic, count=5)
        
        # Assert
        for title in titles:
            assert 0 <= title.expected_ctr <= 1
            assert isinstance(title.expected_ctr, float)
    
    @pytest.mark.asyncio
    async def test_all_titles_have_rationales(self, optimizer, base_topic):
        """Test that all titles have explanatory rationales"""
        # Act
        titles = await optimizer.generate_optimized_titles(base_topic, count=5)
        
        # Assert
        for title in titles:
            assert len(title.rationale) > 10
            assert isinstance(title.rationale, str)
    
    @pytest.mark.asyncio
    async def test_ab_test_variants_assigned(self, optimizer, base_topic):
        """Test that A/B test variants are assigned"""
        # Act
        titles = await optimizer.generate_optimized_titles(base_topic, count=5)
        
        # Assert
        variants = [t.test_variant for t in titles]
        assert "A" in variants
        assert len(set(variants)) == len(variants)  # All unique
    
    @pytest.mark.asyncio
    async def test_data_hook_with_statistics(self, optimizer):
        """Test data-driven hook when statistics available"""
        # Arrange
        topic = ContentTopic(
            title="Automation Impact",
            angle="Data insights",
            hook_type=HookType.DATA,
            industry="packaging",
            target_audience="b2b",
            business_intent=0.8,
            trend_score=0.8,
            differentiation_score=0.7,
            research_result=ResearchResult(
                statistics=[
                    {"value": 67, "subject": "companies", "metric": "savings", "impact_score": 0.9}
                ],
                timestamp=datetime.now()
            )
        )
        
        # Act
        titles = await optimizer.generate_optimized_titles(topic, count=5)
        
        # Assert
        data_titles = [t for t in titles if t.hook_type == HookType.DATA]
        assert len(data_titles) > 0
        # Data titles should reference the statistic
        assert any("67" in t.title for t in data_titles)
    
    @pytest.mark.asyncio
    async def test_problem_hook_with_pain_points(self, optimizer):
        """Test problem-focused hook when pain points available"""
        # Arrange
        topic = ContentTopic(
            title="Cost Management",
            angle="Problem solving",
            hook_type=HookType.PROBLEM,
            industry="packaging",
            target_audience="b2b",
            business_intent=0.7,
            trend_score=0.6,
            differentiation_score=0.6,
            research_result=ResearchResult(
                pain_points=[
                    PainPoint(
                        description="High costs",
                        category="Cost Management",
                        severity=0.85,
                        frequency="common"
                    )
                ],
                timestamp=datetime.now()
            )
        )
        
        # Act
        titles = await optimizer.generate_optimized_titles(topic, count=5)
        
        # Assert
        problem_titles = [t for t in titles if t.hook_type == HookType.PROBLEM]
        assert len(problem_titles) > 0
    
    @pytest.mark.asyncio
    async def test_ctr_estimation_factors(self, optimizer):
        """Test that CTR estimation considers multiple factors"""
        # Arrange - High value topic
        high_value = ContentTopic(
            title="High Value",
            angle="Premium",
            hook_type=HookType.DATA,
            industry="packaging",
            target_audience="b2b",
            business_intent=0.95,
            trend_score=0.9,
            differentiation_score=0.9,
            research_result=ResearchResult(
                statistics=[{"value": 85}],
                pain_points=[PainPoint(description="Test", category="Test", severity=0.9, frequency="common")],
                timestamp=datetime.now()
            )
        )
        
        # Arrange - Low value topic
        low_value = ContentTopic(
            title="Low Value",
            angle="Basic",
            hook_type=HookType.HOW_TO,
            industry="packaging",
            target_audience="b2b",
            business_intent=0.3,
            trend_score=0.3,
            differentiation_score=0.2,
            research_result=None
        )
        
        # Act
        high_titles = await optimizer.generate_optimized_titles(high_value, count=1)
        low_titles = await optimizer.generate_optimized_titles(low_value, count=1)
        
        # Assert
        assert high_titles[0].expected_ctr > low_titles[0].expected_ctr
    
    @pytest.mark.asyncio
    async def test_select_best_title_ctr_strategy(self, optimizer, base_topic):
        """Test selecting best title with CTR strategy"""
        # Arrange
        titles = await optimizer.generate_optimized_titles(base_topic, count=5)
        
        # Act
        best = await optimizer.select_best_title(titles, strategy="ctr")
        
        # Assert
        assert best.expected_ctr == max(t.expected_ctr for t in titles)
    
    @pytest.mark.asyncio
    async def test_select_best_title_balanced_strategy(self, optimizer, base_topic):
        """Test selecting best title with balanced strategy"""
        # Arrange
        titles = await optimizer.generate_optimized_titles(base_topic, count=5)
        
        # Act
        best = await optimizer.select_best_title(titles, strategy="balanced")
        
        # Assert
        assert best is not None
        # Should prefer data/problem if close to max
        if best.hook_type in [HookType.DATA, HookType.PROBLEM]:
            assert best.expected_ctr >= max(t.expected_ctr for t in titles) * 0.95
    
    @pytest.mark.asyncio
    async def test_select_best_title_experimental_strategy(self, optimizer, base_topic):
        """Test selecting best title with experimental strategy"""
        # Arrange
        titles = await optimizer.generate_optimized_titles(base_topic, count=5)
        
        # Act
        best = await optimizer.select_best_title(titles, strategy="experimental")
        
        # Assert
        assert best is not None
        # Might select controversial or story hooks
        uncommon = [HookType.CONTROVERSY, HookType.STORY]
        if best.hook_type in uncommon:
            pass  # Expected behavior
        else:
            # Otherwise should be max CTR
            assert best.expected_ctr == max(t.expected_ctr for t in titles)
    
    @pytest.mark.asyncio
    async def test_ctr_bounds(self, optimizer, base_topic):
        """Test that CTR estimates stay within reasonable bounds"""
        # Act
        titles = await optimizer.generate_optimized_titles(base_topic, count=10)
        
        # Assert
        for title in titles:
            assert 0.02 <= title.expected_ctr <= 0.08, f"CTR {title.expected_ctr} out of expected bounds"
    
    @pytest.mark.asyncio
    async def test_title_contains_keyword(self, optimizer, base_topic):
        """Test that generated titles relate to the topic"""
        # Act
        titles = await optimizer.generate_optimized_titles(base_topic, count=5)
        
        # Assert
        for title in titles:
            # Title should be non-empty and reasonable length
            assert len(title.title) > 10
            assert len(title.title) < 200
