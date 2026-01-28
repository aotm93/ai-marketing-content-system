
import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("smoke_test")

import pytest

@pytest.mark.asyncio
async def test_connectivity():
    print("\n[RUNNING SYSTEM SMOKE TEST (REAL CONNECTIONS)]\n" + "="*50)
    
    # 1. Load Env
    load_dotenv()
    
    # Fix import path for src module
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

    # 2. Redis Check
    print("\n[1/3] Testing Redis Connection...")
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        print("[FAIL] REDIS_URL not set in .env")
    else:
        try:
            import redis
            r = redis.from_url(redis_url, socket_timeout=3)
            r.ping()
            print(f"[OK] Redis Connected: {redis_url}")
            
            # Test Persistence Logic
            r.set("smoke_test_key", "active")
            val = r.get("smoke_test_key")
            if val == b"active" or val == "active":
                 print("[OK] Redis Read/Write: OK")
            else:
                 print(f"[FAIL] Redis Read/Write Failed. Got: {val}")
        except Exception as e:
            print(f"[FAIL] Redis Failed: {e}")
            print("   -> Tip: Ensure Redis server is running (docker run -d -p 6379:6379 redis)")

    # 3. WordPress Check
    print("\n[2/3] Testing WordPress API...")
    wp_url = os.getenv("WORDPRESS_URL", "").rstrip("/")
    wp_user = os.getenv("WORDPRESS_USERNAME")
    wp_pass = os.getenv("WORDPRESS_PASSWORD")
    
    if not all([wp_url, wp_user, wp_pass]):
        print("[FAIL] WordPress credentials missing in .env")
    else:
        try:
            import httpx
            import base64
            
            creds = f"{wp_user}:{wp_pass}"
            auth = base64.b64encode(creds.encode()).decode()
            
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                # Test Basic Auth & Permissions
                resp = await client.get(
                    f"{wp_url}/wp-json/wp/v2/users/me",
                    headers={"Authorization": f"Basic {auth}"}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"[OK] WordPress Connected: {data.get('name')} (Role: {data.get('roles')})")
                else:
                    print(f"[FAIL] WordPress Auth Failed: {resp.status_code}")
                    print(f"   Response: {resp.text[:200]}")
        except Exception as e:
             print(f"[FAIL] WordPress Connection Error: {e}")

    # 4. Mock Generation Pipeline Check
    print("\n[3/3] Testing pSEO Factory Initialization...")
    try:
        from src.pseo.page_factory import BatchJobQueue
        queue = BatchJobQueue()
        status = queue.get_queue_status()
        print(f"[OK] Factory Initialized. Queue Status: {status}")
        print(f"   Persistence Mode: {status.get('persistence', 'unknown')}")
    except Exception as e:
        print(f"[FAIL] Factory Init Failed: {e}")

    print("\n" + "="*50 + "\nTest Complete.\n")

if __name__ == "__main__":
    asyncio.run(test_connectivity())
