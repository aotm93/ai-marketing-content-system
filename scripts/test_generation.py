import asyncio
import os
import sys
import logging

# Add project root to path BEFORE importing src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings
from src.scheduler.jobs import content_generation_job

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_generation():
    """
    Test the content generation logic completely.
    This will attempt to run the job end-to-end.
    """
    print("🚀 Starting Content Generation Test...")
    
    # 1. Mock Configuration
    mock_config = {
        "auto_publish": False, # Safer for testing
        "require_seo_score": 60,
        "max_tokens_per_day": 100000
    }
    
    print(f"🔧 Config: {mock_config}")
    
    # 2. Check Environment
    if not settings.primary_ai_api_key:
        print("❌ Error: PRIMARY_AI_API_KEY is not set in .env")
        return

    print(f"🤖 AI Provider: {settings.primary_ai_provider}")
    print(f"🔍 GSC Site: {settings.gsc_site_url or 'Not Set (Ok, using fallback)'}")
    print(f"🔑 Keyword API: {'Configured' if settings.keyword_api_key else 'Not Set (Ok, using fallback)'}")

    try:
        # 3. Execute Job
        print("\n⏳ Running job... (This may take 30-60 seconds)")
        result = await content_generation_job({"config": mock_config})
        
        # 4. Report Results
        print("\n✅ Job Completed!")
        print(f"Status: {result.get('status')}")
        
        if result.get("error"):
            print(f"❌ Error: {result.get('error')}")
            
        print("\n📝 Steps Execution:")
        for step in result.get("steps", []):
            status_val = step.get('status', 'unknown')
            status_icon = "✅" if status_val in ['completed', 'success'] else "❌"
            print(f"{status_icon} Step: {step.get('step', 'Unknown Step')}")
            print(f"   Data: {step.get('data')}")
            
        if result.get("post_url"):
            print(f"\n🔗 Published URL: {result.get('post_url')}")
            print(f"🆔 Post ID: {result.get('post_id')}")
            
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Add project root to path
    sys.path.append(os.getcwd())
    
    # Run async test
    asyncio.run(test_generation())
