import os
import time
import httpx

# Set this to your live domain (e.g., https://api.scrappie.tech) if testing in production
BASE_URL = os.getenv("API_URL", "https://scrappie.tech")
TARGET_URL = "https://gopanda.in"

def run_tests():
    print(f"🚀 Starting API Tests against {TARGET_URL} 🚀\n")
    
    # Using httpx since it's already in your requirements.txt
    client = httpx.Client(base_url=BASE_URL, timeout=60.0)

    # 1. Get Plans
    print("1️⃣  Testing GET /v1/plans...")
    res = client.get("/v1/plans")
    print(f"Status: {res.status_code}")
    
    # 2. Create API Key
    print("\n2️⃣  Testing POST /v1/keys/create...")
    res = client.post("/v1/keys/create", json={"email": "humayunroshid2@gmail.com", "plan": "free"})
    print(f"Status: {res.status_code}")
    
    api_key = res.json().get("api_key")
    if not api_key:
        print("❌ Failed to get API key. Is your Redis running?")
        return
    
    print(f"✅ Generated Test API Key: {api_key}")
    
    # Attach the API key to all future requests
    client.headers.update({"x-api-key": api_key})

    # 3. Check Usage
    print("\n3️⃣  Testing GET /v1/keys/usage...")
    res = client.get("/v1/keys/usage")
    print(f"Status: {res.status_code} | Requests Used: {res.json().get('requests_used')}")
    
    # 4. Sync Scrape (With Markdown & JSON extraction)
    print("\n4️⃣  Testing POST /v1/scrape...")
    res = client.post("/v1/scrape", json={
        "url": TARGET_URL, 
        "extract_markdown": True,
        "extract_json": True
    })
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        md = data.get("markdown", "")
        print(f"✅ Success! Page Title: {data.get('title')}")
        print(f"✅ Extracted {len(md)} characters of markdown.")
    else:
        print("Response:", res.text)

    # 5. Sync Browser (Simulate human interaction & Screenshot)
    print("\n5️⃣  Testing POST /v1/browser...")
    res = client.post("/v1/browser", json={
        "url": TARGET_URL,
        "steps": [{"action": "scroll", "y": 1000}],  # Scroll down to load lazy elements
        "screenshot": True
    })
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        ss = res.json().get("screenshot_base64", "")
        print(f"✅ Success! Captured screenshot (Base64 length: {len(ss)}).")

    # 6. Async Scrape (Testing RQ Worker & Redis Queue)
    print("\n6️⃣  Testing POST /v1/scrape/async...")
    res = client.post("/v1/scrape/async", json={"url": TARGET_URL})
    print(f"Status: {res.status_code}")
    job_id = res.json().get("job_id")
    
    if job_id:
        print(f"✅ Queued Job ID: {job_id}. Polling for completion...")
        # Poll the job status endpoint every 2 seconds
        for i in range(15):
            time.sleep(2)
            res = client.get(f"/v1/jobs/{job_id}")
            status = res.json().get("status")
            print(f"   [{i+1}/15] Job Status: {status}")
            
            if status in ["finished", "failed"]:
                print(f"✅ Job completed with status: {status}")
                break
        else:
            print("⚠️ Job polling timed out (took longer than 30s).")
    
    print("\n🎉 All tests completed successfully!")

if __name__ == "__main__":
    run_tests()