# Scrappy 🕵️‍♂️ 
**The Stealth Web Scraping & Browser Automation API for AI and Data Teams.**

Scrappy is a powerful, hosted API designed to solve the hardest problems in web data extraction. Whether you are building AI agents, RAG pipelines, or market intelligence tools, Scrappy bypasses advanced anti-bot protections to deliver clean, structured data from any website.

---

## 🚀 Why Scrappy?

Modern websites are heavily protected by WAFs (Cloudflare, Datadome) and rely on complex JavaScript frameworks (React, Vue). Traditional HTTP scrapers fail instantly. 

Scrappy handles the complexity for you:
- **Invisible to Anti-Bots:** Powered by *CloakBrowser* and routed through *Hysteria2* stealth proxy protocols. Your requests look exactly like legitimate, human web browsing.
- **Built for the AI Era:** Instantly convert messy web pages into clean, LLM-ready **Markdown** with a single API flag (`extract_markdown: true`).
- **Full JavaScript Execution:** Scrappy loads and renders Single Page Applications (SPAs) completely before extracting data.
- **No-Code Interactivity:** Easily define interactions (clicks, scrolls, typing, waiting) using simple JSON arrays. No need to write and maintain brittle Puppeteer or Playwright scripts.
- **At-Scale Reliability:** Features asynchronous, queue-based scraping for long-running workflows, complete with job status polling and cancellation.

---

## 💡 Core Features

### 1. The Stealth Scraping Engine
Extract data from heavily protected sites without getting IP-banned. Scrappy automatically rotates IPs through an integrated proxy pool and spoofs browser fingerprints.

### 2. AI & LLM Optimized Extractions
Stop feeding your AI raw HTML. Scrappy can automatically return:
- Clean Markdown (`extract_markdown: true`)
- Structured JSON-LD Data (`extract_json: true`)
- Page Metadata (Title, OpenGraph tags, etc.)
- Full-page base64 Screenshots

### 3. Remote Browser Interactions
Need to bypass a "Click to load more" button or submit a search form before scraping? Pass an array of actions directly in your API request:
```json
"steps": [
  { "action": "type", "selector": "#search", "text": "AI pricing" },
  { "action": "click", "selector": ".submit-btn" },
  { "action": "wait_for", "selector": ".results-grid" }
]
```

2) Update the configs:

- nginx/nginx.conf (server_name + cert paths)
- hysteria/hysteria-client.yaml (server + auth)
- hysteria/hysteria-server.yaml (cert paths + auth)

3) Start services:

```
docker compose up -d --build
```

4) Create an API key:

```
curl -X POST https://<your-domain>/v1/keys/create \
  -H "Content-Type: application/json" \
  -d '{"email": "you@email.com", "plan": "free"}'
```

5) Test a scrape:

```
curl -X POST https://<your-domain>/v1/scrape \
  -H "x-api-key: sk_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Frontend

The landing page is served by Nginx from index.html at the repo root.

## Notes

- Hysteria2 server can run in the same compose file or on a separate node.
- CloakBrowser is resource-heavy; tune MAX_CONCURRENT_BROWSERS to available RAM.

## File Structure

```
scrappy/
├── app/
│   ├── jobs.py          # RQ job helpers
│   ├── main.py          # FastAPI routes + auth
│   ├── scraper.py       # CloakBrowser engine + steps
│   └── proxy.py         # Hysteria2 credential generator
├── hysteria/
│   ├── Dockerfile
│   ├── hysteria-server.yaml
│   └── hysteria-client.yaml
├── nginx/
│   └── nginx.conf
├── index.html
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```
