# Task 10: Advanced MCP Implementation Guide

## 📋 Implementation Overview

This guide provides step-by-step instructions for implementing a custom MCP (Model Context Protocol) server and client from scratch using FastAPI and aiohttp.

---

## 🎯 What You'll Implement

### Server Components
1. **MCPServer** (`mcp_server/services/mcp_server.py`) - Core MCP protocol handler
2. **FastAPI Server** (`mcp_server/server.py`) - HTTP endpoint with SSE streaming
3. **5 User Management Tools** - CRUD operations for user service

### Client Components
1. **CustomMCPClient** (`agent/clients/custom_mcp_client.py`) - Pure Python MCP client
2. **Agent Application** (`agent/app.py`) - AI agent using both library and custom clients

---

## 🚀 Quick Start Commands for WSL

### Step 1: Navigate to Project and Set Up Environment

```bash
cd /mnt/c/Users/AndreyPopov/ai-dial-mcp-advanced
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Start Docker User Service

```bash
# Start the mock user service (1000 users)
docker compose up -d

# Verify it's running
curl http://localhost:8041/health
```

### Step 3: Run MCP Server (After Implementation)

```bash
# In first WSL terminal
cd /mnt/c/Users/AndreyPopov/ai-dial-mcp-advanced
source .venv/bin/activate
export DIAL_API_KEY="your_dial_api_key_here"
python mcp_server/server.py
```

Server will start on `http://localhost:8006`

### Step 4: Test with Agent (After Implementation)

```bash
# In second WSL terminal
cd /mnt/c/Users/AndreyPopov/ai-dial-mcp-advanced
source .venv/bin/activate
export DIAL_API_KEY="your_dial_api_key_here"
python agent/app.py
```

### Step 5: Stop Services

```bash
# Stop Docker user service
docker compose down

# Stop MCP server (Ctrl+C in the terminal)
```

---

## 📝 Implementation Approach

### Phase 1: MCP Server Core Logic

**File:** `mcp_server/services/mcp_server.py`

**Key Implementations:**

#### 1. Session Management
```python
class MCPSession:
    """Represents an MCP session"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.ready_for_operation = False
        self.created_at = asyncio.get_event_loop().time()
        self.last_activity = self.created_at
```

#### 2. Initialize Handler
```python
def handle_initialize(self, request: MCPRequest) -> tuple[MCPResponse, str]:
    """
    Create new session and return server capabilities
    
    Returns:
        - MCPResponse with protocolVersion, capabilities, serverInfo
        - Session ID (UUID without dashes)
    """
    session_id = str(uuid.uuid4()).replace("-", "")
    session = MCPSession(session_id)
    self.sessions[session_id] = session
    
    return MCPResponse(...), session_id
```

#### 3. Tools List Handler
```python
def handle_tools_list(self, request: MCPRequest) -> MCPResponse:
    """
    Return all available tools with their schemas
    
    Tool schema format:
    {
        "name": "tool_name",
        "description": "What the tool does",
        "inputSchema": {JSON schema}
    }
    """
    tools_list = [tool.to_mcp_tool() for tool in self.tools.values()]
    return MCPResponse(id=request.id, result={"tools": tools_list})
```

#### 4. Tools Call Handler
```python
async def handle_tools_call(self, request: MCPRequest) -> MCPResponse:
    """
    Execute a tool and return result in MCP format
    
    Request params:
        - name: tool name
        - arguments: tool arguments dict
    
    Response format:
    {
        "content": [
            {"type": "text", "text": "result string"}
        ]
    }
    """
    tool_name = request.params.get("name")
    arguments = request.params.get("arguments", {})
    
    tool = self.tools[tool_name]
    result_text = await tool.execute(arguments)
    
    return MCPResponse(
        id=request.id,
        result={
            "content": [{"type": "text", "text": result_text}]
        }
    )
```

---

### Phase 2: FastAPI Server Endpoints

**File:** `mcp_server/server.py`

**Key Implementations:**

#### 1. SSE Stream Generator
```python
async def _create_sse_stream(messages: list):
    """Convert messages to Server-Sent Events format"""
    for message in messages:
        # SSE format: "data: {json}\n\n"
        event_data = f"data: {json.dumps(message.dict(exclude_none=True))}\n\n"
        yield event_data.encode('utf-8')
    
    yield b"data: [DONE]\n\n"
```

