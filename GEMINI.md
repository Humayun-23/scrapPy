# Scrappie Jobs API — Full Build Instructions for Gemini
> This document gives you everything you need to build the Indian Job Market Data API on top of the existing Scrappie infrastructure.

---

## Who You Are Helping

A student indie developer in India who has already built and deployed a web scraping API called Scrappie. The infrastructure is live at scrappie.tech. You are helping him pivot the product to a **Indian Job Market Data API** — scraping Naukri.com and returning structured job data via a clean REST API.

---

## What Is Already Built And Working

### Live Infrastructure
- **Domain:** scrappie.tech (SSL active, Nginx running)
- **Server:** DigitalOcean Droplet, Ubuntu 22.04, 4GB RAM, 2 vCPU
- **IP:** 168.144.113.171
- **SSH:** `ssh scrappy@168.144.113.171` (non-root user with sudo)
- **Project path:** `~/scrapPy/`
- **All services run in Docker Compose**

### Working Services
```
scrappy-api     → FastAPI app on port 8000 (internal)
scrappy-redis   → Redis 7 on port 6379 (internal)
scrappy-nginx   → Nginx on ports 80 + 443 (public)
```

### Existing File Structure
```
~/scrapPy/
├── app/
│   ├── main.py       ← FastAPI app — MODIFY this
│   ├── scraper.py    ← Old CloakBrowser scraper — REPLACE this
│   ├── proxy.py      ← Hysteria2 proxy — leave alone
│   └── billing.py    ← Dodo Payments billing — leave alone
├── nginx/
│   └── nginx.conf    ← leave alone
├── docker-compose.yml
├── Dockerfile        ← MODIFY to add Playwright
├── requirements.txt  ← MODIFY to add new dependencies
└── .env
```

### Existing API Key System (Already Working — Do Not Break)
Redis stores API keys like this:
```
apikey:sk_xxx → {email, plan, created_at, active}
keys:email:user@email.com → {sk_xxx}
usage:sk_xxx:YYYY-MM → count
```

Plans already defined in main.py:
```python
PLANS = {
    "free":    {"requests": 100,     "price": 0},
    "starter": {"requests": 10_000,  "price": 49},
    "growth":  {"requests": 50_000,  "price": 149},
    "scale":   {"requests": 200_000, "price": 499},
}
```

Auth works via `x-api-key` header. The `verify_api_key` dependency in main.py handles this — do not change it.

---

## What You Need To Build

### The Goal
Replace the broken CloakBrowser scraper with a **Playwright-based Naukri.com scraper** and add 3 new job-specific API endpoints.

### New Endpoints To Add

**1. POST /v1/jobs/search**
```json
Request:
{
  "query": "python developer",
  "location": "bangalore",
  "experience_min": 2,
  "experience_max": 5,
  "limit": 50
}

Response:
{
  "success": true,
  "query": "python developer",
  "location": "bangalore",
  "total_found": 847,
  "returned": 50,
  "cached": true,
  "jobs": [
    {
      "title": "Senior Python Developer",
      "company": "Razorpay",
      "location": "Bangalore",
      "salary_min": 1800000,
      "salary_max": 2500000,
      "salary_currency": "INR",
      "experience": "2-5 years",
      "skills": ["Python", "Django", "AWS", "Redis"],
      "posted_at": "2026-05-19",
      "applicants": 234,
      "job_url": "https://www.naukri.com/...",
      "source": "naukri"
    }
  ],
  "requests_used": 1,
  "requests_remaining": 99
}
```

**2. POST /v1/jobs/salary**
```json
Request:
{
  "role": "data scientist",
  "location": "mumbai",
  "experience": 3
}

Response:
{
  "success": true,
  "role": "Data Scientist",
  "location": "Mumbai",
  "experience_years": 3,
  "salary_min": 1200000,
  "salary_max": 2000000,
  "salary_median": 1600000,
  "salary_p75": 1800000,
  "salary_currency": "INR",
  "sample_size": 143,
  "top_hiring_companies": ["Flipkart", "Swiggy", "CRED", "Meesho"],
  "top_skills_in_demand": ["Python", "ML", "SQL", "TensorFlow"]
}
```

