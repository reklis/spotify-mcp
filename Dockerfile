# Use the official UV image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml README.md ./

# Install dependencies using uv
RUN uv venv && \
    uv pip install -e .

# Copy application code
COPY . .

# Install the package in the virtual environment
RUN uv pip install -e .

# Expose the HTTP port
EXPOSE 8765

# Add labels for GitHub Container Registry
LABEL org.opencontainers.image.source="https://github.com/${GITHUB_REPOSITORY}"
LABEL org.opencontainers.image.description="Spotify MCP Server - Model Context Protocol server for Spotify integration"
LABEL org.opencontainers.image.licenses="MIT"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD uv run python -c "import urllib.request; urllib.request.urlopen('http://localhost:8765/mcp').read()" || exit 1

# Run the server using uv
CMD ["uv", "run", "spotify-mcp"]