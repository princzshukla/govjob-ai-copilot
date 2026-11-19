# Backend API image.
FROM python:3.13-slim

WORKDIR /app

# Hashing (Argon2) and TLS certificates; boto cache not required. Slimmer: no dev deps.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

# Behind a reverse proxy, --forwarded-allow-ips must trust the proxy address
# (or be narrowed), otherwise per-IP rate limits all share one bucket.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
