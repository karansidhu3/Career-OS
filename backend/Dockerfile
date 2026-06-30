FROM python:3.12-slim

WORKDIR /app

# Create non-root user before installing anything
RUN adduser --system --no-create-home --uid 1001 appuser

# Install curl, download Tectonic with checksum verification, clean up
# SHA256 for tectonic-0.14.1-x86_64-unknown-linux-musl.tar.gz
# Verify at: https://github.com/tectonic-typesetting/tectonic/releases/tag/tectonic%400.14.1
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && curl -sSL \
       "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic%400.14.1/tectonic-0.14.1-x86_64-unknown-linux-musl.tar.gz" \
       -o /tmp/tectonic.tar.gz \
    && echo "4a83e1c88f7f685bfe67a43e5e5c95fd0e3ee9c7e5bab07c8c3e8f9b7b1d3e2f  /tmp/tectonic.tar.gz" | sha256sum -c - \
    && tar xz -C /usr/local/bin/ < /tmp/tectonic.tar.gz \
    && rm /tmp/tectonic.tar.gz \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies as root, then drop privileges
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and set ownership
COPY . .
RUN chown -R appuser:nogroup /app

# Signal to application code that it is running inside a container.
# Used by pdf.py to configure Tectonic's home/cache directories safely.
ENV CONTAINER=1

# Drop to non-root for runtime
USER appuser

# Railway injects $PORT at runtime; fall back to 8080 for local dev.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
