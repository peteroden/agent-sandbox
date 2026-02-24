#!/bin/bash
set -e

echo "==================================="
echo "Setting up development environment"
echo "==================================="

cd /workspaces/agent-sandbox

# Install frontend dependencies
echo ""
echo "Installing frontend dependencies..."
if [ -d "frontend" ]; then
    cd frontend
    pnpm install
    cd ..
fi

# Install E2E test dependencies (Playwright)
echo ""
echo "Installing E2E test dependencies..."
if [ -d "e2e" ]; then
    cd e2e
    pnpm install
    pnpm exec playwright install chromium
    cd ..
fi

# Install Python dependencies with uv
echo ""
echo "Installing Python dependencies with uv..."
uv sync

# Setup SigNoz for observability (includes auto-registration)
echo ""
echo "Setting up SigNoz..."
if command -v docker &>/dev/null; then
    chmod +x scripts/setup-signoz.sh
    scripts/setup-signoz.sh
else
    echo "Docker not available, skipping SigNoz setup"
    echo "Run ./scripts/setup-signoz.sh manually when Docker is ready"
fi

echo ""
echo "==================================="
echo "Setup complete!"
echo ""
echo "To start the development servers:"
echo "  ./scripts/dev.sh"
echo ""
echo "With SigNoz observability:"
echo "  ./scripts/dev.sh --signoz"
echo "==================================="