**3. POST /v1/jobs/skills**
```json
Request:
{
  "category": "backend",
  "location": "india"
}

Response:
{
  "success": true,
  "category": "backend",
  "location": "india",
  "trending_skills": [
    {"skill": "Rust",   "job_count": 234,  "growth_30d": "+45%"},
    {"skill": "Go",     "job_count": 891,  "growth_30d": "+23%"},
    {"skill": "AWS",    "job_count": 4521, "growth_30d": "+12%"},
    {"skill": "Python", "job_count": 9823, "growth_30d": "+8%"}
  ]
}
```

---

## Exact Files To Create / Modify

### 1. CREATE: `app/jobs_scraper.py`
This is the core new file. It must:

**A. Scrape Naukri.com using Playwright + stealth**

Use this URL pattern for Naukri:
```
https://www.naukri.com/{query}-jobs-in-{location}?experience={exp_min}to{exp_max}
```

Example:
```
https://www.naukri.com/python-developer-jobs-in-bangalore?experience=2to5
```

The Naukri job card CSS selectors (as of 2026):
```
Job container:  .srp-jobtuple-wrapper  or  article.jobTuple
Job title:      a.title  or  .row1 .title
Company name:   .comp-name  or  .row2 a
Experience:     .exp-wrap  or  .row2 .experience
Salary:         .salary-estimate  or  .row2 .salary
Location:       .loc-wrap  or  .row2 .location
Skills:         .tags-gt li  or  ul.tags li
Posted date:    .job-post-day
Applicants:     .applied-count
Job URL:        a.title[href]
```

Note: Naukri updates their HTML occasionally. If selectors don't work, try inspecting the page and finding the right ones. Always include fallbacks.

**B. Parse salary strings into integers**

Naukri shows salary like:
- "8-12 Lacs PA" → salary_min: 800000, salary_max: 1200000
- "Not disclosed" → null
- "25-40 Lacs PA" → salary_min: 2500000, salary_max: 4000000
- "1.5-2.5 Lacs PA" → salary_min: 150000, salary_max: 250000

Parse using regex:
```python
import re

def parse_salary(salary_text: str) -> tuple:
    if not salary_text or 'not disclosed' in salary_text.lower():
        return None, None
    match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*lac', 
                      salary_text, re.IGNORECASE)
    if match:
        min_lac = float(match.group(1))
        max_lac = float(match.group(2))
        return int(min_lac * 100000), int(max_lac * 100000)
    return None, None
```

**C. Implement Redis caching**

Cache key format: `jobs:{query}:{location}:{exp_min}:{exp_max}`
TTL: 21600 seconds (6 hours)

Logic:
1. Check Redis for cached result
2. If found → return immediately (add `"cached": true` to response)
3. If not found → scrape Naukri → parse → store in Redis → return

**D. Use asyncio Semaphore to limit concurrent browsers**

Max 3 concurrent Playwright instances (server has 4GB RAM):
```python
_semaphore = asyncio.Semaphore(3)
```

**E. Full Playwright stealth setup**

```python
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def get_browser_page():
    p = await async_playwright().start()
    browser = await p.chromium.launch(
        headless=True,
        args=[
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-gpu',
            '--window-size=1920,1080',
        ]
    )
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/122.0.0.0 Safari/537.36',
        viewport={'width': 1920, 'height': 1080},
        locale='en-IN',
        timezone_id='Asia/Kolkata',
        extra_http_headers={
            'Accept-Language': 'en-IN,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
    )
    page = await context.new_page()
    await stealth_async(page)
    return p, browser, page
```

**F. Salary intelligence function**