#### 2. Main MCP Endpoint
```python
@app.post("/mcp")
async def handle_mcp_request(
    request: MCPRequest,
    response: Response,
    accept: Optional[str] = Header(None),
    mcp_session_id: Optional[str] = Header(None, alias="Mcp-Session-Id")
):
    """
    Single endpoint handling all MCP methods:
    - initialize: Create session
    - notifications/initialized: Mark session ready
    - tools/list: Return available tools
    - tools/call: Execute tool
    """
    
    # Validate Accept header (must include both JSON and SSE)
    if not _validate_accept_header(accept):
        return error_response(406, "Must accept application/json and text/event-stream")
    
    # Handle initialize (no session required)
    if request.method == "initialize":
        mcp_response, session_id = mcp_server.handle_initialize(request)
        response.headers["Mcp-Session-Id"] = session_id
    
    # All other methods require valid session
    else:
        if not mcp_session_id or not mcp_server.get_session(mcp_session_id):
            return error_response(400, "Invalid session")
        
        # Handle notification (no response)
        if request.method == "notifications/initialized":
            session.ready_for_operation = True
            return Response(status_code=202)
        
        # Handle tools/list and tools/call
        if request.method == "tools/list":
            mcp_response = mcp_server.handle_tools_list(request)
        elif request.method == "tools/call":
            mcp_response = await mcp_server.handle_tools_call(request)
    
    # Return as SSE stream
    return StreamingResponse(
        _create_sse_stream([mcp_response]),
        media_type="text/event-stream"
    )
```

---

### Phase 3: User Management Tools

**Files:** `mcp_server/tools/users/*.py`

All tools follow this pattern:

```python
from mcp_server.tools.users.base import BaseUserServiceTool

class GetUserByIdTool(BaseUserServiceTool):
    
    @property
    def name(self) -> str:
        return "get_user_by_id"
    
    @property
    def description(self) -> str:
        return "Provides full user information by user_id"
    
    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "number", "description": "User ID"}
            },
            "required": ["id"]
        }
    
    async def execute(self, arguments: dict[str, Any]) -> str:
        user_id = int(arguments["id"])
        return await self._user_client.get_user(user_id)
```

**Tools to Implement:**
1. ✅ `GetUserByIdTool` - Get user by ID
2. ✅ `SearchUsersTool` - Search users by name/email/gender
3. ✅ `CreateUserTool` - Add new user
4. ✅ `UpdateUserTool` - Update user info
5. ✅ `DeleteUserTool` - Delete user

---

### Phase 4: Custom MCP Client

**File:** `agent/clients/custom_mcp_client.py`

**Key Implementations:**

#### 1. JSON-RPC Request Builder
```python
async def _send_request(self, method: str, params: Optional[dict] = None) -> dict:
    """
    Build and send JSON-RPC 2.0 request
    
    Request format:
    {
        "jsonrpc": "2.0",
        "id": "unique-id",
        "method": "method_name",
        "params": {...}
    }
    """
    request_data = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method
    }
    
    if params:
        request_data["params"] = params
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    # Add session ID for non-initialize requests
    if method != "initialize" and self.session_id:
        headers["Mcp-Session-Id"] = self.session_id
    
    async with self.http_session.post(
        self.server_url, json=request_data, headers=headers
    ) as response:
        # Capture session ID from response
        if response.headers.get("Mcp-Session-Id"):
            self.session_id = response.headers["Mcp-Session-Id"]
        
        return await self._parse_sse_response(response)
```

#### 2. SSE Response Parser
```python
async def _parse_sse_response_streaming(self, response) -> dict:
    """
    Parse Server-Sent Events response
    
    SSE format:
    data: {"jsonrpc": "2.0", ...}
    data: [DONE]
    """
    async for line in response.content:
        line_str = line.decode('utf-8').strip()
        
        # Skip empty lines and comments
        if not line_str or line_str.startswith(':'):
            continue
        
        if line_str.startswith('data: '):
            data_part = line_str[6:].strip()
            
            # Stop on [DONE] marker
            if data_part == '[DONE]':
                break
            
            try:
                return json.loads(data_part)
            except json.JSONDecodeError:
                continue
    
    raise RuntimeError("No valid JSON in SSE stream")
```

#### 3. Connection Flow
```python
async def connect(self) -> None:
    """Initialize MCP connection"""
    self.http_session = aiohttp.ClientSession()
    
    # 1. Initialize
    init_result = await self._send_request("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "clientInfo": {"name": "my-custom-mcp-client", "version": "1.0.0"}
    })
    
    # 2. Send initialized notification
    await self._send_notification("notifications/initialized")
```

