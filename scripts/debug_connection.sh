#!/bin/bash

echo "MCP Connection Debugger"
echo "======================="

# Check Docker
echo "1. Docker Status:"
docker ps | grep grants-mcp || echo "❌ Container not running"

# Check port
echo -e "\n2. Port 8081 Status:"
lsof -i :8081 || echo "❌ Port 8081 not in use"

# Check HTTP endpoint
echo -e "\n3. HTTP Endpoint Test:"
curl -s -X POST http://localhost:8081/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}' | python3 -m json.tool || echo "❌ Endpoint not responding"

# Check mcp-remote
echo -e "\n4. MCP Remote Proxy:"
which mcp-remote || echo "❌ mcp-remote not found (install with: npm install -g @modelcontextprotocol/mcp-remote)"

# Check Claude config
echo -e "\n5. Current Claude Config:"
grep -A5 "grantsmanship" ~/Library/Application\ Support/Claude/claude_desktop_config.json || echo "❌ No grantsmanship config found"