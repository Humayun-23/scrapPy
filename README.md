# Scrappy 🕵️‍♂️

**The Stealth Web Scraping & Browser Automation API for AI and Data Teams.**
**Indian Job Market Data API — Best Pick.**

Scrappy is a powerful, self-hostable API designed to solve the hardest problems in web data extraction. Whether you are building AI agents, RAG pipelines, or market intelligence tools, Scrappy bypasses advanced anti-bot protections to deliver clean, structured data from any website.
Naukri, LinkedIn, Indeed, and Internshala aggressively wall off their data. HR teams, recruiters, and salary benchmarking tools desperately need this data but can't get it cleanly. Scrappy is a DaaS API that bypasses their WAFs and returns perfectly structured job listings, salary ranges, and required skills by role, city, and experience level.

---

## ⚡ Quick Start Examples

Convert a protected page into clean Markdown instantly using your preferred language.
Get structured job listings with parsed salaries instantly.

**cURL**
```bash
curl -X POST https://your-domain.com/v1/scrape \
curl -X POST https://your-domain.com/v1/jobs/search \
  -H "x-api-key: sk_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "extract_markdown": true}'
  -d '{"query": "python developer", "location": "bangalore", "source": "naukri"}'
```

**Node.js (Fetch)**
```javascript
const response = await fetch('https://your-domain.com/v1/scrape', {
  method: 'POST',
  headers: {
    'x-api-key': 'sk_your_key_here',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    url: 'https://example.com',
    extract_markdown: true
  })
});
const data = await response.json();
console.log(data.markdown);
```

**Python (Requests)**
```python
import requests

response = requests.post(
    "https://your-domain.com/v1/scrape",
    headers={"x-api-key": "sk_your_key_here"},
    json={"url": "https://example.com", "extract_markdown": True}
)
print(response.json().get("markdown"))
```

---

## 🚀 Why Scrappy?

Modern websites are heavily protected by WAFs (Cloudflare, Datadome) and rely on complex JavaScript frameworks (React, Vue). Traditional HTTP scrapers fail instantly. 

Scrappy handles the complexity for you:

- **Invisible to Anti-Bots:** Powered by a stealth browser engine and routed through the *Hysteria2* stealth proxy protocol. Your requests look exactly like legitimate, human web browsing.
- **Built for the AI Era:** Instantly convert messy web pages into clean, LLM-ready **Markdown** or structured JSON with a single API flag.
- **Full JavaScript Execution:** Scrappy loads and renders Single Page Applications (SPAs) completely before extracting data.
- **No-Code Interactivity:** Easily define interactions (clicks, scrolls, typing, waiting) using simple JSON arrays. No need to write and maintain brittle Puppeteer or Playwright scripts.
- **At-Scale Reliability:** Features asynchronous, queue-based scraping for long-running workflows, complete with job status polling and cancellation.

---

## 💡 Core Features

- **Stealth Scraping Engine:** Extract data from heavily protected sites without getting IP-banned. Scrappy automatically rotates IPs through an integrated proxy pool and spoofs browser fingerprints.
- **AI & LLM Optimized Extractions:** Stop feeding your AI raw HTML. Scrappy can automatically return clean Markdown, structured JSON-LD data, page metadata, and full-page screenshots.
- **Remote Browser Interactions:** Need to bypass a "Click to load more" button or submit a search form? Pass an array of actions directly in your API request.
- **Asynchronous Scraping:** For long-running scraping tasks, use the job queue to run them in the background. Poll the `/v1/jobs/{job_id}` endpoint to get the result.
- **Proxy Access:** Paid plans get direct SOCKS5/HTTP access to the Hysteria2 proxy network.

---

## Architecture

```
Customer → Nginx (TLS) → FastAPI → CloakBrowser → Hysteria2 Client → Hysteria2 Server → Target Website
```

