# Scrappy API Documentation

**Version:** 1.0.0  
**Description:** Stealth web scraping powered by CloakBrowser + Hysteria2

## Base URL
`https://your-domain.com`

## Authentication
Most endpoints require authentication using an API key provided in the headers.

| Header | Type | Description |
| :--- | :--- | :--- |
| `x-api-key` | string | Your Scrappy API key. |

---

## Scraping Endpoints

### Scrape a URL (Synchronous)
**`POST /v1/scrape`**

Stealthily scrapes a single URL and returns the extracted HTML, Markdown, or JSON data synchronously.

**Request Body (`application/json`)**
```json
{
  "url": "https://example.com",
  "wait_for": "#specific-element",
  "extract_json": false,
  "screenshot": false,
  "extract_markdown": true,
  "timeout": 30
}
```

### Render a URL (Synchronous)
**`POST /v1/render`**

Loads a URL in a stealth browser, waits for JS execution, and returns the fully rendered raw HTML.

**Request Body (`application/json`)**
```json
{
  "url": "https://example.com",
  "wait_for": null,
  "timeout": 30
}
```

### Batch Scrape URLs
**`POST /v1/batch`**

Concurrently scrapes up to 10 URLs in a single synchronous request.

**Request Body (`application/json`)**
```json
{
  "urls": ["https://example.com/1", "https://example.com/2"],
  "wait_for": null,
  "timeout": 30
}
```

---

## Asynchronous Scraping Endpoints

### Scrape a URL (Asynchronous)
**`POST /v1/scrape/async`**  
Enqueues a background job to scrape a URL. Returns a job ID to poll for status and results. (Accepts the same payload as `/v1/scrape`).

### Render a URL (Asynchronous)
**`POST /v1/render/async`**  
Enqueues a background job to render a URL. Returns a job ID to poll for status. (Accepts the same payload as `/v1/render`).

### Get Job Status
**`GET /v1/jobs/{job_id}`**  
Retrieve the status and optional result of a previously enqueued asynchronous job.

### Cancel a Job
**`POST /v1/jobs/{job_id}/cancel`**  
Attempt to cancel a pending or currently running asynchronous job.

---

## Browser Automation

### Automate Browser Interactions
**`POST /v1/browser`**

Navigate to a URL and perform a sequence of browser actions (click, type, scroll, wait) before extracting data.

**Request Body (`application/json`)**
```json
{
  "url": "https://example.com",
  "steps": [
    {
      "action": "click",
      "selector": "#load-more"
    },
    {
      "action": "wait",
      "wait_ms": 2000
    }
  ],
  "wait_for": null,
  "extract_json": true,
  "screenshot": false,
  "extract_markdown": true,
  "timeout": 30
}
```

### Automate Browser Interactions (Asynchronous)
**`POST /v1/browser/async`**  
Enqueues a background job to automate browser interactions. Returns a job ID. (Accepts the same payload as `/v1/browser`).

---

## API Keys & Billing

### Create a new API Key
**`POST /v1/keys/create`**  
Generates a new API key for the specified plan and emails it to the user. Limited to 3 per IP per day.

### Check API Key Usage
**`GET /v1/keys/usage`**  
Returns the current month's usage, limits, and reset date for the provided API key.

### List Subscription Plans
**`GET /v1/plans`** *(No authentication required)*  
Returns a list of all available subscription plans and their details.

---

## Proxy

### Proxy Credentials
**`POST /v1/proxy/credentials`**

Generate per-user SOCKS5/HTTP proxy credentials backed by Hysteria2 nodes.

**Request Body (`application/json`)**
```json
{
  "region": "us"
}
```

---

## Administration

### Get Admin Statistics
**`GET /v1/admin/stats`**  
Returns aggregate usage statistics for all API keys. Requires the `x-admin-secret` header instead of `x-api-key`.