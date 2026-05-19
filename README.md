# Scrappy - Stealth Scraping API + Hosted Browser

Scrappy is a hosted web scraping API and browser automation service built on CloakBrowser and Hysteria2. It provides sync and async scraping, optional JS interaction steps, and a proxy layer for stealthy traffic.

## What It Does

- Scrape URLs and return HTML + metadata
- Render JS-heavy pages
- Run interaction steps (click, fill, scroll, wait)
- Async jobs with status + cancel
- Optional proxy credentials for paid plans
- Static landing page served by Nginx

## Architecture

```
Client -> Nginx (TLS + frontend) -> FastAPI -> CloakBrowser
                          |                 -> Redis (usage + queue)
                          |                 -> RQ Worker (async jobs)
                          -> Hysteria2 Client -> Hysteria2 Server -> Web
```

## API Endpoints (MVP)

- POST /v1/scrape
- POST /v1/render
- POST /v1/browser
- POST /v1/scrape/async
- POST /v1/render/async
- POST /v1/browser/async
- GET  /v1/jobs/{job_id}
- POST /v1/jobs/{job_id}/cancel
- POST /v1/keys/create
- GET  /v1/keys/usage
- GET  /v1/plans

## Quick Start (Docker Compose)

1) Ensure TLS certs are available on the VM:

```
/etc/letsencrypt/live/<your-domain>/fullchain.pem
/etc/letsencrypt/live/<your-domain>/privkey.pem
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
