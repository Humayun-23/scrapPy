FROM python:3.12-slim

# Install Chromium system dependencies (required by CloakBrowser)
RUN apt-get update && apt-get install -y \
    libnss3 libgbm1 libasound2 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libgtk-3-0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libxss1 libxtst6 fonts-liberation \
    libappindicator3-1 xdg-utils wget curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download CloakBrowser binary at build time (so container starts fast)
RUN python -c "from cloakbrowser import ensure_binary; ensure_binary()"

# Copy app
COPY app/ ./app/

# Run
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "asyncio", "--workers", "1"]
