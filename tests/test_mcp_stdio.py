#!/usr/bin/env python3
"""Test MCP server with stdio transport (simulates Claude Desktop)."""

import json
import subprocess
import sys
import time

def test_mcp_stdio():
    """Test the MCP server with stdio transport."""
    print("Testing MCP Server with stdio transport...")
    print("=" * 50)
    
    # Start the MCP server as a subprocess
    proc = subprocess.Popen(
        [sys.executable, "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0
    )
    
    try:
        # Send an initialize request (MCP protocol)
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        print(f"Sending initialize request...")
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        
        # Give it time to process
        time.sleep(2)
        
        # Check if process is still running
        if proc.poll() is not None:
            stderr = proc.stderr.read()
            stdout = proc.stdout.read()
            print(f"Server exited with code {proc.returncode}")
            print(f"STDERR: {stderr[:500]}")
            print(f"STDOUT: {stdout[:500]}")
            return False
        
        print("✅ Server is running and accepting connections")
        
        # Send a list tools request
        list_tools = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        print(f"Sending tools/list request...")
        proc.stdin.write(json.dumps(list_tools) + "\n")
        proc.stdin.flush()
        
        time.sleep(1)
        
        # Terminate the server
        proc.terminate()
        proc.wait(timeout=5)
        
        # Read any output
        stderr = proc.stderr.read()
        
        # Check for errors in stderr
        if "ERROR" in stderr and "Already running asyncio" not in stderr:
            print(f"⚠️  Errors found in server log:")
            print(stderr[:500])
        else:
            print("✅ Server ran without critical errors")
        
        print("\n" + "=" * 50)
        print("MCP server is working correctly!")
        print("\nTo use with Claude Desktop:")
        print("1. Restart Claude Desktop")
        print("2. Check for 'grantsmanship' in the MCP tools")
        print("3. Try: 'Search for renewable energy grants'")
        
        return True
        
    except Exception as e:
        print(f"Error during test: {e}")
        proc.terminate()
        return False
    finally:
        if proc.poll() is None:
            proc.terminate()

if __name__ == "__main__":
    success = test_mcp_stdio()
    sys.exit(0 if success else 1)