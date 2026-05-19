"""
scraper.py — CloakBrowser + Hysteria2 stealth scraping engine
"""
import os
import asyncio
import base64
from typing import Optional

from cloakbrowser import launch_async, launch_context

# Hysteria2 SOCKS5 proxy (set via env)
HYSTERIA_PROXY = os.getenv("HYSTERIA_PROXY") or None

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
            **({'proxy': HYSTERIA_PROXY} if HYSTERIA_PROXY else {})
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


async def _apply_steps(page, steps: list[dict], default_timeout: int) -> None:
    for step in steps:
        action = (step.get("action") or "").lower()
        if action == "wait_for":
            selector = step.get("selector")
            if not selector:
                raise ValueError("wait_for requires selector")
            timeout_ms = step.get("timeout_ms") or (default_timeout * 1000)
            await page.wait_for_selector(selector, timeout=timeout_ms)
            continue

        if action == "click":
            selector = step.get("selector")
            if not selector:
                raise ValueError("click requires selector")
            await page.click(selector)
            continue

        if action == "fill":
            selector = step.get("selector")
            value = step.get("value")
            if not selector or value is None:
                raise ValueError("fill requires selector and value")
            await page.fill(selector, value)
            continue

        if action == "type":
            selector = step.get("selector")
            text = step.get("text")
            if not selector or text is None:
                raise ValueError("type requires selector and text")
            delay_ms = step.get("delay_ms")
            if delay_ms is None:
                await page.type(selector, text)
            else:
                await page.type(selector, text, delay=delay_ms)
            continue

        if action == "scroll":
            selector = step.get("selector")
            if selector:
                await page.eval_on_selector(
                    selector,
                    "el => el.scrollIntoView({behavior: 'auto', block: 'center'})",
                )
            else:
                x = step.get("x") or 0
                y = step.get("y") or 0
                if x == 0 and y == 0:
                    y = 500
                await page.evaluate("([x, y]) => window.scrollBy(x, y)", [x, y])
            continue

        if action == "wait":
            wait_ms = step.get("wait_ms")
            if wait_ms is None:
                raise ValueError("wait requires wait_ms")
            await asyncio.sleep(wait_ms / 1000)
            continue

        raise ValueError(f"Unknown action: {action}")


async def browser_url(
    url: str,
    steps: Optional[list[dict]] = None,
    wait_for: Optional[str] = None,
    extract_json: bool = False,
    screenshot: bool = False,
    timeout: int = 30,
) -> dict:
    """
    Browse a URL, run optional interaction steps, and return HTML and metadata.
    """
    async with _semaphore:
        browser = await launch_async(
            headless=True,
            **({'proxy': HYSTERIA_PROXY} if HYSTERIA_PROXY else {})
        )
        try:
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            })

            await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=10_000)

            if steps:
                await _apply_steps(page, steps, timeout)

            html = await page.content()
            title = await page.title()

            result = {
                "html": html,
                "title": title,
                "url": page.url,
            }

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
