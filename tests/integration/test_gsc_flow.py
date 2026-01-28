
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from datetime import date

from src.api.main import app
from src.core.database import SessionLocal, init_db
from src.models.gsc_data import GSCQuery as GSCQueryDB
from src.api.gsc import get_gsc_client
from src.integrations.gsc_client import GSCQuery

# Mock GSC Client
mock_gsc = MagicMock()
mock_gsc.health_check.return_value = {"status": "connected", "mock": True}
mock_gsc.get_search_analytics.return_value = [
    GSCQuery(
        date="2023-10-01",
        query="test query",
        page="https://example.com/test",
        clicks=10,
        impressions=100,
        ctr=0.1,
        position=5.5
    )
]
mock_gsc.get_low_hanging_fruits.return_value = [
    GSCQuery(
        date="2023-10-01",
        query="opportunity query",
        page="https://example.com/opp",
        clicks=50,
        impressions=1000,
        ctr=0.05,
        position=8.0
    )
]

from src.core.auth import get_current_admin

def override_get_gsc_client():
    return mock_gsc

def override_get_current_admin():
    return {"username": "admin", "role": "admin"}

app.dependency_overrides[get_gsc_client] = override_get_gsc_client
app.dependency_overrides[get_current_admin] = override_get_current_admin

def test_gsc_flow():
    print("\n[START GSC FLOW TEST]\n" + "="*50)
    
    # Clean DB
    import os
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    
    # Clean DB
    import os
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    
    # 2. Test status (Lifespan will init DB)
    with TestClient(app) as client:
        print("\n[1/3] Testing Status...")
        resp = client.get("/gsc/status")
        print(f"Status Response: {resp.json()}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "connected"
        
        # 3. Test Sync
        print("\n[2/3] Testing Sync...")
        resp = client.post("/gsc/sync", json={"days": 7})
        print(f"Sync Response: {resp.json()}")
        assert resp.status_code == 200
        assert resp.json()["success"] == True
        assert resp.json()["rows_fetched"] == 1
        
        # Verify DB
        db = SessionLocal()
        count = db.query(GSCQueryDB).count()
        print(f"Rows in DB: {count}")
        assert count >= 1
        
        # 4. Test Opportunities
        print("\n[3/3] Testing Opportunities...")
        resp = client.get("/gsc/opportunities")
        data = resp.json()
        print(f"Opportunities found: {len(data)}")
        if len(data) > 0:
            print(f"First opp: {data[0]['query']} (Score: {data[0]['potential_score']})")
        assert len(data) > 0
        
    print("\n" + "="*50 + "\nTest Complete.\n")

if __name__ == "__main__":
    test_gsc_flow()
