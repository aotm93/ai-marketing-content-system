"""
Test suite for improvements and repairs documented in:
- IMPROVEMENT_COMPLETE.md
- REPAIR_COMPLETE.md

Tests the new GSC quota tracking, indexing status, and other enhanced features.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, date, timedelta

# Mock Environment Variables for Settings to load without .env
os.environ["PRIMARY_AI_API_KEY"] = "mock_key"
os.environ["DATABASE_URL"] = "sqlite:///test_improvements.db"
os.environ["WORDPRESS_URL"] = "http://mock.com"
os.environ["WORDPRESS_USERNAME"] = "mock"
os.environ["WORDPRESS_PASSWORD"] = "mock"
os.environ["ADMIN_PASSWORD"] = "mock"
os.environ["ADMIN_SESSION_SECRET"] = "mock"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ImprovementsTester:
    """Test runner for improvements and repairs"""
    
    def __init__(self):
        self.results = {"passed": 0, "failed": 0, "details": []}

    async def run_all(self):
        logger.info("=" * 60)
        logger.info("Starting Improvements and Repairs Test Suite...")
        logger.info("=" * 60)
        
        await self.test_gsc_usage_models()
        await self.test_gsc_usage_tracker()
        await self.test_indexing_status_model()
        await self.test_index_checker_service()
        await self.test_content_action_model()
        await self.test_indexnow_client()
        await self.test_opportunities_api_structure()
        await self.test_api_routers_import()
        
        self.print_summary()
        return self.results["failed"] == 0

    async def assert_true(self, condition: bool, message: str):
        if condition:
            self.results["passed"] += 1
            self.results["details"].append(f"✅ {message}")
            logger.info(f"✅ {message}")
        else:
            self.results["failed"] += 1
            self.results["details"].append(f"❌ {message}")
            logger.error(f"❌ {message}")

    # ==================== GSC Usage Models ====================
    
    async def test_gsc_usage_models(self):
        """Test GSC API Usage models from IMPROVEMENT_COMPLETE.md"""
        logger.info("\n--- Testing GSC Usage Models ---")
        try:
            from src.models.gsc_data import GSCApiUsage, GSCQuotaStatus
            
            # Test GSCApiUsage fields
            await self.assert_true(hasattr(GSCApiUsage, 'usage_date'), "GSCApiUsage has usage_date field")
            await self.assert_true(hasattr(GSCApiUsage, 'call_type'), "GSCApiUsage has call_type field")
            await self.assert_true(hasattr(GSCApiUsage, 'rows_fetched'), "GSCApiUsage has rows_fetched field")
            await self.assert_true(hasattr(GSCApiUsage, 'api_calls'), "GSCApiUsage has api_calls field")
            await self.assert_true(hasattr(GSCApiUsage, 'response_time_ms'), "GSCApiUsage has response_time_ms field")
            await self.assert_true(hasattr(GSCApiUsage, 'success'), "GSCApiUsage has success field")
            
            # Test GSCQuotaStatus fields
            await self.assert_true(hasattr(GSCQuotaStatus, 'quota_date'), "GSCQuotaStatus has quota_date field")
            await self.assert_true(hasattr(GSCQuotaStatus, 'daily_limit'), "GSCQuotaStatus has daily_limit field")
            await self.assert_true(hasattr(GSCQuotaStatus, 'used_today'), "GSCQuotaStatus has used_today field")
            await self.assert_true(hasattr(GSCQuotaStatus, 'status'), "GSCQuotaStatus has status field")
            
            # Test GSCQuotaStatus methods
            await self.assert_true(hasattr(GSCQuotaStatus, 'usage_percentage'), "GSCQuotaStatus has usage_percentage property")
            await self.assert_true(hasattr(GSCQuotaStatus, 'update_status'), "GSCQuotaStatus has update_status method")
            
        except Exception as e:
            await self.assert_true(False, f"GSC Usage Models Exception: {str(e)}")

    async def test_gsc_usage_tracker(self):
        """Test GSCUsageTracker service from IMPROVEMENT_COMPLETE.md"""
        logger.info("\n--- Testing GSC Usage Tracker Service ---")
        try:
            from src.services.gsc_usage_tracker import GSCUsageTracker
            
            # Test class constants
            await self.assert_true(hasattr(GSCUsageTracker, 'DEFAULT_DAILY_LIMIT'), "GSCUsageTracker has DEFAULT_DAILY_LIMIT")
            await self.assert_true(hasattr(GSCUsageTracker, 'WARNING_THRESHOLD'), "GSCUsageTracker has WARNING_THRESHOLD")
            await self.assert_true(hasattr(GSCUsageTracker, 'CRITICAL_THRESHOLD'), "GSCUsageTracker has CRITICAL_THRESHOLD")
            
            # Test methods
            await self.assert_true(hasattr(GSCUsageTracker, 'log_api_call'), "GSCUsageTracker has log_api_call method")
            await self.assert_true(hasattr(GSCUsageTracker, 'get_quota_status'), "GSCUsageTracker has get_quota_status method")
            await self.assert_true(hasattr(GSCUsageTracker, 'check_quota_available'), "GSCUsageTracker has check_quota_available method")
            await self.assert_true(hasattr(GSCUsageTracker, 'get_usage_history'), "GSCUsageTracker has get_usage_history method")
            await self.assert_true(hasattr(GSCUsageTracker, 'get_usage_by_type'), "GSCUsageTracker has get_usage_by_type method")
            
            # Test thresholds values
            await self.assert_true(GSCUsageTracker.WARNING_THRESHOLD == 0.80, "Warning threshold is 80%")
            await self.assert_true(GSCUsageTracker.CRITICAL_THRESHOLD == 0.90, "Critical threshold is 90%")
            await self.assert_true(GSCUsageTracker.DEFAULT_DAILY_LIMIT == 2000, "Default daily limit is 2000")
            
        except Exception as e:
            await self.assert_true(False, f"GSC Usage Tracker Exception: {str(e)}")

    # ==================== Indexing Status ====================
    
    async def test_indexing_status_model(self):
        """Test IndexingStatus model from IMPROVEMENT_COMPLETE.md"""
        logger.info("\n--- Testing Indexing Status Model ---")
        try:
            from src.models.indexing_status import IndexingStatus
            
            # Test fields exist
            await self.assert_true(hasattr(IndexingStatus, 'page_url'), "IndexingStatus has page_url field")
            await self.assert_true(hasattr(IndexingStatus, 'page_slug'), "IndexingStatus has page_slug field")
            await self.assert_true(hasattr(IndexingStatus, 'post_id'), "IndexingStatus has post_id field")
            await self.assert_true(hasattr(IndexingStatus, 'is_indexed'), "IndexingStatus has is_indexed field")
            await self.assert_true(hasattr(IndexingStatus, 'last_checked_at'), "IndexingStatus has last_checked_at field")
            await self.assert_true(hasattr(IndexingStatus, 'auto_retry_count'), "IndexingStatus has auto_retry_count field")
            await self.assert_true(hasattr(IndexingStatus, 'next_scheduled_check'), "IndexingStatus has next_scheduled_check field")
            await self.assert_true(hasattr(IndexingStatus, 'issue_severity'), "IndexingStatus has issue_severity field")
            
            # Test methods
            await self.assert_true(hasattr(IndexingStatus, 'to_dict'), "IndexingStatus has to_dict method")
            
        except Exception as e:
            await self.assert_true(False, f"Indexing Status Model Exception: {str(e)}")

    async def test_index_checker_service(self):
        """Test IndexChecker service from IMPROVEMENT_COMPLETE.md"""
        logger.info("\n--- Testing Index Checker Service ---")
        try:
            from src.services.index_checker import IndexChecker
            
            # Test class constants
            await self.assert_true(hasattr(IndexChecker, 'CHECK_INTERVAL_NEW'), "IndexChecker has CHECK_INTERVAL_NEW")
            await self.assert_true(hasattr(IndexChecker, 'CHECK_INTERVAL_PENDING'), "IndexChecker has CHECK_INTERVAL_PENDING")
            await self.assert_true(hasattr(IndexChecker, 'CHECK_INTERVAL_INDEXED'), "IndexChecker has CHECK_INTERVAL_INDEXED")
            await self.assert_true(hasattr(IndexChecker, 'MAX_AUTO_RETRIES'), "IndexChecker has MAX_AUTO_RETRIES")
            
            # Test methods
            await self.assert_true(hasattr(IndexChecker, 'check_page_index_status'), "IndexChecker has check_page_index_status method")
            await self.assert_true(hasattr(IndexChecker, 'run_scheduled_checks'), "IndexChecker has run_scheduled_checks method")
            await self.assert_true(hasattr(IndexChecker, 'get_coverage_report'), "IndexChecker has get_coverage_report method")
            await self.assert_true(hasattr(IndexChecker, 'get_pages_needing_attention'), "IndexChecker has get_pages_needing_attention method")
            await self.assert_true(hasattr(IndexChecker, 'register_page_submission'), "IndexChecker has register_page_submission method")
            
        except Exception as e:
            await self.assert_true(False, f"Index Checker Service Exception: {str(e)}")

    # ==================== Content Action Model ====================
    
    async def test_content_action_model(self):
        """Test ContentAction model from REPAIR_COMPLETE.md"""
        logger.info("\n--- Testing Content Action Model ---")
        try:
            from src.models.job_runs import ContentAction
            
            # Test fields
            await self.assert_true(hasattr(ContentAction, 'action_type'), "ContentAction has action_type field")
            await self.assert_true(hasattr(ContentAction, 'post_id'), "ContentAction has post_id field")
            await self.assert_true(hasattr(ContentAction, 'before_snapshot'), "ContentAction has before_snapshot field")
            await self.assert_true(hasattr(ContentAction, 'after_snapshot'), "ContentAction has after_snapshot field")
            await self.assert_true(hasattr(ContentAction, 'metrics_before'), "ContentAction has metrics_before field")
            await self.assert_true(hasattr(ContentAction, 'metrics_after'), "ContentAction has metrics_after field")
            await self.assert_true(hasattr(ContentAction, 'status'), "ContentAction has status field")
            
            # Test methods
            await self.assert_true(hasattr(ContentAction, 'can_rollback'), "ContentAction has can_rollback method")
            await self.assert_true(hasattr(ContentAction, 'calculate_impact'), "ContentAction has calculate_impact method")
            await self.assert_true(hasattr(ContentAction, 'to_dict'), "ContentAction has to_dict method")
            
        except Exception as e:
            await self.assert_true(False, f"Content Action Model Exception: {str(e)}")

    # ==================== IndexNow Client ====================
    
    async def test_indexnow_client(self):
        """Test IndexNow client from REPAIR_COMPLETE.md"""
        logger.info("\n--- Testing IndexNow Client ---")
        try:
            from src.integrations.indexnow import IndexNowClient
            
            # Test class structure
            await self.assert_true(hasattr(IndexNowClient, 'ENDPOINTS'), "IndexNowClient has ENDPOINTS")
            await self.assert_true(hasattr(IndexNowClient, 'submit_url'), "IndexNowClient has submit_url method")
            await self.assert_true(hasattr(IndexNowClient, 'submit_urls'), "IndexNowClient has submit_urls method")
            
            # Test endpoint list
            await self.assert_true(len(IndexNowClient.ENDPOINTS) >= 3, "IndexNowClient has at least 3 endpoints")
            
            # Test instantiation
            client = IndexNowClient(api_key="test-key", host="example.com")
            await self.assert_true(client.api_key == "test-key", "IndexNowClient stores api_key correctly")
            await self.assert_true(client.host == "example.com", "IndexNowClient stores host correctly")
            
        except Exception as e:
            await self.assert_true(False, f"IndexNow Client Exception: {str(e)}")

    # ==================== Opportunities API ====================
    
    async def test_opportunities_api_structure(self):
        """Test Opportunities API structure from REPAIR_COMPLETE.md"""
        logger.info("\n--- Testing Opportunities API Structure ---")
        try:
            from src.api.opportunities import (
                OpportunityTypeEnum, OpportunityStatusEnum, 
                SortFieldEnum, ActionTypeEnum,
                OpportunityResponse, OpportunityStatsResponse
            )
            
            # Test enums exist
            await self.assert_true(hasattr(OpportunityTypeEnum, 'CONTENT_GAP'), "OpportunityTypeEnum has CONTENT_GAP")
            await self.assert_true(hasattr(OpportunityTypeEnum, 'CTR_OPTIMIZE'), "OpportunityTypeEnum has CTR_OPTIMIZE")
            await self.assert_true(hasattr(OpportunityStatusEnum, 'PENDING'), "OpportunityStatusEnum has PENDING")
            await self.assert_true(hasattr(OpportunityStatusEnum, 'COMPLETED'), "OpportunityStatusEnum has COMPLETED")
            await self.assert_true(hasattr(SortFieldEnum, 'SCORE'), "SortFieldEnum has SCORE")
            await self.assert_true(hasattr(ActionTypeEnum, 'GENERATE'), "ActionTypeEnum has GENERATE")
            
            # Test response models
            await self.assert_true(hasattr(OpportunityResponse, 'model_fields'), "OpportunityResponse is a Pydantic model")
            await self.assert_true(hasattr(OpportunityStatsResponse, 'model_fields'), "OpportunityStatsResponse is a Pydantic model")
            
        except Exception as e:
            await self.assert_true(False, f"Opportunities API Structure Exception: {str(e)}")

    # ==================== API Routers ====================
    
    async def test_api_routers_import(self):
        """Test all API routers can be imported"""
        logger.info("\n--- Testing API Routers Import ---")
        try:
            from src.api.gsc import router as gsc_router
            await self.assert_true(gsc_router is not None, "GSC API router imports successfully")
            
            from src.api.indexing import router as indexing_router
            await self.assert_true(indexing_router is not None, "Indexing API router imports successfully")
            
            from src.api.opportunities import router as opp_router
            await self.assert_true(opp_router is not None, "Opportunities API router imports successfully")
            
            from src.api.admin import router as admin_router
            await self.assert_true(admin_router is not None, "Admin API router imports successfully")
            
        except Exception as e:
            await self.assert_true(False, f"API Routers Import Exception: {str(e)}")

    def print_summary(self):
        logger.info("\n" + "=" * 60)
        logger.info("IMPROVEMENTS & REPAIRS TEST SUMMARY")
        logger.info("=" * 60)
        
        for detail in self.results["details"]:
            logger.info(detail)
        
        logger.info(f"\nTotal Passed: {self.results['passed']}")
        logger.info(f"Total Failed: {self.results['failed']}")
        
        if self.results['failed'] > 0:
            logger.error("❌ IMPROVEMENTS TEST SUITE FAILED")
        else:
            logger.info("✅ IMPROVEMENTS TEST SUITE PASSED")


if __name__ == "__main__":
    tester = ImprovementsTester()
    success = asyncio.run(tester.run_all())
    sys.exit(0 if success else 1)
