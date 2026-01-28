"""
Integration Test Suite
Validates P0-P3 core workflows using mock adapters.

Run this to verify system integrity.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# Mock Environment Variables for Settings to load without .env
os.environ["PRIMARY_AI_API_KEY"] = "mock_key"
os.environ["DATABASE_URL"] = "sqlite:///mock.db"
os.environ["WORDPRESS_URL"] = "http://mock.com"
os.environ["WORDPRESS_USERNAME"] = "mock"
os.environ["WORDPRESS_PASSWORD"] = "mock"
os.environ["ADMIN_PASSWORD"] = "mock"
os.environ["ADMIN_SESSION_SECRET"] = "mock"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.agents.base_agent import BaseAgent
from src.scheduler.autopilot import AutopilotScheduler, AutopilotConfig
from src.scheduler.job_runner import JobRunner
from src.pseo.dimension_model import DimensionModel, Dimension, DimensionValue, DimensionType
from src.pseo.page_factory import pSEOFactory, FactoryConfig
from src.pseo.components import PageTemplate
from src.conversion.dynamic_cta import CTARecommendationEngine, UserIntent
from src.conversion.attribution import ConversionTracker, ConversionEvent, ConversionEventType

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockWordPressClient:
    """Mock WP Client for testing"""
    async def create_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[MOCK] Creating WP post: {post_data.get('title')}")
        return {"id": 123, "link": "http://mock-wp.com/post-123"}
        
    async def update_post_meta(self, post_id: int, meta: Dict[str, Any]) -> bool:
        logger.info(f"[MOCK] Updating meta for #{post_id}: {meta}")
        return True

class IntegrationTester:
    """Main integration test runner"""
    
    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "details": []}

    async def run_all(self):
        logger.info("Starting Integration Test Suite...")
        
        await self.test_p0_autopilot()
        await self.test_p1_agents()
        await self.test_p2_pseo()
        await self.test_supplementary()
        await self.test_p3_conversion()
        
        self.print_summary()

    async def assert_true(self, condition: bool, message: str):
        if condition:
            self.results["passed"] += 1
            self.results["details"].append(f"✅ {message}")
        else:
            self.results["failed"] += 1
            self.results["details"].append(f"❌ {message}")
            logger.error(f"Assertion failed: {message}")

    async def test_p0_autopilot(self):
        """Test P0: Autopilot Scheduling"""
        logger.info("--- Testing P0: Autopilot ---")
        try:
            config = AutopilotConfig(enabled=True, publish_interval_minutes=60)
            scheduler = AutopilotScheduler(config)
            
            # Register a mock job
            mock_run = False
            async def mock_job(ctx):
                nonlocal mock_run
                mock_run = True
                return {"status": "success"}
                
            scheduler.register_job("content_generation", mock_job)
            
            # Test run_once
            result = await scheduler.run_once("content_generation")
            
            await self.assert_true(result["status"] == "success", "Autopilot run_once")
            await self.assert_true(mock_run, "Job execution verified")
            
        except Exception as e:
            await self.assert_true(False, f"P0 Test Exception: {str(e)}")

    async def test_p1_agents(self):
        """Test P1: Agent Framework"""
        logger.info("--- Testing P1: Agents ---")
        try:
            # We'll test a simple agent component directly
            # Mocking OpportunityScoringAgent logic
            from src.agents.opportunity_scoring import OpportunityScoringAgent
            
            agent = OpportunityScoringAgent()
            
            # Mock GSC data
            mock_data = {
                "gsc_data": [
                    {"query": "test query", "position": 10, "impressions": 1000, "clicks": 50, "ctr": 0.05},
                    {"query": "hard query", "position": 50, "impressions": 100, "clicks": 0, "ctr": 0.0}
                ]
            }
            
            # Since OpenAI is required for full agent execution, we test the pre-processing logic
            # or we just verifying the class instantiates and has correct structure
            await self.assert_true(hasattr(agent, "execute"), "Agent has execute method")
            
            # Simulate scoring logic (white-box test logic from agent)
            # score = impression_score * 0.3 + position_score * 0.3 + ...
            # We trust the unit logic, here we verify integration readiness
            await self.assert_true(agent.SCORING_WEIGHTS is not None, "Agent constants loaded")
            
        except Exception as e:
            await self.assert_true(False, f"P1 Test Exception: {str(e)}")

    async def test_p2_pseo(self):
        """Test P2: pSEO Factory"""
        logger.info("--- Testing P2: pSEO ---")
        try:
            # 1. Dimension Model
            model = DimensionModel("test_model")
            dim = Dimension(DimensionType.MATERIAL, "Material")
            dim.add_value(DimensionValue("steel", "Steel", "steel"))
            dim.add_value(DimensionValue("wood", "Wood", "wood"))
            model.add_dimension(dim)
            
            combos = model.generate_all_combinations()
            await self.assert_true(len(combos) == 2, "Dimension combination count correct")
            
            # 2. Factory
            template = PageTemplate("tpl_1", "Test Template")
            factory = pSEOFactory(model, template, FactoryConfig(enable_quality_gate=False, deduplicate=False))
            
            # Factory generation
            pages = await factory.generate_all_pages()
            await self.assert_true(pages.success_count == 2, "Factory generation success")
            await self.assert_true(pages.generated_pages[0]["slug"] == "steel", "Slug generation correct")
            
        except Exception as e:
            await self.assert_true(False, f"P2 Test Exception: {str(e)}")

    async def test_supplementary(self):
        """Test Supplementary: RAG & Webhook"""
        logger.info("--- Testing Supplementary ---")
        try:
            # 1. RAG
            from src.core.rag import KnowledgeBase
            kb = KnowledgeBase(storage_path="tests/data/rag_test")
            doc_id = await kb.add_document("The sun rises in the east.", metadata={"source": "test"})
            
            results = await kb.search("sun")
            await self.assert_true(len(results) > 0, "RAG search returned results")
            await self.assert_true("sun" in results[0][0].content.lower(), "RAG content match")
            
            # 2. Webhook
            from src.integrations.webhook_adapter import WebhookAdapter
            # Use a dummy URL, expected to fail connection but verify class structure
            adapter = WebhookAdapter("http://localhost:9999/webhook")
            await self.assert_true(hasattr(adapter, "publish_content"), "WebhookAdapter has publish method")
            
        except Exception as e:
            await self.assert_true(False, f"Supplementary Test Exception: {str(e)}")

    async def test_p3_conversion(self):
        """Test P3: Conversion Tracking"""
        logger.info("--- Testing P3: Conversion ---")
        try:
            # 1. CTA Recommendation
            cta_engine = CTARecommendationEngine()
            ctas = cta_engine.recommend_ctas(UserIntent.COMMERCIAL, "product")
            await self.assert_true(len(ctas) > 0, "CTA recommendations returned")
            
            # 2. Tracking
            tracker = ConversionTracker()
            tracker.track_event(ConversionEvent(
                event_id="1", event_type=ConversionEventType.PAGEVIEW, 
                user_id="u1", session_id="s1", page_url="/page1"
            ))
            tracker.track_event(ConversionEvent(
                event_id="2", event_type=ConversionEventType.CLICK, 
                user_id="u1", session_id="s1", page_url="/page1"
            ))
            
            journey = tracker.get_journey("s1")
            await self.assert_true(len(journey) == 2, "Journey tracking correct")
            
        except Exception as e:
            await self.assert_true(False, f"P3 Test Exception: {str(e)}")

    def print_summary(self):
        logger.info("\n=== Integration Test Summary ===")
        for detail in self.results["details"]:
            logger.info(detail)
        logger.info(f"\nPassed: {self.results['passed']}")
        logger.info(f"Failed: {self.results['failed']}")
        
        if self.results['failed'] > 0:
            logger.error("❌ TEST SUITE FAILED")
        else:
            logger.info("✅ TEST SUITE PASSED")

if __name__ == "__main__":
    tester = IntegrationTester()
    asyncio.run(tester.run_all())