Collect jobs for a role+location, aggregate salary data:
```python
async def get_salary_intelligence(role: str, location: str, experience: int):
    # Scrape jobs for this role
    jobs = await scrape_naukri(role, location, experience, experience + 2, limit=100)
    
    # Extract all salary data points
    salaries = []
    companies = []
    all_skills = []
    
    for job in jobs:
        if job.get('salary_min') and job.get('salary_max'):
            mid = (job['salary_min'] + job['salary_max']) / 2
            salaries.append(mid)
        if job.get('company'):
            companies.append(job['company'])
        if job.get('skills'):
            all_skills.extend(job['skills'])
    
    if not salaries:
        return None
    
    salaries.sort()
    n = len(salaries)
    
    # Count top companies and skills
    from collections import Counter
    top_companies = [c for c, _ in Counter(companies).most_common(5)]
    top_skills = [s for s, _ in Counter(all_skills).most_common(8)]
    
    return {
        "salary_min": int(min(salaries)),
        "salary_max": int(max(salaries)),
        "salary_median": int(salaries[n // 2]),
        "salary_p75": int(salaries[int(n * 0.75)]),
        "salary_currency": "INR",
        "sample_size": len(salaries),
        "top_hiring_companies": top_companies,
        "top_skills_in_demand": top_skills,
    }
```

**G. Skills trending function**

Skill categories to track:
```python
SKILL_CATEGORIES = {
    "backend":   ["Python", "Java", "Go", "Rust", "Node.js", "Django", "Spring", "FastAPI"],
    "frontend":  ["React", "Vue", "Angular", "TypeScript", "Next.js", "Svelte"],
    "devops":    ["AWS", "Docker", "Kubernetes", "Terraform", "CI/CD", "GCP", "Azure"],
    "data":      ["Python", "SQL", "Spark", "Kafka", "Airflow", "dbt", "Tableau"],
    "ml":        ["TensorFlow", "PyTorch", "Scikit-learn", "LangChain", "HuggingFace"],
    "mobile":    ["Flutter", "React Native", "Swift", "Kotlin", "Android", "iOS"],
}
```

For each skill in category, count how many jobs mention it. Return sorted by job count.

---

### 2. MODIFY: `app/main.py`

Add these imports at the top:
```python
from .jobs_scraper import scrape_naukri, get_salary_intelligence, get_skills_trending
```

Add these 3 new Pydantic models:
```python
class JobSearchRequest(BaseModel):
    query: str
    location: str = "india"
    experience_min: Optional[int] = 0
    experience_max: Optional[int] = 10
    limit: Optional[int] = 50

class SalaryRequest(BaseModel):
    role: str
    location: str = "india"
    experience: int = 3

class SkillsRequest(BaseModel):
    category: str = "backend"
    location: str = "india"
```

Add these 3 new route handlers:
```python
@app.post("/v1/jobs/search")
async def jobs_search(req: JobSearchRequest, auth: dict = Depends(verify_api_key)):
    """Search Indian job listings from Naukri.com"""
    try:
        start = time.time()
        result = await scrape_naukri(
            query=req.query,
            location=req.location,
            experience_min=req.experience_min,
            experience_max=req.experience_max,
            limit=req.limit,
        )
        elapsed = round(time.time() - start, 2)
        return {
            "success": True,
            "query": req.query,
            "location": req.location,
            "returned": len(result["jobs"]),
            "cached": result.get("cached", False),
            "elapsed_seconds": elapsed,
            "jobs": result["jobs"],
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/jobs/salary")
async def jobs_salary(req: SalaryRequest, auth: dict = Depends(verify_api_key)):
    """Get salary intelligence for a role in India"""
    try:
        result = await get_salary_intelligence(
            role=req.role,
            location=req.location,
            experience=req.experience,
        )
        if not result:
            raise HTTPException(status_code=404, 
                              detail="Not enough salary data for this query")
        return {
            "success": True,
            "role": req.role,
            "location": req.location,
            "experience_years": req.experience,
            **result,
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/jobs/skills")
async def jobs_skills(req: SkillsRequest, auth: dict = Depends(verify_api_key)):
    """Get trending skills by category in India"""
    try:
        result = await get_skills_trending(
            category=req.category,
            location=req.location,
        )
        return {
            "success": True,
            "category": req.category,
            "location": req.location,
            "trending_skills": result,
            "requests_used": auth["usage"],
            "requests_remaining": auth["limit"] - auth["usage"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

### 3. MODIFY: `requirements.txt`

Replace entire file with:
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.8.2
redis[asyncio]==5.0.8
playwright==1.44.0
playwright-stealth==1.0.6
stripe==10.9.0
python-dotenv==1.0.1
httpx==0.27.2
svix==1.21.0
```

