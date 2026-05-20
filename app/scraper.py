"""
scraper.py — CloakBrowser + Hysteria2 stealth scraping engine
"""
import os
import asyncio
import itertools
from typing import Optional

from cloakbrowser import launch_async, launch_context

# Hysteria2 SOCKS5 proxy (set via env)
HYSTERIA_PROXY = os.getenv("HYSTERIA_PROXY") or None

# Residential proxy pool (comma-separated proxy URLs)
PROXY_POOL_ENV = os.getenv("PROXY_POOL", "")
PROXY_POOL = [p.strip() for p in PROXY_POOL_ENV.split(",") if p.strip()]
_proxy_iterator = itertools.cycle(PROXY_POOL) if PROXY_POOL else None

def _get_proxy() -> Optional[str]:
    """Rotate through the proxy pool if defined, else fallback to Hysteria proxy."""
    if _proxy_iterator:
        return next(_proxy_iterator)
    return HYSTERIA_PROXY

# Semaphore: max concurrent browser instances (tune to your VPS RAM)
# Each CloakBrowser instance uses ~300MB RAM
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_BROWSERS", "5"))
_semaphores = {}

def _get_semaphore() -> asyncio.Semaphore:
    """Lazily initialize semaphore per event loop to prevent issues with asyncio.run() in RQ workers."""
    loop = asyncio.get_running_loop()
    if loop not in _semaphores:
        _semaphores[loop] = asyncio.Semaphore(MAX_CONCURRENT)
    return _semaphores[loop]


async def extract_jobs_from_page(page, site: str) -> list[dict]:
    """
    Injects JS to parse the DOM into structured Job objects.
    Note: Selectors must be monitored and updated periodically as sites change them.
    """
    if site == "linkedin":
        pass

    elif site == "indeed":
        pass

    elif site == "naukri":
        return await page.evaluate("""() => {
            const jobCards = document.querySelectorAll('.srp-jobtuple-wrapper');
            return Array.from(jobCards).map(card => {
                let min_sal = null, max_sal = null;
                const salText = card.querySelector('.sal')?.innerText || '';
                if(salText.includes('-')) {
                    const parts = salText.split('-');
                    min_sal = parseInt(parts[0].replace(/[^0-9]/g, '')) * 100000 || null;
                    max_sal = parseInt(parts[1].replace(/[^0-9]/g, '')) * 100000 || null;
                }
                return {
                    title: (card.querySelector('.title')?.innerText || '').trim(),
                    company: (card.querySelector('.comp-name')?.innerText || '').trim(),
                    location: (card.querySelector('.locWdth')?.innerText || '').trim(),
                    salary_min: min_sal,
                    salary_max: max_sal,
                    experience: (card.querySelector('.expwdth')?.innerText || null),
                    skills: Array.from(card.querySelectorAll('.tags-gt .tag-li')).map(s => s.innerText.trim()),
                    posted_at: (card.querySelector('.job-post-day')?.innerText || '').trim(),
                    applicants: null,
                    job_url: (card.querySelector('.title')?.href || '').trim(),
                    source: "naukri"
                };
            }).filter(j => j.title);
        }""")

    elif site == "internshala":
        return await page.evaluate("""() => {
            const jobCards = document.querySelectorAll('.individual_internship');
            return Array.from(jobCards).map(card => {
                let min_sal = null, max_sal = null;
                const salText = card.querySelector('.stipend')?.innerText || '';
                const salMatch = salText.match(/(\d+)/g);
                if (salMatch && salMatch.length > 0) {
                    min_sal = parseInt(salMatch[0]);
                    max_sal = salMatch.length > 1 ? parseInt(salMatch[1]) : min_sal;
                }
                return {
                    title: (card.querySelector('.profile')?.innerText || '').trim(),
                    company: (card.querySelector('.company_name')?.innerText || '').trim(),
                    location: (card.querySelector('.location_link')?.innerText || '').trim(),
                    salary_min: min_sal,
                    salary_max: max_sal,
                    experience: "0-1 years",
                    skills: [],
                    posted_at: (card.querySelector('.status-success')?.innerText || '').trim(),
                    applicants: null,
                    job_url: (card.querySelector('.profile a')?.href || '').trim(),
                    source: "internshala"
                };
            }).filter(j => j.title);
        }""")
    return []

async def search_job_market(
    query: str,
    location: str,
    experience_min: int,
    experience_max: int,
    source: str,
    limit: int = 50,
    timeout: int = 45,
) -> list[dict]:
    """Constructs the appropriate URL for the targeted job board and extracts data."""
    import urllib.parse
    
    # 1. URL Construction Logic
    q = urllib.parse.quote(query.replace(" ", "-"))
    
    if location:
        l = urllib.parse.quote(location.replace(" ", "-"))
        if source == "naukri":
            url = f"https://www.naukri.com/{q}-jobs-in-{l}?experience={experience_min}"
        elif source == "internshala":
            url = f"https://internshala.com/internships/{q}-internship-in-{l}/"
        else:
            url = f"https://example.com"
    else:
        if source == "naukri":
            url = f"https://www.naukri.com/{q}-jobs?experience={experience_min}"
        elif source == "internshala":
            url = f"https://internshala.com/internships/{q}-internship/"
        else:
            url = f"https://example.com"

    # 2. Stealth Browser Execution
    async with _get_semaphore():
        current_proxy = _get_proxy()
        browser = await launch_async(
            headless=True,
            **({'proxy': current_proxy} if current_proxy else {})
        )
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
            })

            # Some of these sites need longer timeouts and aggressive bot protections
            await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            await asyncio.sleep(3)  # Allow JS rendering (e.g. React frameworks on Naukri)
            
            if limit > 20:
                for _ in range(3):
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await asyncio.sleep(1)
                    
            return await extract_jobs_from_page(page, source)
        finally:
            await browser.close()
