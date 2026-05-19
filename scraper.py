"""
scraper.py — CloakBrowser + Hysteria2 stealth scraping engine
"""
import os
import asyncio
import base64
from typing import Optional

from cloakbrowser import launch_async, launch_context

# Hysteria2 SOCKS5 proxy (set via env)
HYSTERIA_PROXY = os.getenv("HYSTERIA_PROXY", "socks5://127.0.0.1:1080")

# Semaphore: max concurrent browser instances (tune to your VPS RAM)
# Each CloakBrowser instance uses ~300MB RAM
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_BROWSERS", "5"))
_semaphore = asyncio.Semaphore(MAX_CONCURRENT)


async def scrape_url(
    url: str,
    wait_for: Optional[str] = None,
    extract_json: bool = False,
    screenshot: bool = False,
    timeout: int = 30,
) -> dict:
    """
    Scrape a single URL using CloakBrowser routed through Hysteria2.
    Returns cleaned HTML, optional screenshot, optional structured data.
    """
    async with _semaphore:
        browser = await launch_async(
            headless=True,
            proxy=HYSTERIA_PROXY,
        )
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            })

            await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")

            # Wait for specific element if requested
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=10_000)
                except Exception:
                    pass  # Continue even if selector not found

            # Get page content
            html = await page.content()
            title = await page.title()

            result = {
                "html": html,
                "title": title,
                "url": page.url,  # Final URL after redirects
            }

            # Optional: extract JSON-LD structured data
            if extract_json:
                json_data = await page.evaluate("""() => {
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    return Array.from(scripts).map(s => {
                        try { return JSON.parse(s.textContent); } catch(e) { return null; }
                    }).filter(Boolean);
                }""")
                meta = await page.evaluate("""() => {
                    const metas = document.querySelectorAll('meta');
                    const result = {};
                    metas.forEach(m => {
                        const name = m.getAttribute('name') || m.getAttribute('property');
                        const content = m.getAttribute('content');
                        if (name && content) result[name] = content;
                    });
                    return result;
                }""")
                result["structured_data"] = json_data
                result["meta"] = meta

            # Optional: screenshot as base64
            if screenshot:
                png_bytes = await page.screenshot(full_page=True)
                result["screenshot_base64"] = base64.b64encode(png_bytes).decode()

            return result

        finally:
            await browser.close()


async def render_url(
    url: str,
    wait_for: Optional[str] = None,
    timeout: int = 30,
) -> str:
    """
    Simple render — returns raw HTML string after full JS execution.
    """
    result = await scrape_url(url, wait_for=wait_for, timeout=timeout)
    return result["html"]


async def batch_scrape(
    urls: list[str],
    wait_for: Optional[str] = None,
    timeout: int = 30,
) -> list[dict]:
    """
    Scrape multiple URLs concurrently.
    Each runs independently with its own CloakBrowser instance.
    """
    tasks = [
        scrape_url(url, wait_for=wait_for, timeout=timeout)
        for url in urls
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = []
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            output.append({"url": url, "success": False, "error": str(result)})
        else:
            output.append({"url": url, "success": True, **result})
    return output
