# MCP Devcontainer Setup with Pixi

This devcontainer configuration sets up MCP (Model Context Protocol) servers using pixi for dependency management.

**Platform:** Linux-64 only (works on all Docker hosts, including Apple Silicon via Rosetta)

## Quick Start

1. Copy the `.devcontainer` folder to your project
2. Open in VS Code and select "Reopen in Container"
3. MCP servers will be installed automatically via `postCreateCommand`

## Configuration

### Choosing an Environment

Set `MCP_ENV` before building the container to choose which servers to install:

```bash
# In devcontainer.json, modify containerEnv:
"containerEnv": {
  "MCP_ENV": "research"  # Options: minimal, default, research, full
}
```

**Available environments:**
- `minimal` - Just filesystem server
- `default` - filesystem, memory, fetch
- `research` - filesystem, arxiv, fetch
- `full` - All servers

### Adding New Servers

#### Option 1: Add to pixi.toml (recommended for PyPI/conda packages)

Edit `.devcontainer/mcp-setup/pixi.toml`:

```toml
[feature.my-new-server]
[feature.my-new-server.pypi-dependencies]
my-new-mcp-server = "*"

# Or from git:
[feature.another-server]
[feature.another-server.pypi-dependencies]
another-server = { git = "https://github.com/user/repo.git" }
```

Then add the feature to an environment:

```toml
[environments]
default = { features = ["filesystem", "memory", "fetch", "my-new-server"], solve-group = "default" }
```

And update `generate-config.sh` to include the new server mapping.

#### Option 2: Clone from git (supports both pixi.toml and pyproject.toml)

Add to `.devcontainer/mcp-setup/servers.txt`:

```
my-server|git-clone|https://github.com/user/my-mcp-server.git|
```

The setup automatically detects and handles:
- **pixi.toml**: Creates isolated conda environment via `pixi install`
- **pyproject.toml**: Installs in shared pixi environment via `pixi run pip install -e`
  - Uses pixi's Python (includes development headers)
  - Avoids missing `Python.h` compilation errors
  - Better binary compatibility via conda-forge packages

### Using the MCP Servers

After installation, the MCP config is at:
```
~/.config/claude/mcp_servers.json
```

Wrapper scripts are at:
```
~/.local/mcp-servers/wrappers/
```

### Testing

Run the test script to verify all servers are working:

```bash
bash .devcontainer/mcp-setup/test-servers.sh
```

### Regenerating Config

If you modify the setup, regenerate the config:

```bash
cd ~/.local/mcp-servers
bash /workspace/.devcontainer/mcp-setup/generate-config.sh default
```

## File Structure

```
.devcontainer/
├── devcontainer.json      # VS Code devcontainer config
├── Dockerfile             # Container image with pixi
└── mcp-setup/
    ├── pixi.toml          # MCP server dependencies
    ├── install.sh         # Main installation script
    ├── generate-config.sh # Generates Claude MCP config
    ├── test-servers.sh    # Tests installed servers
    └── servers.txt        # Git repos to clone
```

## Troubleshooting

### Servers not found

1. Check that pixi installed correctly: `pixi --version`
2. Verify the environment: `cd ~/.local/mcp-servers && pixi info`
3. Check wrapper scripts exist: `ls ~/.local/mcp-servers/wrappers/`

### Permission issues

The setup runs as the `vscode` user. All installations go to user-writable directories:
- `~/.local/mcp-servers/`
- `~/.config/claude/`
- `~/.pixi/`

### Dependency conflicts

If servers have conflicting dependencies, consider:
1. Using separate pixi environments per server
2. Installing conflicting servers via `servers.txt` with their own pixi.toml
