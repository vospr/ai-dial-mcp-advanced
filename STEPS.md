# Task 10: Advanced MCP Implementation - Planning & Execution

## 🎯 Task Overview

**Objective:** Implement a custom MCP server and client from scratch without high-level framework abstractions, demonstrating deep understanding of the Model Context Protocol.

**Repository:** ai-dial-mcp-advanced

**Key Learning:** Raw JSON-RPC protocol implementation, manual session management, and SSE streaming.

---

## 🧠 Conceptual Understanding

### Difference from MCP Fundamentals (Task 9)

| Aspect | **Task 9 (Fundamentals)** | **Task 10 (Advanced)** |
|--------|---------------------------|------------------------|
| **Server** | FastMCP (automatic) | FastAPI (manual JSON-RPC) |
| **Client** | MCP library (stdio/http) | Custom aiohttp client |
| **Session** | Automatic | Manual UUID management |
| **Streaming** | Built-in | Manual SSE parsing |
| **Protocol** | Abstracted | Raw JSON-RPC 2.0 |
| **Learning** | Protocol usage | Protocol implementation |

---

## 📐 Architecture & Protocol Flow

### MCP Protocol Stack

```
┌────────────────────────────────────────────────────┐
│                  AI Agent                          │
│  (Natural Language → Tool Selection)               │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│              DIAL Client                           │
│  (Azure OpenAI + Tool Calling)                     │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│          Custom MCP Client                         │
│  • HTTP Request Building                           │
│  • Session Management (UUID)                       │
│  • SSE Response Parsing                            │
│  • JSON-RPC Protocol                               │
└────────────┬───────────────────────────────────────┘
             │ HTTP/JSON-RPC
             ▼
┌────────────────────────────────────────────────────┐
│          FastAPI MCP Server                        │
│  • Initialize (session creation)                   │
│  • Tools/List (discover tools)                     │
│  • Tools/Call (execute tools)                      │
│  • SSE Streaming                                   │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│          Tool Registry                             │
│  • GetUserByIdTool                                 │
│  • SearchUsersTool                                 │
│  • CreateUserTool                                  │
│  • UpdateUserTool                                  │
│  • DeleteUserTool                                  │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│          User Service (Docker)                     │
│  REST API: CRUD operations on 1000 users           │
└────────────────────────────────────────────────────┘
```

---

## 🔄 JSON-RPC 2.0 Protocol Implementation

### Complete Session Flow

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1: Session Initialization                        │
└─────────────────────────────────────────────────────────┘

Client → Server: POST /mcp
{
  "jsonrpc": "2.0",
  "id": "init-1",
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "CustomMCPClient", "version": "1.0.0"}
  }
}

Server → Client: HTTP 200
Headers: Mcp-Session-Id: <uuid>
{
  "jsonrpc": "2.0",
  "id": "init-1",
  "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": {"tools": {}},
    "serverInfo": {"name": "CustomMCPServer", "version": "1.0.0"}
  }
}

┌─────────────────────────────────────────────────────────┐
│ Phase 2: Initialized Notification                      │
└─────────────────────────────────────────────────────────┘

Client → Server: POST /mcp
Headers: Mcp-Session-Id: <uuid>
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}

Server → Client: HTTP 202 Accepted
(No response body for notifications)

┌─────────────────────────────────────────────────────────┐
│ Phase 3: Tool Discovery                                │
└─────────────────────────────────────────────────────────┘

Client → Server: POST /mcp
Headers: Mcp-Session-Id: <uuid>
{
  "jsonrpc": "2.0",
  "id": "tools-list-1",
  "method": "tools/list"
}

Server → Client: HTTP 200 (SSE Stream)
data: {"jsonrpc":"2.0","id":"tools-list-1","result":{"tools":[
data:   {"name":"get_user_by_id","description":"...","inputSchema":{...}},
data:   {"name":"search_users","description":"...","inputSchema":{...}},
data:   ...
data: ]}}
data: [DONE]

┌─────────────────────────────────────────────────────────┐
│ Phase 4: Tool Execution                                │
└─────────────────────────────────────────────────────────┘

Client → Server: POST /mcp
Headers: Mcp-Session-Id: <uuid>
{
  "jsonrpc": "2.0",
  "id": "tools-call-1",
  "method": "tools/call",
  "params": {
    "name": "get_user_by_id",
    "arguments": {"id": 1}
  }
}

Server → Client: HTTP 200 (SSE Stream)
data: {"jsonrpc":"2.0","id":"tools-call-1","result":{
data:   "content":[{"type":"text","text":"User: ID=1, Name=John..."}]
data: }}
data: [DONE]
```

---

## 💭 Key Design Decisions

### Decision 1: Session Management Strategy

**Challenge:** MCP requires persistent sessions across multiple requests

**Options:**
1. **In-Memory Dict:** Simple but lost on restart
2. **Redis:** Scalable but adds dependency
3. **JWT Tokens:** Stateless but complex

**Chosen:** In-Memory Dict with UUID
```python
sessions: dict[str, dict] = {}  # session_id → session_data

