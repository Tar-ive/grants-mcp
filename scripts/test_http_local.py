#!/usr/bin/env python3
"""Test HTTP MCP server locally"""
import httpx
import asyncio
import json
import sys

async def test_mcp_server():
    base_url = "http://localhost:8081/mcp"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Testing MCP HTTP Server...")
        print("=" * 50)
        
        # Test 1: Initialize
        print("\n1. Testing initialization...")
        try:
            response = await client.post(
                base_url,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream"
                },
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "clientInfo": {
                            "name": "test-client",
                            "version": "1.0.0"
                        }
                    },
                    "id": 1
                }
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Initialization successful")
                result = response.json()
                print(f"Server: {result.get('result', {}).get('serverInfo', {})}")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 2: List tools
        print("\n2. Testing tools/list...")
        try:
            response = await client.post(
                base_url,
                headers={"Content-Type": "application/json"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/list",
                    "id": 2
                }
            )
            if response.status_code == 200:
                tools = response.json().get("result", {}).get("tools", [])
                print(f"✅ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"   - {tool['name']}")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Test 3: Call opportunity_discovery tool
        print("\n3. Testing opportunity_discovery tool...")
        try:
            response = await client.post(
                base_url,
                headers={"Content-Type": "application/json"},
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": "opportunity_discovery",
                        "arguments": {
                            "query": "renewable energy",
                            "max_results": 5
                        }
                    },
                    "id": 3
                },
                timeout=60.0  # Longer timeout for API calls
            )
            if response.status_code == 200:
                print("✅ Tool call successful")
                result = response.json().get("result", {})
                if "content" in result and result["content"]:
                    content = result['content'][0].get('text', '')
                    print(f"Response preview: {content[:200]}...")
            else:
                print(f"❌ Failed: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "=" * 50)
        print("Testing complete!")

if __name__ == "__main__":
    asyncio.run(test_mcp_server())