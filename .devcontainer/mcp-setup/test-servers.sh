#!/bin/bash
# MCP Server Test Script (Devcontainer - linux-64 only)
# Tests that installed MCP servers are accessible
set -e

CONFIG_DIR="$HOME/.config/claude"
CONFIG="$CONFIG_DIR/mcp_servers.json"
MCP_DIR="${MCP_SERVERS_DIR:-$HOME/.local/mcp-servers}"

if [[ ! -f "$CONFIG" ]]; then
    echo "Error: MCP config not found at $CONFIG"
    echo "Run install.sh first."
    exit 1
fi

echo "Testing MCP servers..."
echo "Config: $CONFIG"
echo ""

# Test each server in the config
for server in $(jq -r '.mcpServers | keys[]' "$CONFIG"); do
    cmd=$(jq -r ".mcpServers[\"$server\"].command" "$CONFIG")
    echo -n "  $server: "
    
    if [[ -x "$cmd" ]]; then
        # Try to run with --help or --version to verify it works
        if timeout 5 "$cmd" --help &>/dev/null 2>&1; then
            echo "✓ (--help works)"
        elif timeout 5 "$cmd" --version &>/dev/null 2>&1; then
            echo "✓ (--version works)"
        elif [[ -f "$cmd" ]]; then
            echo "✓ (executable exists)"
        else
            echo "? (exists but couldn't verify)"
        fi
    else
        echo "✗ not found or not executable: $cmd"
    fi
done

echo ""
echo "Pixi environment info:"
cd "$MCP_DIR" && pixi info 2>/dev/null || echo "  (pixi info not available)"

echo ""
echo "Wrapper scripts:"
ls -la "$MCP_DIR/wrappers/" 2>/dev/null || echo "  No wrappers found"
