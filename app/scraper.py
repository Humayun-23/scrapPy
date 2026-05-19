"""
scraper.py — CloakBrowser + Hysteria2 stealth scraping engine
"""
import os
import asyncio
import base64
import itertools
try:
    import markdownify
except ImportError:
    markdownify = None
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


async def _extract_page_data(
    page, extract_json: bool, screenshot: bool, extract_markdown: bool = False
) -> dict:
    """Helper to extract common data, reducing duplicate code and IPC overhead."""
    html_content = await page.content()
    result = {
        "html": html_content,
        "title": await page.title(),
        "url": page.url,
    }

    if extract_markdown:
        if markdownify:
            # Clean markdown conversion optimized for LLM inputs
            result["markdown"] = markdownify.markdownify(html_content, heading_style="ATX").strip()
        else:
            result["markdown"] = "Error: markdownify package is not installed."

    if extract_json:
        # Combine JS evaluation to reduce round-trips to the browser context
        extracted = await page.evaluate("""() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            const json_data = Array.from(scripts).map(s => {
                try { return JSON.parse(s.textContent); } catch(e) { return null; }
            }).filter(Boolean);

            const metas = document.querySelectorAll('meta');
            const meta = {};
            metas.forEach(m => {
                const name = m.getAttribute('name') || m.getAttribute('property');
                const content = m.getAttribute('content');
                if (name && content) meta[name] = content;
            });
            return { json_data, meta };
        }""")
        result["structured_data"] = extracted["json_data"]
        result["meta"] = extracted["meta"]

    if screenshot:
        png_bytes = await page.screenshot(full_page=True)
        result["screenshot_base64"] = base64.b64encode(png_bytes).decode()

    return result

async def scrape_url(
    url: str,
    wait_for: Optional[str] = None,
    extract_json: bool = False,
    screenshot: bool = False,
    extract_markdown: bool = False,
    timeout: int = 30,
) -> dict:
    """
    Scrape a single URL using CloakBrowser routed through Hysteria2.
    Returns cleaned HTML, optional screenshot, optional structured data.
    """
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
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            })

            await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")

            # Wait for specific element if requested
            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=timeout * 1000)
                except Exception:
                    pass  # Continue even if selector not found

            return await _extract_page_data(page, extract_json, screenshot, extract_markdown)

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
    extract_markdown: bool = False,
    timeout: int = 30,
) -> dict:
    """
    Browse a URL, run optional interaction steps, and return HTML and metadata.
    """
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
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            })

            await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")

            if wait_for:
                try:
                    await page.wait_for_selector(wait_for, timeout=timeout * 1000)
                except Exception:
                    pass

            if steps:
                await _apply_steps(page, steps, timeout)

            return await _extract_page_data(page, extract_json, screenshot, extract_markdown)

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