def create_session() -> str:
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "created_at": time.time(),
        "initialized": False,
        "tools": []
    }
    return session_id
```

**Reasoning:**
- ✅ Simple for single-server setup
- ✅ Fast lookups
- ✅ No external dependencies
- ❌ Not production-ready (use Redis for prod)

---

### Decision 2: SSE vs WebSocket

**Challenge:** Real-time streaming of responses

**Options:**
1. **WebSocket:** Bidirectional, complex
2. **SSE (Server-Sent Events):** Unidirectional, simple
3. **Long Polling:** Simple but inefficient

**Chosen:** SSE (Server-Sent Events)

**SSE Format:**
```
data: {"key": "value"}
data: [DONE]
```

**Parsing Logic:**
```python
async def parse_sse_response(response):
    content = []
    async for line in response.content:
        line = line.decode('utf-8').strip()
        if line.startswith('data:'):
            data = line[5:].strip()  # Remove 'data:' prefix
            if data == '[DONE]':
                break
            content.append(json.loads(data))
    return content
```

**Reasoning:**
- ✅ MCP spec uses SSE
- ✅ HTTP-based (firewall-friendly)
- ✅ Simpler than WebSocket
- ✅ One-way communication sufficient

---

### Decision 3: Custom vs Library Client

**Why Custom Client:**

**Learning Goals:**
- Understand HTTP headers (Accept, Mcp-Session-Id)
- Manual JSON-RPC construction
- SSE parsing implementation
- Error handling at protocol level

**Implementation Complexity:**
```python
# With Library (Easy)
async with MCPClient(url) as client:
    tools = await client.list_tools()

# Custom (Complex but Educational)
async with aiohttp.ClientSession() as session:
    # Initialize
    init_response = await session.post(
        url, 
        json=build_jsonrpc_request("initialize", {...}),
        headers={"Accept": "application/json, text/event-stream"}
    )
    session_id = init_response.headers['Mcp-Session-Id']
    
    # Send notification
    await session.post(
        url,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        headers={"Mcp-Session-Id": session_id}
    )
    
    # List tools
    tools_response = await session.post(
        url,
        json=build_jsonrpc_request("tools/list"),
        headers={
            "Mcp-Session-Id": session_id,
            "Accept": "application/json, text/event-stream"
        }
    )
    
    # Parse SSE
    tools = await parse_sse_response(tools_response)
```

**Trade-off:** More code, deeper understanding

---

## 🛠️ Implementation Patterns

### Pattern 1: JSON-RPC Request Builder

```python
def build_jsonrpc_request(
    method: str, 
    params: dict = None, 
    request_id: str = None
) -> dict:
    """Build standard JSON-RPC 2.0 request"""
    request = {
        "jsonrpc": "2.0",
        "method": method
    }
    
    if request_id:  # Requests have IDs, notifications don't
        request["id"] = request_id
    
    if params:
        request["params"] = params
    
    return request
```

---

### Pattern 2: Session Validation Middleware

```python
async def validate_session(request: Request, call_next):
    """Middleware to validate MCP session"""
    
    # Initialize doesn't need session
    if "initialize" in await request.body().decode():
        return await call_next(request)
    
    # Check for session ID header
    session_id = request.headers.get('Mcp-Session-Id')
    if not session_id or session_id not in sessions:
        return JSONResponse(
            status_code=401,
            content={"error": "Invalid or missing session"}
        )
    
    return await call_next(request)
```

---

### Pattern 3: SSE Streaming Response

```python
async def stream_sse_response(data: dict):
    """Stream response in SSE format"""
    
    async def event_generator():
        # Stream the data
        json_str = json.dumps(data)
        yield f"data: {json_str}\n\n"
        
        # Send done marker
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
```

---

### Pattern 4: Tool Registry Pattern

```python
class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """Register a tool"""
        self.tools[tool.name] = tool
    
    def get_schemas(self) -> list[dict]:
        """Get all tool schemas"""
        return [tool.schema for tool in self.tools.values()]
    
    def execute(self, name: str, arguments: dict) -> str:
        """Execute a tool by name"""
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        
        return self.tools[name].execute(arguments)
