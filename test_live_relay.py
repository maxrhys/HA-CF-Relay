#!/usr/bin/env python3
"""
End-to-End Live Verification Test for HA-CF-Relay
Uses Python standard library (urllib) to test live Cloudflare Worker endpoints.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime

def load_env(env_path):
    env_vars = {}
    if not os.path.exists(env_path):
        print(f"Error: {env_path} not found.")
        sys.exit(1)
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                env_vars[k] = v
    return env_vars

def run_tests():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, ".env")
    env = load_env(env_path)

    secret_token = env.get("SECRET_TOKEN", "")
    worker_url = env.get("WORKER_URL", "").rstrip("/")

    if not secret_token or "PASTE_" in secret_token:
        print("❌ Error: SECRET_TOKEN is not set in .env")
        sys.exit(1)
    if not worker_url or "PASTE_" in worker_url:
        print("❌ Error: WORKER_URL is not set in .env")
        sys.exit(1)

    print(f"=== Testing Live HA-CF-Relay at: {worker_url} ===\n")

    # Test 1: Unauthorized POST /update
    print("Test 1: Testing unauthorized POST /update (expected 401)...")
    update_url = f"{worker_url}/update"
    req = urllib.request.Request(
        update_url,
        data=json.dumps({"test": "data"}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid_token_12345"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            print(f"❌ Failed: Expected 401 Unauthorized, but got HTTP {resp.status}")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("✅ Passed: 401 Unauthorized received as expected.")
        else:
            print(f"❌ Failed: Unexpected HTTP status {e.code}")

    # Test 2: Authorized POST /update
    print("\nTest 2: Testing authorized POST /update with sensor telemetry...")
    now_iso = datetime.now().isoformat()
    test_payload = {
        "unit_test_relay": {
            "name": "Live Test Unit",
            "updated_at": now_iso,
            "sensors": {
                "temperature": {"value": 23.4, "unit": "°C"},
                "humidity": {"value": 52.0, "unit": "%"}
            }
        }
    }
    req = urllib.request.Request(
        update_url,
        data=json.dumps(test_payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {secret_token}"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            if resp.status == 200 and data.get("status") == "ok":
                print(f"✅ Passed: Telemetry ingested successfully! Response: {body}")
            else:
                print(f"❌ Failed: Unexpected response HTTP {resp.status} - {body}")
    except Exception as e:
        print(f"❌ Failed: Could not post telemetry: {e}")
        return

    # Test 3: Public GET /data
    print("\nTest 3: Testing public GET /data...")
    data_url = f"{worker_url}/data"
    req = urllib.request.Request(data_url, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            cors_header = resp.headers.get("Access-Control-Allow-Origin")
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            if "unit_test_relay" in data:
                print(f"✅ Passed: GET /data returned ingested device! (CORS Origin: {cors_header})")
            else:
                print(f"❌ Failed: 'unit_test_relay' not found in store: {body}")
    except Exception as e:
        print(f"❌ Failed: GET /data failed: {e}")

    # Test 4: Filtered GET /data?device=unit_test_relay
    print("\nTest 4: Testing filtered GET /data?device=unit_test_relay...")
    filter_url = f"{worker_url}/data?device=unit_test_relay"
    req = urllib.request.Request(filter_url, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            if data.get("name") == "Live Test Unit":
                print(f"✅ Passed: Filtered device query succeeded! Details: {data['sensors']}")
            else:
                print(f"❌ Failed: Device filter response unexpected: {body}")
    except Exception as e:
        print(f"❌ Failed: Filtered query failed: {e}")

    print("\n=== All Live Tests Completed! ===")

if __name__ == "__main__":
    run_tests()