- **Nginx:** Handles TLS termination, rate limiting, and serves the static landing page.
- **FastAPI:** The core API application, handling authentication, routing, and job management.
- **Redis:** Used for API key storage, usage tracking, and as a message broker for the job queue.
- **RQ Worker:** A background process that executes the scraping jobs.
- **CloakBrowser:** A stealth-patched Chromium browser that is difficult for bot detectors to identify.
- **Hysteria2:** A high-performance, stealthy proxy protocol that masks traffic as standard HTTP/3.

---

## 📖 API Endpoints

### Scraping

- `POST /v1/scrape`: Scrape a single URL and get the result synchronously.
- `POST /v1/jobs`: Submit a URL for asynchronous scraping. Returns a `job_id`.
- `GET /v1/jobs/{job_id}`: Check the status and retrieve the result of an asynchronous job.
- `POST /v1/batch`: Scrape up to 10 URLs in a single synchronous call.

### API Key Management

- `POST /v1/keys/create`: Create a new API key.
- `GET /v1/keys/usage`: Check your current API usage and limits.
- `GET /v1/plans`: List available subscription plans.

### Proxy

- `POST /v1/proxy/credentials`: Get SOCKS5/HTTP proxy credentials for paid plans.

---

## 🚀 Self-Hosting Guide

### 1. Prerequisites

- A domain name (e.g., `your-domain.com`).
- A VPS with Docker and Docker Compose installed.
- (Optional but recommended) A separate, clean VPS to run the Hysteria2 server for better stealth.

### 2. Setup & Configuration

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/scrappy.git
    cd scrappy
    ```

2.  **Set up SSL:**
    Obtain SSL certificates for your domain. Let's Encrypt is a good free option.
    ```bash
    sudo apt install certbot
    sudo certbot certonly --standalone -d your-domain.com
    ```

3.  **Configure Environment Variables:**
    Copy `.env.example` to `.env` and fill in the values. At a minimum, you need to set `PROXY_SECRET`.

4.  **Update Config Files:**
    - `nginx/nginx.conf`: Replace `your-domain.com` with your actual domain and update the `ssl_certificate` and `ssl_certificate_key` paths.
    - `hysteria/hysteria-server.yaml`: Update `cert` and `key` paths and set a strong `auth` password.
    - `hysteria/hysteria-client.yaml`: Update the `server` address and `auth` password to match the server config.

### 3. Launch

```bash
docker-compose up -d --build
```

This will start the FastAPI application, the Redis database, and the RQ worker.

### 4. Create an API Key

```bash
curl -X POST https://your-domain.com/v1/keys/create \
  -H "Content-Type: application/json" \
  -d '{"email": "you@email.com", "plan": "free"}'
```

### 5. Test a Scrape

```bash
curl -X POST https://your-domain.com/v1/scrape \
  -H "x-api-key: sk_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

---

## ⚙️ Configuration

Key environment variables to set in your `docker-compose.yml` or `.env` file:

- `MAX_CONCURRENT_BROWSERS`: The number of concurrent browser instances. Tune this based on your server's RAM. Each browser consumes ~300MB.
- `REDIS_URL`: The connection URL for your Redis instance.
- `HYSTERIA_PROXY`: The address of your Hysteria2 client proxy (e.g., `socks5://127.0.0.1:1080`).
- `PROXY_SECRET`: A secret key used for generating temporary proxy credentials.

---

## 📂 File Structure

```
scrappy/
├── app/
│   ├── api/             # FastAPI route modules
│   ├── core/            # Core logic (settings, keys)
│   ├── jobs.py          # RQ job helpers
│   ├── main.py          # FastAPI app entrypoint
│   ├── scraper.py       # CloakBrowser scraping engine
│   └── proxy.py         # Hysteria2 credential generator
├── hysteria/
│   ├── Dockerfile
│   ├── hysteria-server.yaml
│   └── hysteria-client.yaml
├── nginx/
│   └── nginx.conf
├── index.html           # Static landing page
├── docker-compose.yml
├── Dockerfile           # For the main FastAPI app
└── requirements.txt
```