#### 4. Tool Operations
```python
async def get_tools(self) -> list[dict]:
    """Get available tools from server"""
    response = await self._send_request("tools/list")
    tools = response["result"]["tools"]
    
    # Convert to OpenAI function calling format
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {})
            }
        }
        for tool in tools
    ]

async def call_tool(self, tool_name: str, tool_args: dict) -> str:
    """Execute a tool"""
    params = {"name": tool_name, "arguments": tool_args}
    response = await self._send_request("tools/call", params)
    
    # Extract text from MCP content format
    content = response["result"]["content"]
    return content[0]["text"] if content else ""
```

---

## 🧪 Testing with Postman

### Import Collection

1. Open Postman
2. Click **Import** → **Upload Files**
3. Select `mcp.postman_collection.json` from project root
4. Collection "MCP Tools Server" will be imported

### Test Flow

#### Test 1: Initialize Session

**Request:** `1. init`

- **Method:** POST
- **URL:** `http://localhost:8006/mcp`
- **Headers:**
  ```
  Content-Type: application/json
  Accept: application/json, text/event-stream
  ```
- **Body:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": "init-1",
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {
        "tools": {}
      },
      "clientInfo": {
        "name": "postman-client",
        "version": "1.0.0"
      }
    }
  }
  ```

**Expected Response:**
- **Status:** 200 OK
- **Headers:** `Mcp-Session-Id: <uuid>`
- **Body (SSE):**
  ```
  data: {"jsonrpc":"2.0","id":"init-1","result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{"listChanged":true}},"serverInfo":{"name":"custom-ums-mcp-server","version":"1.0.0"}}}
  data: [DONE]
  ```

**Action:** Copy the `Mcp-Session-Id` value from response headers!

---

#### Test 2: Send Initialized Notification

**Request:** `2. init-notification`

- **Method:** POST
- **URL:** `http://localhost:8006/mcp`
- **Headers:**
  ```
  Content-Type: application/json
  Accept: application/json, text/event-stream
  Mcp-Session-Id: <paste-session-id-here>
  ```
- **Body:**
  ```json
  {
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
  }
  ```

**Expected Response:**
- **Status:** 202 Accepted
- **Body:** Empty (notifications don't return responses)

---

#### Test 3: List Available Tools

**Request:** `3. tools/list`

- **Method:** POST
- **URL:** `http://localhost:8006/mcp`
- **Headers:**
  ```
  Content-Type: application/json
  Accept: application/json, text/event-stream
  Mcp-Session-Id: <paste-session-id-here>
  ```
- **Body:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": "tools-list-1",
    "method": "tools/list"
  }
  ```

**Expected Response:**
- **Status:** 200 OK
- **Body (SSE):**
  ```
  data: {"jsonrpc":"2.0","id":"tools-list-1","result":{"tools":[
  data:   {"name":"get_user_by_id","description":"Provides full user information by user_id","inputSchema":{...}},
  data:   {"name":"search_users","description":"Searches users by name, surname, email, and gender","inputSchema":{...}},
  data:   {"name":"add_user","description":"Adds new user into the system","inputSchema":{...}},
  data:   {"name":"update_user","description":"Updates user info","inputSchema":{...}},
  data:   {"name":"delete_user","description":"Deletes user by user_id","inputSchema":{...}}
  data: ]}}
  data: [DONE]
  ```

---

#### Test 4: Call a Tool (Get User by ID)

**Request:** `4. tools/call - get_user_by_id`

- **Method:** POST
- **URL:** `http://localhost:8006/mcp`
- **Headers:**
  ```
  Content-Type: application/json
  Accept: application/json, text/event-stream
  Mcp-Session-Id: <paste-session-id-here>
  ```
- **Body:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": "tools-call-1",
    "method": "tools/call",
    "params": {
      "name": "get_user_by_id",
      "arguments": {
        "id": 1
      }
    }
  }
  ```

**Expected Response:**
- **Status:** 200 OK
- **Body (SSE):**
  ```
  data: {"jsonrpc":"2.0","id":"tools-call-1","result":{"content":[{"type":"text","text":"User: {...}"}]}}
  data: [DONE]
  ```

---

#### Test 5: Call a Tool (Search Users)

**Request:** `5. tools/call - search_users`

- **Body:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": "tools-call-2",
    "method": "tools/call",
    "params": {
      "name": "search_users",
      "arguments": {
        "name": "John"
      }
    }
  }
  ```

