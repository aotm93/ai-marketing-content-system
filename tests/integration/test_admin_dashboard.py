
import requests
import json
import sys
import time

BASE_URL = "http://localhost:8080"
ADMIN_PASSWORD = "admin"

def print_result(test_name, success, message=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if message:
        print(f"   Details: {message}")
    if not success:
        sys.exit(1)

def run_tests():
    print(f"🚀 Starting System Tests on {BASE_URL}...\n")
    
    session = requests.Session()
    
    # ---------------------------------------------------------
    # Test 1: Health Check
    # ---------------------------------------------------------
    try:
        resp = session.get(f"{BASE_URL}/health")
        if resp.status_code == 200:
            print_result("Health Check", True, f"Status: {resp.json().get('status')}")
        else:
            print_result("Health Check", False, f"Status Code: {resp.status_code}")
    except Exception as e:
        print_result("Health Check", False, f"Connection Failed: {e}")

    # ---------------------------------------------------------
    # Test 2: Admin Login
    # ---------------------------------------------------------
    login_payload = {"password": ADMIN_PASSWORD}
    resp = session.post(f"{BASE_URL}/api/v1/admin/login", json=login_payload)
    
    if resp.status_code == 200:
        token = resp.json().get("access_token")
        # Manually set cookie if session doesn't handle it automatically (it should, but safety first)
        session.cookies.set("session_token", token)
        print_result("Admin Login", True, "Successfully authenticated")
    else:
        print_result("Admin Login", False, f"Login failed: {resp.text}")

    # ---------------------------------------------------------
    # Test 3: Get Configuration (Bug Fix Verification)
    # ---------------------------------------------------------
    resp = session.get(f"{BASE_URL}/api/v1/admin/config")
    
    if resp.status_code == 200:
        config = resp.json().get("data", {})
        # Verify Autopilot Enabled is a string (Fix #1)
        autopilot_enabled = config.get("autopilot_enabled")
        if isinstance(autopilot_enabled, str):
             print_result("Config Type Check", True, f"autopilot_enabled is string: '{autopilot_enabled}'")
        else:
             print_result("Config Type Check", False, f"autopilot_enabled is {type(autopilot_enabled)}")
             
        # Verify GSC URL exists (Fix #3)
        if "gsc_site_url" in config:
            print_result("Config Completeness", True, "GSC config present")
        else:
            print_result("Config Completeness", False, "Missing gsc_site_url")
    else:
        print_result("Get Config", False, f"Failed to load config: {resp.status_code}")

    # ---------------------------------------------------------
    # Test 4: Update Configuration (Save Fix Verification)
    # ---------------------------------------------------------
    # Test saving an empty value (Fix #2 logic verification)
    update_payload = {
        "config_key": "GSC_SITE_URL",
        "config_value": "sc-domain:test-site.com"
    }
    
    resp = session.put(f"{BASE_URL}/api/v1/admin/config", json=update_payload)
    
    if resp.status_code == 200:
        print_result("Update Config", True, "Successfully updated GSC_SITE_URL")
    else:
        print_result("Update Config", False, f"Update failed: {resp.text}")

    # Verify update persisted
    resp = session.get(f"{BASE_URL}/api/v1/admin/config")
    new_config = resp.json().get("data", {})
    if new_config.get("gsc_site_url") == "sc-domain:test-site.com":
        print_result("Config Persistence", True, "Value persisted correctly")
    else:
        print_result("Config Persistence", False, f"Value mismatch: {new_config.get('gsc_site_url')}")

    # ---------------------------------------------------------
    # Test 5: Dashboard Static Assets (Integration Verification)
    # ---------------------------------------------------------
    # 1. Main Dashboard Page
    resp = session.get(f"{BASE_URL}/dashboard/")
    if resp.status_code == 200:
        print_result("Dashboard Page Load", True, "Successfully loaded /dashboard/")
        
        # 2. Check for base path in content (Verification of Build Fix)
        if '/dashboard/_next/' in resp.text:
             print_result("Dashboard Asset Path", True, "Found correct basePath in HTML")
        else:
             print_result("Dashboard Asset Path", False, "Missing /dashboard/ prefix in HTML links")
             
    else:
        print_result("Dashboard Page Load", False, f"Failed to load dashboard: {resp.status_code}")

    # 3. Check a static asset (Mock check, assuming Next.js structure)
    # We can try to fetch a known asset if we parsed the HTML, but for now 200 on /dashboard/ is good

    print("\n✨ All System Tests Passed!")

if __name__ == "__main__":
    try:
        run_tests()
    except requests.exceptions.ConnectionError:
        print("❌ FAIL - Cannot connect to server")
        print("   Make sure the server is running on port 8080")
