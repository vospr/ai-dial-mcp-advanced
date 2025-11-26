"""
Comprehensive test suite for Advanced MCP Implementation
Tests both MCPClient (library) and CustomMCPClient (pure Python)
"""
import asyncio
import os
import sys
from pathlib import Path
import subprocess
import time
import requests

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.clients.custom_mcp_client import CustomMCPClient
from agent.clients.mcp_client import MCPClient
from agent.clients.dial_client import DialClient
from agent.models.message import Message, Role


async def check_services():
    """Check if required services are running"""
    print("\n" + "=" * 100)
    print("SERVICE HEALTH CHECK")
    print("=" * 100)
    
    # Check Docker user service
    print("\n1. Checking Docker User Service...")
    try:
        response = requests.get("http://localhost:8041/health", timeout=5)
        response.raise_for_status()
        print(f"   ✅ User service is running: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("   ❌ User service is NOT running!")
        print("\n   Please start Docker user service:")
        print("   → docker compose up -d")
        print("\n   Or in WSL:")
        print("   → cd /mnt/c/Users/AndreyPopov/ai-dial-mcp-advanced && docker compose up -d")
        return False
    except Exception as e:
        print(f"   ❌ Error checking user service: {e}")
        return False
    
    # Check MCP Server
    print("\n2. Checking MCP Server...")
    try:
        # Try to make a simple request to MCP server
        response = requests.post(
            "http://localhost:8006/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "health-check",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            },
            timeout=5
        )
        if response.status_code in [200, 202]:
            print("   ✅ MCP server is running")
        else:
            raise Exception(f"Unexpected status: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ❌ MCP server is NOT running!")
        print("\n   Please start MCP server in a separate terminal:")
        print("   → python mcp_server/server.py")
        print("\n   Or in WSL:")
        print("   → cd /mnt/c/Users/AndreyPopov/ai-dial-mcp-advanced")
        print("   → source .venv/bin/activate")
        print("   → export DIAL_API_KEY='your_api_key'")
        print("   → python mcp_server/server.py")
        return False
    except Exception as e:
        print(f"   ❌ Error checking MCP server: {e}")
        return False
    
    # Check DIAL API key
    print("\n3. Checking DIAL API Key...")
    dial_api_key = os.getenv("DIAL_API_KEY")
    if not dial_api_key:
        print("   ❌ DIAL_API_KEY environment variable is not set!")
        print("\n   Please set it:")
        print("   → export DIAL_API_KEY='your_dial_api_key'")
        return False
    else:
        print(f"   ✅ DIAL_API_KEY is set: {dial_api_key[:10]}...")
    
    print("\n" + "=" * 100)
    print("✅ All services are ready!")
    print("=" * 100 + "\n")
    return True


async def test_mcp_client_library():
    """Test with MCPClient (library-based)"""
    print("\n" + "=" * 100)
    print("TEST 1: MCP CLIENT (Library-based)")
    print("=" * 100)
    
    try:
        print("\n→ Connecting to local MCP server (http://localhost:8006/mcp)...")
        client = await MCPClient.create("http://localhost:8006/mcp")
        
        print("\n→ Fetching available tools...")
        tools = await client.get_tools()
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            tool_name = tool.get('function', {}).get('name', 'unknown')
            print(f"   - {tool_name}")
        
        # Test get_user_by_id
        print("\n→ Testing tool: get_user_by_id (ID=1)")
        result = await client.call_tool("get_user_by_id", {"id": 1})
        print(f"   Result preview: {result[:200]}...")
        
        # Test search_users
        print("\n→ Testing tool: search_users (name='John')")
        result = await client.call_tool("search_users", {"name": "John"})
        print(f"   Result preview: {result[:200]}...")
        
        print("\n✅ MCPClient test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ MCPClient test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_custom_mcp_client():
    """Test with CustomMCPClient (pure Python)"""
    print("\n" + "=" * 100)
    print("TEST 2: CUSTOM MCP CLIENT (Pure Python)")
    print("=" * 100)
    
    try:
        print("\n→ Connecting to local MCP server (http://localhost:8006/mcp)...")
        client = await CustomMCPClient.create("http://localhost:8006/mcp")
        
        print("\n→ Fetching available tools...")
        tools = await client.get_tools()
        print(f"   Found {len(tools)} tools:")
        for tool in tools:
            tool_name = tool.get('function', {}).get('name', 'unknown')
            print(f"   - {tool_name}")
        
        # Test get_user_by_id
        print("\n→ Testing tool: get_user_by_id (ID=2)")
        result = await client.call_tool("get_user_by_id", {"id": 2})
        print(f"   Result preview: {result[:200]}...")
        
        # Test search_users
        print("\n→ Testing tool: search_users (gender='female')")
        result = await client.call_tool("search_users", {"gender": "female"})
        print(f"   Result preview: {result[:200]}...")
        
        print("\n✅ CustomMCPClient test PASSED")
        
        # Clean up
        if client.http_session:
            await client.http_session.close()
        
        return True
        
    except Exception as e:
        print(f"\n❌ CustomMCPClient test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_with_query():
    """Test the full agent with a real query"""
    print("\n" + "=" * 100)
    print("TEST 3: FULL AGENT WITH REAL QUERY")
    print("=" * 100)
    
    try:
        print("\n→ Setting up multi-client agent...")
        
        # Collect tools from local MCP server
        tools = []
        tool_name_client_map = {}
        
        print("\n→ Connecting to local MCP server...")
        ums_mcp_client = await MCPClient.create("http://localhost:8006/mcp")
        for tool in await ums_mcp_client.get_tools():
            tools.append(tool)
            tool_name_client_map[tool.get('function', {}).get('name')] = ums_mcp_client
        print(f"   ✅ Collected {len(tools)} tools from local server")
        
        # Try to connect to remote fetch server (optional)
        print("\n→ Attempting to connect to remote fetch server...")
        try:
            fetch_mcp_client = await CustomMCPClient.create("https://remote.mcpservers.org/fetch/mcp")
            fetch_tools = await fetch_mcp_client.get_tools()
            for tool in fetch_tools:
                tools.append(tool)
                tool_name_client_map[tool.get('function', {}).get('name')] = fetch_mcp_client
            print(f"   ✅ Collected {len(fetch_tools)} tools from remote fetch server")
        except Exception as e:
            print(f"   ⚠️  Remote fetch server unavailable (this is OK): {e}")
        
        print(f"\n→ Total tools available: {len(tools)}")
        
        # Create DIAL client
        dial_client = DialClient(
            api_key=os.getenv("DIAL_API_KEY"),
            endpoint="https://ai-proxy.lab.epam.com",
            tools=tools,
            tool_name_client_map=tool_name_client_map
        )
        
        # Test query
        messages = [
            Message(
                role=Role.SYSTEM,
                content="You are an advanced AI agent. Your goal is to assist user with his questions."
            ),
            Message(
                role=Role.USER,
                content="Check if Arkadiy Dobkin present as a user, if not then search info about him in the web and add him"
            )
        ]
        
        print("\n→ Sending query to agent:")
        print(f"   '{messages[1].content}'")
        print("\n→ Agent is processing (this may take a moment)...\n")
        
        ai_message = await dial_client.get_completion(messages)
        
        print("\n" + "-" * 100)
        print("AGENT RESPONSE:")
        print("-" * 100)
        print(ai_message.content)
        print("-" * 100)
        
        print("\n✅ Agent test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Agent test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n" + "🎯" * 50)
    print("ADVANCED MCP - COMPREHENSIVE TEST SUITE")
    print("🎯" * 50)
    
    # Check services
    if not await check_services():
        print("\n❌ Service check failed. Please start required services and try again.")
        sys.exit(1)
    
    # Run tests
    results = []
    
    # Test 1: MCPClient
    result1 = await test_mcp_client_library()
    results.append(("MCPClient (Library)", result1))
    
    # Small delay between tests
    await asyncio.sleep(2)
    
    # Test 2: CustomMCPClient
    result2 = await test_custom_mcp_client()
    results.append(("CustomMCPClient (Pure Python)", result2))
    
    # Small delay between tests
    await asyncio.sleep(2)
    
    # Test 3: Full Agent
    result3 = await test_agent_with_query()
    results.append(("Full Agent with Query", result3))
    
    # Summary
    print("\n" + "=" * 100)
    print("TEST SUMMARY")
    print("=" * 100)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:40s} {status}")
    print("=" * 100)
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n🎉 All tests PASSED! Ready to commit and push to GitHub.")
        return 0
    else:
        print("\n❌ Some tests FAILED. Please fix issues before committing.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