---

#### Test 6: Call a Tool (Add User)

**Request:** `6. tools/call - add_user`

- **Body:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": "tools-call-3",
    "method": "tools/call",
    "params": {
      "name": "add_user",
      "arguments": {
        "name": "Arkadiy",
        "surname": "Dobkin",
        "email": "arkadiy.dobkin@epam.com",
        "gender": "male",
        "about_me": "CEO of EPAM Systems"
      }
    }
  }
  ```

---

### Common Postman Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Missing session ID` | Forgot to add `Mcp-Session-Id` header | Copy session ID from init response |
| `Invalid session` | Wrong session ID or server restarted | Re-run init request to get new session |
| `406 Not Acceptable` | Missing `Accept` header | Add `application/json, text/event-stream` |
| `Connection refused` | MCP server not running | Start server with `python mcp_server/server.py` |

---

## 🔍 Debugging Tips

### Check if Services are Running

```bash
# Check Docker user service
docker ps
curl http://localhost:8041/health

# Check MCP server
curl http://localhost:8006/
```

### View MCP Server Logs

When running `python mcp_server/server.py`, you'll see:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8006
```

Every request will be logged:

```
Client initialization complete
{'jsonrpc': '2.0', 'id': 'tools-call-1', 'method': 'tools/call', 'params': {...}}
    Calling `get_user_by_id` with {'id': 1}
    ⚙️: User: ID=1, Name=John...
```

### Common Implementation Errors

**Error:** `KeyError: 'result'` in client
- **Cause:** Trying to access `response["result"]` but server returned error
- **Fix:** Check for `"error"` field first

**Error:** `RuntimeError: HTTP session not initialized`
- **Cause:** Calling tool methods before `connect()`
- **Fix:** Use `async with CustomMCPClient.create(url) as client:`

**Error:** `Tool execution error: ...`
- **Cause:** User service not running
- **Fix:** `docker compose up -d`

---

## 🎯 Success Criteria

### Server Implementation ✅

- [ ] `docker compose up -d` starts user service
- [ ] `python mcp_server/server.py` starts without errors
- [ ] Postman init request returns session ID
- [ ] Postman tools/list returns 5 tools
- [ ] Postman tools/call executes successfully

### Client Implementation ✅

- [ ] `python agent/app.py` connects to both MCPClient and CustomMCPClient
- [ ] Agent can list tools from both clients
- [ ] Agent can execute test query: "Check if Arkadiy Dobkin present, if not add him"
- [ ] Tool calls are logged and execute correctly

---

## 📚 Implementation Order

1. **Start with Server** (easier to test with Postman)
   - Implement `mcp_server/services/mcp_server.py`
   - Implement `mcp_server/server.py`
   - Test with Postman

2. **Implement Tools** (reuse from completed branch)
   - Copy all 5 tool implementations
   - Test each tool with Postman

3. **Implement Custom Client**
   - Implement `agent/clients/custom_mcp_client.py`
   - Update `agent/app.py` to use both clients
   - Test with agent query

4. **Final Testing**
   - Run full test query
   - Verify tool calling works
   - Check logs for errors

---

## 🎓 Key Concepts Explained

### Why Session IDs?

MCP uses stateful sessions to:
- Track client capabilities
- Maintain conversation context
- Prevent unauthorized access
- Enable proper cleanup

### Why SSE (Server-Sent Events)?

SSE is used because:
- ✅ HTTP-based (works through firewalls)
- ✅ One-way communication sufficient (server → client)
- ✅ Simpler than WebSockets
- ✅ Native browser support
- ✅ MCP specification uses SSE

### JSON-RPC 2.0 Structure

**Request:**
- `jsonrpc`: Always "2.0"
- `id`: Unique identifier (for matching responses)
- `method`: What to do (e.g., "tools/call")
- `params`: Arguments

**Response:**
- `jsonrpc`: Always "2.0"
- `id`: Matches request ID
- `result`: Success data **OR** `error`: Error details

**Notification:**
- Like request but **no `id`** field
- Server doesn't send response

---

## 🚀 Ready to Implement!

Follow the WSL commands at the top to set up your environment, then implement each component following the patterns described in this guide.

Good luck! 🎉

