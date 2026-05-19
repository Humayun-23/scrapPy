# 🕵️ Scrappy — Deployment Guide

Stealth web scraping API powered by CloakBrowser + Hysteria2.

---

## Architecture

```
Customer → Nginx (TLS) → FastAPI → CloakBrowser → Hysteria2 Client → Hysteria2 Server → Web
```

---

## Step 1 — VPS Setup

Install Docker + Docker Compose on your VPS:

```bash
curl -fsSL https://get.docker.com | sh
apt install docker-compose-plugin -y
```

---

## Step 2 — SSL Certificate

```bash
apt install certbot -y
certbot certonly --standalone -d scrappy.io -d www.scrappy.io
```

---

## Step 3 — Deploy Hysteria2 Server (on a SEPARATE VPS node)

```bash
# Download Hysteria2
curl -fsSL https://get.hy2.sh/ | bash

# Copy your config
cp hysteria/hysteria-server.yaml /etc/hysteria/config.yaml

# Edit: update your domain, cert paths
nano /etc/hysteria/config.yaml

# Start as systemd service
systemctl enable --now hysteria-server@config
```

---

## Step 4 — Configure Environment

```bash
cp .env.example .env
nano .env
# Fill in: PROXY_SECRET, HYSTERIA_US_HOST, STRIPE keys
```

Update `hysteria/hysteria-client.yaml` with your Hysteria2 server hostname.

---

## Step 5 — Launch Everything

```bash
docker compose up -d
```

Check it's running:
```bash
docker compose ps
curl https://scrappy.io/health
```

---

## Step 6 — Create Your First API Key

```bash
curl -X POST https://scrappy.io/v1/keys/create \
  -H "Content-Type: application/json" \
  -d '{"email": "you@email.com", "plan": "free"}'
```

---

## Step 7 — Test a Scrape

```bash
curl -X POST https://scrappy.io/v1/scrape \
  -H "x-api-key: sk_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://bot.sannysoft.com"}'
```

---

## Scaling

| VPS RAM | MAX_CONCURRENT_BROWSERS | Requests/min |
|---------|------------------------|--------------|
| 2 GB    | 3                      | ~18/min      |
| 4 GB    | 6                      | ~36/min      |
| 8 GB    | 12                     | ~72/min      |
| 16 GB   | 20                     | ~120/min     |

For high volume: run multiple API containers behind a load balancer.

---

## Stripe Webhook (auto-provision keys after payment)

```bash
# In your Stripe dashboard, set webhook endpoint to:
# https://scrappy.io/v1/stripe/webhook

# In main.py, add:
@app.post("/v1/stripe/webhook")
async def stripe_webhook(request: Request):
    # On checkout.session.completed:
    # → call /v1/keys/create with customer email + plan
    pass
```

---

## File Structure

```
scrappy/
├── app/
│   ├── main.py          # FastAPI routes + auth
│   ├── scraper.py       # CloakBrowser scraping engine
│   └── proxy.py         # Hysteria2 credential generator
├── hysteria/
│   ├── hysteria-server.yaml   # Deploy on VPS nodes
│   └── hysteria-client.yaml   # Runs alongside FastAPI
├── nginx/
│   └── nginx.conf       # TLS + rate limiting
├── landing/
│   └── index.html       # Marketing site
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```
