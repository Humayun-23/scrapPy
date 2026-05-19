# Check if scraper.py has correct code
cat ~/scrapPy/app/scraper.py | grep -A 5 "launch_async"

# Check env variables
cat ~/scrapPy/.env

# Check what's running inside container
docker exec scrappy-api cat /app/app/scraper.py | grep HYSTERIA

# Test API directly (bypass Nginx)
curl -X POST http://localhost:8000/v1/scrape \
  -H "x-api-key: sk_198435f5daa941f0bcc0aef575323f0e" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Check Redis keys
docker exec scrappy-redis redis-cli keys "*"

# Check specific API key
docker exec scrappy-redis redis-cli hgetall "apikey:sk_198435f5daa941f0bcc0aef575323f0e"

# Fix Redis memory warning
sudo sysctl vm.overcommit_memory=1
echo 'vm.overcommit_memory = 1' | sudo tee -a /etc/sysctl.conf

# current api key for testing
sk_198435f5daa941f0bcc0aef575323f0e
Plan: free
Limit: 100 requests/month