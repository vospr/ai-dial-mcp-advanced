# Quick Start Guide - Advanced MCP

This guide will help you quickly set up and run tests for the Advanced MCP project.

## 📋 Prerequisites

- **Python**: 3.11 or higher
- **Docker**: Docker Desktop installed and running
- **WSL** (for Windows users): Windows Subsystem for Linux
- **DIAL API Key**: Required for AI agent functionality

## 🚀 Quick Start

### 1. Start Docker Services

First, start the User Management Service using Docker Compose:

```bash
# In WSL or Linux
cd /mnt/c/Users/AndreyPopov/ai-dial-mcp-advanced
docker compose up -d

# Or in Windows PowerShell
cd C:\Users\AndreyPopov\ai-dial-mcp-advanced
docker compose up -d
```

Verify the service is running:
```bash
curl http://localhost:8041/health
# Should return: {"status":"ok"}
```

### 2. Start MCP Server

The MCP server must be running before running tests. Start it in a separate terminal:

```bash
# In WSL
cd /mnt/c/Users/AndreyPopov/ai-dial-mcp-advanced
source .venv/bin/activate
export DIAL_API_KEY='your_dial_api_key'
python mcp_server/server.py

# The server should start on http://localhost:8006
```

### 3. Set Environment Variable

Set your DIAL API key:

```bash
# In WSL/Linux
export DIAL_API_KEY='your_dial_api_key'

# In Windows PowerShell
$env:DIAL_API_KEY='your_dial_api_key'
```

### 4. Run Tests

#### Option A: Using Shell Script (WSL/Linux)

```bash
cd /mnt/c/Users/AndreyPopov/ai-dial-mcp-advanced
./run_tests.sh
```

#### Option B: Using PowerShell Script (Windows)

```powershell
cd C:\Users\AndreyPopov\ai-dial-mcp-advanced
.\run_tests.ps1
```

#### Option C: Using Python Script (Cross-platform)

```bash
cd /mnt/c/Users/AndreyPopov/ai-dial-mcp-advanced
python run_tests.py
```

## 📝 Test Suite Overview

The test suite (`test.py`) includes:

1. **Service Health Check**: Verifies Docker and MCP server are running
2. **MCPClient Test**: Tests library-based MCP client
3. **CustomMCPClient Test**: Tests pure Python MCP client implementation
4. **Full Agent Test**: Tests complete agent with real query

## 🔧 Manual Setup (If Scripts Don't Work)

### Step 1: Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/WSL
# or
.venv\Scripts\activate  # Windows
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Start Services

1. **Docker User Service**:
   ```bash
   docker compose up -d
   ```

2. **MCP Server** (in separate terminal):
   ```bash
   source .venv/bin/activate
   export DIAL_API_KEY='your_api_key'
   python mcp_server/server.py
   ```

### Step 4: Run Tests

```bash
source .venv/bin/activate
export DIAL_API_KEY='your_api_key'
python test.py
```

## 🐛 Troubleshooting

### Issue: "User service is NOT running"

**Solution**: Start Docker Compose:
```bash
docker compose up -d
```

### Issue: "MCP server is NOT running"

**Solution**: Start the MCP server in a separate terminal:
```bash
cd /mnt/c/Users/AndreyPopov/ai-dial-mcp-advanced
source .venv/bin/activate
export DIAL_API_KEY='your_api_key'
python mcp_server/server.py
```

### Issue: "DIAL_API_KEY environment variable is not set"

**Solution**: Set the environment variable:
```bash
export DIAL_API_KEY='your_dial_api_key'
```

### Issue: Port 8041 already in use

**Solution**: Stop the conflicting container:
```bash
docker ps
docker stop <container_id>
```

### Issue: Port 8006 already in use

**Solution**: Find and stop the process using port 8006:
```bash
# Linux/WSL
lsof -ti:8006 | xargs kill -9

# Windows
netstat -ano | findstr :8006
taskkill /PID <pid> /F
```

## 📚 Additional Resources

- [Project README](README.md)
- [Implementation Guide](Implementation.md)
- [Detailed Steps](STEPS.md)

## 🎯 Test Query Example

The test suite includes a real-world query:
```
Check if Arkadiy Dobkin present as a user, if not then search info about him in the web and add him
```

This query tests:
- User search functionality
- Web search integration (via remote fetch MCP server)
- User creation functionality

## ✅ Success Indicators

When tests pass, you should see:
- ✅ All service health checks passing
- ✅ MCPClient test passing
- ✅ CustomMCPClient test passing
- ✅ Full agent test passing with agent response

---

**Note**: Make sure both Docker service and MCP server are running before executing tests!

