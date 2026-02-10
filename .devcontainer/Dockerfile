FROM mcr.microsoft.com/devcontainers/base:ubuntu

# Install additional OS packages
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    curl \
    git \
    build-essential \
    shellcheck \
    zstd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright Chromium system dependencies
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    libglib2.0-0t64 \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    libdbus-1-3 \
    libcups2t64 \
    libxkbcommon0 \
    libatspi2.0-0t64 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libcairo2 \
    libpango-1.0-0 \
    libasound2t64 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set working directory
WORKDIR /workspaces/agent-sandbox