---

### 4. MODIFY: `Dockerfile`

Replace entire file with:
```dockerfile
FROM python:3.12-slim

# Install system dependencies for Playwright Chromium
RUN apt-get update && apt-get install -y \
    libnss3 libgbm1 libasound2 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libgtk-3-0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libxss1 libxtst6 fonts-liberation \
    libappindicator3-1 xdg-utils wget curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium browser binary
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY app/ ./app/

# Run FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--loop", "asyncio", "--workers", "1"]
```

---

### 5. CREATE: `app/jobs_cron.py` (Background Prefetcher)

This runs every 6 hours to pre-cache popular searches:

```python
"""
jobs_cron.py — Pre-fetches popular job searches into Redis cache.
Run via cron: 0 */6 * * * cd ~/scrapPy && python -m app.jobs_cron
"""
import asyncio
from .jobs_scraper import scrape_naukri

TOP_SEARCHES = [
    # (query, location, exp_min, exp_max)
    ("python developer", "bangalore", 2, 5),
    ("data scientist", "mumbai", 2, 5),
    ("react developer", "hyderabad", 1, 4),
    ("java developer", "pune", 3, 6),
    ("devops engineer", "india", 2, 5),
    ("machine learning engineer", "bangalore", 2, 5),
    ("full stack developer", "india", 2, 5),
    ("android developer", "india", 1, 4),
    ("ios developer", "india", 1, 4),
    ("product manager", "bangalore", 3, 7),
    ("data analyst", "india", 0, 3),
    ("software engineer", "bangalore", 0, 3),
    ("software engineer", "hyderabad", 0, 3),
    ("software engineer", "pune", 0, 3),
    ("backend developer", "india", 2, 5),
    ("frontend developer", "india", 1, 4),
    ("golang developer", "india", 2, 5),
    ("rust developer", "india", 1, 4),
    ("cloud architect", "india", 5, 10),
    ("cybersecurity engineer", "india", 2, 6),
]

async def prefetch_all():
    print(f"[CRON] Starting prefetch of {len(TOP_SEARCHES)} searches...")
    for i, (query, location, exp_min, exp_max) in enumerate(TOP_SEARCHES):
        try:
            print(f"[CRON] {i+1}/{len(TOP_SEARCHES)}: {query} in {location}")
            await scrape_naukri(query, location, exp_min, exp_max, limit=50)
            await asyncio.sleep(8)  # Be polite — don't hammer Naukri
        except Exception as e:
            print(f"[CRON] Error on {query}/{location}: {e}")
            await asyncio.sleep(5)
    print("[CRON] Prefetch complete.")

if __name__ == "__main__":
    asyncio.run(prefetch_all())
```

---

## Step-By-Step Build Process

### Step 1 — SSH into server
```bash
ssh scrappy@168.144.113.171
cd ~/scrapPy
```

### Step 2 — Pull latest code or create files
Either git pull if repo is set up, or create files directly using nano:
```bash
nano app/jobs_scraper.py
# paste the jobs_scraper.py content
```

### Step 3 — Update requirements.txt
```bash
nano requirements.txt
# replace with new content above
```

### Step 4 — Update Dockerfile
```bash
nano Dockerfile
# replace with new content above
```

### Step 5 — Update main.py
```bash
nano app/main.py
# add the 3 new imports, 3 new models, 3 new routes
# do NOT remove any existing code
```

### Step 6 — Full rebuild (takes 5-10 minutes — Playwright is large)
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Step 7 — Watch logs while starting
```bash
docker compose logs -f api
```

Wait until you see:
```
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000
```

### Step 8 — Test jobs search endpoint
```bash
curl -X POST http://localhost:8000/v1/jobs/search \
  -H "x-api-key: sk_198435f5daa941f0bcc0aef575323f0e" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "python developer",
    "location": "bangalore",
    "experience_min": 2,
    "experience_max": 5,
    "limit": 10
  }'
```

Expected: JSON response with list of jobs from Naukri.

