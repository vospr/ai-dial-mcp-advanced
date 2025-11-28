#!/bin/bash

# Advanced MCP - Test Runner Script for WSL/Linux
# This script sets up the environment and runs the test suite

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Advanced MCP - Test Runner"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Check Docker service
echo ""
echo "Checking Docker User Service (port 8041)..."
if curl -s -f http://localhost:8041/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Docker User Service is running${NC}"
else
    echo -e "${RED}❌ Docker User Service is NOT running${NC}"
    echo ""
    echo "Starting Docker services..."
    docker compose up -d
    echo "Waiting for service to be ready..."
    sleep 5
    
    # Check again
    if curl -s -f http://localhost:8041/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Docker User Service is now running${NC}"
    else
        echo -e "${RED}❌ Failed to start Docker User Service${NC}"
        echo "Please check Docker and try: docker compose up -d"
        exit 1
    fi
fi

# Check MCP Server
echo ""
echo "Checking MCP Server (port 8006)..."
if curl -s -f -X POST http://localhost:8006/mcp \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc":"2.0","id":"health-check","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
    > /dev/null 2>&1; then
    echo -e "${GREEN}✅ MCP Server is running${NC}"
else
    echo -e "${YELLOW}⚠️  MCP Server is NOT running${NC}"
    echo ""
    echo "Please start the MCP server in a separate terminal:"
    echo "  cd $(pwd)"
    echo "  source .venv/bin/activate"
    echo "  export DIAL_API_KEY='your_api_key'"
    echo "  python mcp_server/server.py"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to cancel..."
fi

# Check DIAL_API_KEY
echo ""
if [ -z "$DIAL_API_KEY" ]; then
    echo -e "${YELLOW}⚠️  DIAL_API_KEY environment variable is not set${NC}"
    echo ""
    echo "Please set it:"
    echo "  export DIAL_API_KEY='your_dial_api_key'"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to cancel..."
else
    echo -e "${GREEN}✅ DIAL_API_KEY is set${NC}"
fi

# Run tests
echo ""
echo "=========================================="
echo "Running Test Suite"
echo "=========================================="
echo ""

python test.py

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ All tests completed successfully!${NC}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
fi

exit $exit_code