```

---

## 📊 Implementation Checklist

### Server Implementation

- [ ] **mcp_server/services/mcp_server.py**
  - [ ] Session management (create, validate, store)
  - [ ] Tool registry initialization
  - [ ] `handle_initialize()` - Create session, return capabilities
  - [ ] `handle_initialized()` - Mark session as ready
  - [ ] `handle_tools_list()` - Return tool schemas
  - [ ] `handle_tools_call()` - Execute tool and return result
  - [ ] JSON-RPC request parsing
  - [ ] JSON-RPC response building

- [ ] **mcp_server/server.py**
  - [ ] FastAPI app initialization
  - [ ] POST `/mcp` endpoint (handles all methods)
  - [ ] Session ID header management
  - [ ] SSE streaming setup
  - [ ] Error handling middleware

- [ ] **mcp_server/tools/**
  - [ ] All 5 tools extend BaseTool
  - [ ] Each tool has: name, description, input_schema, execute()
  - [ ] Tools wrap UserClient operations

### Client Implementation

- [ ] **agent/clients/custom_mcp_client.py**
  - [ ] aiohttp session management
  - [ ] `__aenter__` - Initialize + Send notification
  - [ ] `__aexit__` - Cleanup
  - [ ] `list_tools()` - Discover available tools
  - [ ] `call_tool()` - Execute specific tool
  - [ ] JSON-RPC request building
  - [ ] SSE response parsing
  - [ ] Session ID storage and reuse

### Testing

- [ ] **test.py**
  - [ ] Start Docker user service
  - [ ] Start MCP server
  - [ ] Test with both MCPClient (library) and CustomMCPClient
  - [ ] Test query: "Check if Arkadiy Dobkin present, if not add him"
  - [ ] Verify tool calling works
  - [ ] Verify session management works

---

## 🔐 Security Considerations

### Session Security

**Vulnerabilities:**
- Session hijacking (UUID predictable?)
- No session expiration
- No authentication

**Improvements:**
```python
import secrets

def create_session():
    session_id = secrets.token_urlsafe(32)  # Cryptographically secure
    sessions[session_id] = {
        "created_at": time.time(),
        "expires_at": time.time() + 3600,  # 1 hour expiry
        "client_info": {...}
    }
    return session_id

def is_session_valid(session_id: str) -> bool:
    if session_id not in sessions:
        return False
    
    session = sessions[session_id]
    if time.time() > session["expires_at"]:
        del sessions[session_id]
        return False
    
    return True
```

---

## 📈 Performance Considerations

### Server Performance

**Bottlenecks:**
1. In-memory session dict (single server limit)
2. Synchronous tool execution
3. No caching of user data

**Optimizations:**
```python
# 1. Use Redis for sessions (multi-server)
import redis
redis_client = redis.Redis()

# 2. Parallel tool execution
results = await asyncio.gather(*[
    tool.execute(args) for tool in tools
])

# 3. Cache user lookups
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_user_cached(user_id: int):
    return user_client.get_user(user_id)
```

---

## 🎓 Key Learnings

### Protocol Understanding

**Before (Fundamentals):**
- Used FastMCP → "It just works"
- stdio/HTTP transport → Abstracted away
- Tool schemas → Auto-generated

**After (Advanced):**
- Understand JSON-RPC 2.0 structure
- Know HTTP headers for MCP
- Implement SSE parsing
- Manual session lifecycle
- Error code meanings

### Production Readiness Gap

**Current Implementation:**
- ❌ No authentication
- ❌ No rate limiting
- ❌ In-memory sessions (single server)
- ❌ No monitoring/logging
- ❌ No session expiration

**Production Requirements:**
- ✅ OAuth/API key authentication
- ✅ Redis for distributed sessions
- ✅ Rate limiting (per session/client)
- ✅ Structured logging (JSON)
- ✅ Metrics (Prometheus)
- ✅ Health checks
- ✅ Circuit breakers for tools

---

## 🚀 Deployment Strategy

### Development

```bash
# Start all services
docker compose up -d        # User service
python mcp_server/server.py # MCP server
python agent/app.py         # Test agent
```

### Production

```yaml
# docker-compose.prod.yml
services:
  redis:
    image: redis:7-alpine
  
  mcp_server:
    build: ./mcp_server
    environment:
      - REDIS_URL=redis://redis:6379
      - SESSION_TTL=3600
    depends_on:
      - redis
  
  user_service:
    image: khshanovskyi/mockuserservice:latest
```

---

## 🎯 Conclusion

This advanced MCP implementation demonstrates:

1. **Deep Protocol Knowledge:** JSON-RPC 2.0, SSE, session management
2. **Client-Server Architecture:** Custom implementation without abstractions
3. **Real-World Patterns:** Registry pattern, middleware, streaming
4. **Production Awareness:** Security, performance, scalability considerations

**Key Achievement:** Moved from "using MCP" to "implementing MCP" - understanding the protocol at a fundamental level enables building custom solutions and debugging production issues.

**Next Steps:**
- Add authentication layer
- Implement Redis sessions
- Add comprehensive logging
- Build monitoring dashboard
- Load testing and optimization

The gap between this educational implementation and production-ready code is **architectural patterns** (microservices, observability, resilience) rather than protocol understanding - which this task successfully provides.