### Step 9 — Test salary endpoint
```bash
curl -X POST http://localhost:8000/v1/jobs/salary \
  -H "x-api-key: sk_198435f5daa941f0bcc0aef575323f0e" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "data scientist",
    "location": "bangalore",
    "experience": 3
  }'
```

### Step 10 — Test via public URL
```bash
curl -X POST https://scrappie.tech/v1/jobs/search \
  -H "x-api-key: sk_198435f5daa941f0bcc0aef575323f0e" \
  -H "Content-Type: application/json" \
  -d '{"query": "python developer", "location": "bangalore"}'
```

### Step 11 — Set up cron for prefetcher
```bash
crontab -e
# Add this line:
0 */6 * * * cd ~/scrapPy && docker exec scrappy-api python -m app.jobs_cron >> /home/scrappy/cron.log 2>&1
```

---

## Common Issues And Fixes

### Playwright not found after build
```bash
docker exec scrappy-api playwright install chromium
```

### Naukri returning empty results
Naukri occasionally updates their HTML structure. If selectors stop working:
1. Go to naukri.com manually in Chrome
2. Right-click a job card → Inspect
3. Find the new CSS selectors
4. Update the `parse_naukri_jobs()` function in jobs_scraper.py
5. Rebuild: `docker compose up -d --build api`

### Rate limited by Naukri
Add delays between requests:
```python
await asyncio.sleep(random.uniform(2, 5))
```
Or add proxy rotation (Webshare.io, ~$10/month for 100 IPs).

### Redis connection error
```bash
docker compose restart redis
docker compose restart api
```

### Out of memory
Reduce concurrent browsers:
```python
_semaphore = asyncio.Semaphore(2)  # reduce from 3 to 2
```

---

## Environment Variables Needed in .env

No new env vars needed for the scraper itself.
Optional for proxy rotation (add later):
```
WEBSHARE_PROXY_LIST=proxy1:port:user:pass,proxy2:port:user:pass,...
```

---

## Testing Checklist

- [ ] `docker compose ps` shows all containers as Up
- [ ] `curl https://scrappie.tech/health` returns `{"status":"ok"}`
- [ ] `POST /v1/jobs/search` returns job listings from Naukri
- [ ] `POST /v1/jobs/salary` returns salary data
- [ ] `POST /v1/jobs/skills` returns trending skills
- [ ] Second call to same query returns faster (Redis cache hit)
- [ ] `docker compose logs api` shows no Python errors
- [ ] API key usage increments correctly

---

## What NOT To Touch

- `app/proxy.py` — leave completely alone
- `app/billing.py` — leave completely alone
- `nginx/nginx.conf` — leave completely alone
- `docker-compose.yml` — leave completely alone
- The `verify_api_key` function in `main.py` — leave completely alone
- Existing routes in `main.py` (`/v1/scrape`, `/v1/render`, `/v1/batch`) — leave alone

Only ADD new code, never remove existing working code.

---

## Current API Key For Testing
```
sk_198435f5daa941f0bcc0aef575323f0e
Plan: free (100 requests/month)
```

---

## Final Goal

When complete, these commands should all return valid data:

```bash
# Job search
curl -X POST https://scrappie.tech/v1/jobs/search \
  -H "x-api-key: sk_198435f5daa941f0bcc0aef575323f0e" \
  -H "Content-Type: application/json" \
  -d '{"query": "python developer", "location": "bangalore"}'

# Salary intelligence  
curl -X POST https://scrappie.tech/v1/jobs/salary \
  -H "x-api-key: sk_198435f5daa941f0bcc0aef575323f0e" \
  -H "Content-Type: application/json" \
  -d '{"role": "data scientist", "location": "mumbai", "experience": 3}'

# Skills trending
curl -X POST https://scrappie.tech/v1/jobs/skills \
  -H "x-api-key: sk_198435f5daa941f0bcc0aef575323f0e" \
  -H "Content-Type: application/json" \
  -d '{"category": "backend", "location": "india"}'
```

---

*Product: Scrappie Jobs API — scrappie.tech*
*Target market: Indian HR tech, recruitment agencies, EdTech platforms*
*Data source: Naukri.com*
*Last updated: May 20, 2026*
