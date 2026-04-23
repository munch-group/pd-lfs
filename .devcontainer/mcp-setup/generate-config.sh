#!/bin/bash
# MCP Server Configuration Generator (Devcontainer - linux-64 only)
# This script generates wrapper scripts and registers MCP servers with Claude Code
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_DIR="${MCP_SERVERS_DIR:-$HOME/.local/mcp-servers}"
CONFIG_DIR="$HOME/.config/claude"
WRAPPER_DIR="$MCP_DIR/wrappers"
MCP_ENV="${1:-default}"

mkdir -p "$WRAPPER_DIR" "$CONFIG_DIR"

# Helper to add server to Claude Code
# Note: We run from /workspace so servers are registered to the correct project
add_server() {
    local name="$1"
    local command="$2"
    shift 2
    local args=("$@")

    echo "  Registering with Claude Code: $name"
    # Run from /workspace to register servers under the workspace project
    # Use || true to prevent failure if server already exists
    if [[ ${#args[@]} -gt 0 ]]; then
        (cd /workspace && claude mcp add --transport stdio "$name" -- "$command" "${args[@]}") || echo "    (already registered)"
    else
        (cd /workspace && claude mcp add --transport stdio "$name" -- "$command") || echo "    (already registered)"
    fi
}

# Create wrapper script for a Python MCP server
create_python_wrapper() {
    local name="$1"
    local module="$2"
    local wrapper="$WRAPPER_DIR/${name}.sh"
    
    cat > "$wrapper" << EOF
#!/bin/bash
cd "$MCP_DIR"
exec pixi run -e "$MCP_ENV" python -m $module "\$@"
EOF
    chmod +x "$wrapper"
    echo "$wrapper"
}

# Create wrapper for Node.js MCP server
create_node_wrapper() {
    local name="$1"
    local package="$2"
    local wrapper="$WRAPPER_DIR/${name}.sh"
    
    cat > "$wrapper" << EOF
#!/bin/bash
cd "$MCP_DIR"
exec pixi run -e "$MCP_ENV" npx $package "\$@"
EOF
    chmod +x "$wrapper"
    echo "$wrapper"
}

# Define server configurations
# Format: name|type|module_or_package
# These should match the features defined in pixi.toml
#
# NOTE: filesystem and fetch are REMOVED - they're built into Claude Code:
# - filesystem: Claude Code has mcp__filesystem__* tools
# - fetch: Claude Code has WebFetch tool
read -r -d '' SERVERS << 'SERVERS_EOF' || true
memory|node|@modelcontextprotocol/server-memory
arxiv|python|arxiv_mcp_server
github|node|@modelcontextprotocol/server-github
sqlite|python|mcp_server_sqlite
SERVERS_EOF

# Map environments to their features
get_env_features() {
    local env="$1"
    case "$env" in
        default)
            echo "memory"
            ;;
        full)
            echo "memory arxiv github sqlite"
            ;;
        research)
            echo "arxiv"
            ;;
        minimal)
            echo ""
            ;;
        *)
            echo ""
            ;;
    esac
}

available_features=$(get_env_features "$MCP_ENV")

echo "Generating config for environment: $MCP_ENV"
echo "Available features: $available_features"

echo "$SERVERS" | while IFS='|' read -r name type module || [[ -n "$name" ]]; do
    [[ -z "$name" ]] && continue
    
    # Check if this server's feature is available in the current environment
    if echo "$available_features" | grep -qw "$name"; then
        echo "  Adding: $name"
        
        case "$type" in
            python)
                wrapper=$(create_python_wrapper "$name" "$module")
                add_server "$name" "$wrapper"
                ;;
            node)
                wrapper=$(create_node_wrapper "$name" "$module")
                add_server "$name" "$wrapper"
                ;;
        esac
    fi
done

# Handle git-cloned repos with their own pixi.toml or pyproject.toml
if [[ -d "$MCP_DIR/repos" ]]; then
    for repo_dir in "$MCP_DIR/repos"/*; do
        [[ -d "$repo_dir" ]] || continue
        name=$(basename "$repo_dir")

        # Check for pixi.toml (conda-based environment)
        if [[ -f "$repo_dir/pixi.toml" ]]; then
            wrapper="$WRAPPER_DIR/${name}.sh"
            cat > "$wrapper" << EOF
#!/bin/bash
cd "$repo_dir"
exec pixi run start "\$@"
EOF
            chmod +x "$wrapper"
            add_server "$name" "$wrapper"
            echo "  Adding (pixi repo): $name"

        # Check for pyproject.toml (pip-based environment installed in shared pixi env)
        elif [[ -f "$repo_dir/pyproject.toml" ]]; then
            wrapper="$WRAPPER_DIR/${name}.sh"

            # Use pixi run to execute in the shared environment
            # This provides Python headers and better binary compatibility
            cat > "$wrapper" << EOF
#!/bin/bash
cd "$MCP_DIR"
exec pixi run -e "$MCP_ENV" python -m $name "\$@"
EOF

            chmod +x "$wrapper"
            add_server "$name" "$wrapper"
            echo "  Adding (pyproject repo): $name"

        # Check for package.json (Node.js-based environment)
        elif [[ -f "$repo_dir/package.json" ]]; then
            wrapper="$WRAPPER_DIR/${name}.sh"

            # Install dependencies if node_modules doesn't exist
            # Use --ignore-scripts to prevent postinstall scripts from running before build
            if [[ ! -d "$repo_dir/node_modules" ]]; then
                echo "  Installing npm dependencies for $name..."
                (cd "$repo_dir" && npm install --ignore-scripts --silent 2>&1 | grep -v "^npm WARN" || true)
            fi

            # Build if there's a build script and no dist/build directory
            if grep -q '"build"' "$repo_dir/package.json" && [[ ! -d "$repo_dir/dist" && ! -d "$repo_dir/build" ]]; then
                echo "  Building $name..."
                (cd "$repo_dir" && npm run build --silent 2>&1 | grep -v "^npm WARN" || true)
            fi

            # Determine how to run the server
            # Check for "start" script first, then look for main/bin entry
            if grep -q '"start"' "$repo_dir/package.json"; then
                cat > "$wrapper" << EOF
#!/bin/bash
cd "$repo_dir"
exec npm run start -- "\$@"
EOF
            else
                # Try to find main entry point
                main_file=$(grep -oP '"main"\s*:\s*"\K[^"]+' "$repo_dir/package.json" 2>/dev/null || echo "")
                if [[ -n "$main_file" && -f "$repo_dir/$main_file" ]]; then
                    cat > "$wrapper" << EOF
#!/bin/bash
cd "$repo_dir"
exec node "$main_file" "\$@"
EOF
                else
                    # Default: try running with npx using the package name
                    cat > "$wrapper" << EOF
#!/bin/bash
cd "$repo_dir"
exec npx . "\$@"
EOF
                fi
            fi

            chmod +x "$wrapper"
            add_server "$name" "$wrapper"
            echo "  Adding (npm repo): $name"
        fi
    done
fi

echo ""
echo "MCP servers registered with Claude Code."
echo "Run 'claude mcp list' to verify."
