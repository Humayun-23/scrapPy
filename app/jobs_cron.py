"""
jobs_cron.py — Pre-fetches popular job searches into Redis cache.
Run via cron: 0 */6 * * * cd ~/scrapPy && python -m app.jobs_cron
"""
import asyncio
import random
from app.jobs_scraper import scrape_naukri

TOP_SEARCHES = [
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
            # Added random jitter to avoid fixed-interval bot detection
            jitter = random.uniform(8.0, 15.0)
            await asyncio.sleep(jitter)
        except Exception as e:
            print(f"[CRON] Error on {query}/{location}: {e}")
            await asyncio.sleep(5)
    print("[CRON] Prefetch complete.")

if __name__ == "__main__":
    asyncio.run(prefetch_all())