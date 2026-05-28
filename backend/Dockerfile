FROM python:3.12-slim

WORKDIR /app

# Install curl, download Tectonic (statically linked musl binary — no extra runtime deps),
# then clean up apt cache to keep the image lean.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && curl -sSL \
       "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.14.1/tectonic-0.14.1-x86_64-unknown-linux-musl.tar.gz" \
       | tar xz -C /usr/local/bin/ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Railway injects $PORT at runtime; fall back to 8080 for local dev.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
