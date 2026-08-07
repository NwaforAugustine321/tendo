FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for caching
COPY pyproject.toml ./

# Install dependencies
RUN uv pip install --system -e .

# Copy source code
COPY src/ ./src/

# Download model files for faster cold starts
RUN python -c "from livekit.agents import inference; print('Dependencies OK')" || true

# Run the agent
CMD ["python", "src/agent.py", "start"]
