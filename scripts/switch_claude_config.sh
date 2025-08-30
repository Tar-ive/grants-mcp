#!/bin/bash

CONFIG_DIR="/Users/tarive/Desktop/grants-data-analysis/grants-mcp/claude_desktop_configs"
CLAUDE_CONFIG="/Users/tarive/Library/Application Support/Claude/claude_desktop_config.json"

echo "Claude Desktop Configuration Switcher"
echo "====================================="
echo "1. Local stdio version (original)"
echo "2. Local Docker version (containerized)"
echo "3. Both versions (for testing)"
echo "4. Show current config"
read -p "Select option (1-4): " choice

case $choice in
    1)
        cp "$CONFIG_DIR/config_local_stdio.json" "$CLAUDE_CONFIG"
        echo "✅ Switched to local stdio version"
        ;;
    2)
        cp "$CONFIG_DIR/config_local_docker.json" "$CLAUDE_CONFIG"
        echo "✅ Switched to Docker version"
        echo "⚠️  Make sure Docker container is running: docker-compose up -d"
        ;;
    3)
        cp "$CONFIG_DIR/config_both.json" "$CLAUDE_CONFIG"
        echo "✅ Enabled both versions"
        ;;
    4)
        echo "Current configuration:"
        cat "$CLAUDE_CONFIG" | python3 -m json.tool
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo ""
echo "⚠️  Restart Claude Desktop for changes to take effect"
echo "   Quit Claude Desktop completely (Cmd+Q) and restart"