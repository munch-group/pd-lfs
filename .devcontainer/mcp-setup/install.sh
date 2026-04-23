#!/bin/bash
# MCP Server Installation Script (Devcontainer - linux-64 only)
# Installs pixi and MCP servers in the devcontainer environment
set -e

echo "=== MCP Installation Starting ==="
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "HOME: $HOME"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "SCRIPT_DIR: $SCRIPT_DIR"

MCP_DIR="${MCP_SERVERS_DIR:-$HOME/.local/mcp-servers}"
CONFIG_DIR="$HOME/.config/claude"
WRAPPER_DIR="$MCP_DIR/wrappers"

# Ensure pixi and uv are in PATH (installed in Dockerfile)
export PATH="$HOME/.pixi/bin:$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
echo "PATH: $PATH"
echo ""

# Check for pixi
if command -v pixi &> /dev/null; then
    echo "✓ Found pixi: $(which pixi)"
else
    echo "✗ ERROR: pixi not found in PATH"
    echo "Checking installation directory..."
    ls -la "$HOME/.pixi/bin/" 2>&1 || echo "  $HOME/.pixi/bin/ does not exist"
    exit 1
fi

# Check for uv
if command -v uv &> /dev/null; then
    echo "✓ Found uv: $(which uv)"
else
    echo "✗ ERROR: uv not found in PATH"
    echo "Checking installation directory..."
    ls -la "$HOME/.cargo/bin/" 2>&1 || echo "  $HOME/.cargo/bin/ does not exist"
    exit 1
fi

echo ""
mkdir -p "$MCP_DIR" "$CONFIG_DIR" "$WRAPPER_DIR"

# Copy pixi.toml to MCP directory
if [[ ! -f "$SCRIPT_DIR/pixi.toml" ]]; then
    echo "Error: pixi.toml not found at $SCRIPT_DIR/pixi.toml"
    echo "SCRIPT_DIR: $SCRIPT_DIR"
    ls -la "$SCRIPT_DIR/"
    exit 1
fi

cp "$SCRIPT_DIR/pixi.toml" "$MCP_DIR/"
cd "$MCP_DIR"

# Choose which environment to install (can be overridden via MCP_ENV)
MCP_ENV="${MCP_ENV:-default}"
echo "Installing MCP servers (environment: $MCP_ENV)..."

# Install the pixi environment
pixi install -e "$MCP_ENV"

# Process git-based servers that need cloning (defined in servers.txt)
if [[ -f "$SCRIPT_DIR/servers.txt" ]]; then
    while IFS='|' read -r name type source extra || [[ -n "$name" ]]; do
        [[ "$name" =~ ^#.*$ || -z "$name" ]] && continue
        
        if [[ "$type" == "git-clone" ]]; then
            echo "Cloning $name from $source..."
            repo_dir="$MCP_DIR/repos/$name"
            mkdir -p "$MCP_DIR/repos"
            
            if [[ -d "$repo_dir" ]]; then
                git -C "$repo_dir" pull
            else
                git clone "$source" "$repo_dir"
            fi
            
            # If it has a pixi.toml, install it
            if [[ -f "$repo_dir/pixi.toml" ]]; then
                echo "  Installing pixi environment for $name..."
                (cd "$repo_dir" && pixi install)
            # If it has a pyproject.toml, install in shared pixi environment with pip
            # This avoids missing Python.h errors and provides better binary compatibility
            elif [[ -f "$repo_dir/pyproject.toml" ]]; then
                echo "  Installing Python package in pixi environment for $name..."
                (cd "$MCP_DIR" && pixi run -e "$MCP_ENV" pip install -e "$repo_dir")
            fi
        fi
    done < "$SCRIPT_DIR/servers.txt"
fi

# Generate wrapper scripts and config
bash "$SCRIPT_DIR/generate-config.sh" "$MCP_ENV"

# # Install Claude CLI (using Node.js 20 from pixi environment)
# if ! command -v claude &> /dev/null; then
#     echo ""
#     echo "Installing Claude CLI..."
#     curl -fsSL https://storage.googleapis.com/claude-cli/install.sh | bash
#     export PATH="$HOME/.local/bin:$PATH"
# fi

echo ""
echo "✓ MCP servers installed"
echo "  Environment: $MCP_ENV"
echo "  Config: $CONFIG_DIR/mcp_servers.json"
echo "✓ Claude CLI installed: $(command -v claude || echo 'not found')"
