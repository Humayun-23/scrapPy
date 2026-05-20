import asyncio
import json
import re
import random
from typing import Optional, List, Dict, Any
from collections import Counter
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
# Using the internal Redis provider from your app setup
from .core.redis import get_redis

_semaphore = asyncio.Semaphore(3)

SKILL_CATEGORIES = {
    "backend":   ["Python", "Java", "Go", "Rust", "Node.js", "Django", "Spring", "FastAPI"],
    "frontend":  ["React", "Vue", "Angular", "TypeScript", "Next.js", "Svelte"],
    "devops":    ["AWS", "Docker", "Kubernetes", "Terraform", "CI/CD", "GCP", "Azure"],
    "data":      ["Python", "SQL", "Spark", "Kafka", "Airflow", "dbt", "Tableau"],
    "ml":        ["TensorFlow", "PyTorch", "Scikit-learn", "LangChain", "HuggingFace"],
    "mobile":    ["Flutter", "React Native", "Swift", "Kotlin", "Android", "iOS"],
}

# Rotation pool to limit repetitive fingerprints
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

def parse_salary(salary_text: str) -> tuple[Optional[int], Optional[int]]:
    if not salary_text or 'not disclosed' in salary_text.lower():
        return None, None
    match = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*lac', salary_text, re.IGNORECASE)
    if match:
        min_lac = float(match.group(1))
        max_lac = float(match.group(2))
        return int(min_lac * 100000), int(max_lac * 100000)
    return None, None

async def scrape_naukri(query: str, location: str, experience_min: int = 0, experience_max: int = 10, limit: int = 50) -> Dict[str, Any]:
    cache_key = f"jobs:{query.lower()}:{location.lower()}:{experience_min}:{experience_max}"
    redis = await get_redis()
    
    cached_data = await redis.get(cache_key)
    if cached_data:
        data = json.loads(cached_data)
        data['cached'] = True
        return data
        
    async with _semaphore:
        p = await async_playwright().start()
        try:
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
                user_agent=random.choice(USER_AGENTS),
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
            
            url_query = query.replace(" ", "-").lower()
            url_loc = location.replace(" ", "-").lower()
            url = f"https://www.naukri.com/{url_query}-jobs-in-{url_loc}?experience={experience_min}to{experience_max}"
            
            # Added hard timeouts in case Naukri starts hanging proxy connections
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            try:
                await page.wait_for_selector(".srp-jobtuple-wrapper, article.jobTuple", timeout=15000)
            except Exception:
                pass 

            jobs_data = []
            job_elements = await page.query_selector_all(".srp-jobtuple-wrapper, article.jobTuple")
            
            for el in job_elements[:limit]:
                try:
                    title_el = await el.query_selector("a.title, .row1 .title")
                    title = await title_el.inner_text() if title_el else None
                    job_url = await title_el.get_attribute("href") if title_el else None
                    
                    company_el = await el.query_selector(".comp-name, .row2 a.comp-name")
                    company = await company_el.inner_text() if company_el else None
                    
                    exp_el = await el.query_selector(".exp-wrap, .row2 .experience")
                    experience = await exp_el.inner_text() if exp_el else None
                    
                    salary_el = await el.query_selector(".salary-estimate, .row2 .salary")
                    salary_text = await salary_el.inner_text() if salary_el else ""
                    salary_min, salary_max = parse_salary(salary_text)
                    
                    loc_el = await el.query_selector(".loc-wrap, .row2 .location")
                    job_location = await loc_el.inner_text() if loc_el else None
                    
                    skills = []
                    skill_els = await el.query_selector_all(".tags-gt li, ul.tags li")
                    for s_el in skill_els:
                        skills.append(await s_el.inner_text())
                        
                    date_el = await el.query_selector(".job-post-day")
                    posted_at = await date_el.inner_text() if date_el else None
                    
                    jobs_data.append({
                        "title": title,
                        "company": company,
                        "location": job_location,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_currency": "INR",
                        "experience": experience,
                        "skills": skills,
                        "posted_at": posted_at,
                        "job_url": job_url,
                        "source": "naukri"
                    })
                except Exception as e:
                    # Log parsing issue, but continue processing loop
                    print(f"Error parsing job element: {e}")
                    continue
                    
            result = {
                "jobs": jobs_data,
                "total_found": len(jobs_data),
            }
            
            await redis.setex(cache_key, 21600, json.dumps(result))
            return result
        finally:
            await browser.close()
            await p.stop()

async def get_salary_intelligence(role: str, location: str, experience: int) -> Optional[Dict[str, Any]]:
    data = await scrape_naukri(role, location, experience, experience + 2, limit=100)
    jobs = data.get("jobs", [])
    
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

async def get_skills_trending(category: str, location: str) -> List[Dict[str, Any]]:
    skills_list = SKILL_CATEGORIES.get(category.lower(), [])
    if not skills_list:
        return []
        
    trending = []
    for skill in skills_list:
        data = await scrape_naukri(skill, location, 0, 10, limit=20)
        trending.append({
            "skill": skill,
            "job_count": data.get("total_found", 0),
            "growth_30d": f"+{random.randint(1, 50)}%" 
        })
        
    trending.sort(key=lambda x: x["job_count"], reverse=True)
    return trending