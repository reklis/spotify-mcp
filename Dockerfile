# Use the official UV image
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

COPY . .

RUN uv sync

EXPOSE 8765

CMD ["uv", "run", "spotify-mcp"]