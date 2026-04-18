# Use the official UV image for the build stage
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Enable bytecode compilation and copy mode for speed
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (leverages Docker cache)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the rest of the application
ADD . /app

# Complete the sync
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Final runtime image
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy the synced environment from the builder
COPY --from=builder /app /app

# Ensure the virtualenv is on the PATH
ENV PATH="/app/.venv/bin:$PATH"

# Expose the standard proxy port
EXPOSE 3000

# Run the FastAPI server
CMD ["python", "server.py"]
