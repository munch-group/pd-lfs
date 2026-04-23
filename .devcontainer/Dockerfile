FROM node:20

ARG TZ
ENV TZ="$TZ"

ARG CLAUDE_CODE_VERSION=latest

# Install basic development tools and iptables/ipset
RUN apt-get update && apt-get install -y --no-install-recommends \
  less \
  git \
  procps \
  sudo \
  fzf \
  zsh \
  man-db \
  unzip \
  gnupg2 \
  gh \
  iptables \
  ipset \
  iproute2 \
  dnsutils \
  aggregate \
  jq \
  nano \
  vim \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure default node user has access to /usr/local/share
RUN mkdir -p /usr/local/share/npm-global && \
  chown -R node:node /usr/local/share

ARG USERNAME=node

# Persist bash history.
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  && mkdir /commandhistory \
  && touch /commandhistory/.bash_history \
  && chown -R $USERNAME /commandhistory

# Set `DEVCONTAINER` environment variable to help with orientation
ENV DEVCONTAINER=true

# Create workspace and config directories and set permissions
RUN mkdir -p /workspace /home/node/.claude /home/node/.local/mcp-servers /home/node/.config/claude /home/node/.pixi && \
  chown -R node:node /workspace /home/node/.claude /home/node/.local /home/node/.config /home/node/.pixi

WORKDIR /workspace

ARG GIT_DELTA_VERSION=0.18.2
RUN ARCH=$(dpkg --print-architecture) && \
  wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  sudo dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

# Set up non-root user
USER node

# Install global packages
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin

# Set the default shell to zsh rather than sh
ENV SHELL=/bin/zsh

# Set the default editor and visual
ENV EDITOR=nano
ENV VISUAL=nano

# # Default powerline10k theme
# ARG ZSH_IN_DOCKER_VERSION=1.2.0
# RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \
#   -p git \
#   -p fzf \
#   -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
#   -a "source /usr/share/doc/fzf/examples/completion.zsh" \
#   -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
#   -x

# Install Claude
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}


# Copy and set up firewall script
COPY init-firewall.sh /usr/local/bin/
USER root
RUN chmod +x /usr/local/bin/init-firewall.sh && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall && \
  chmod 0440 /etc/sudoers.d/node-firewall
USER node

# Install pixi (conda-based package manager for MCP servers)
RUN curl -fsSL https://pixi.sh/install.sh | bash

# Install uv (Python package manager for pyproject.toml-based MCP servers)
RUN curl -LsSf https://astral.sh/uv/install.sh | bash

# Update PATH to include pixi, uv, and local binaries
ENV PATH="/home/node/.pixi/bin:/home/node/.cargo/bin:/home/node/.local/bin:${PATH}"

RUN echo 'eval "$(pixi/bin/pixi completion -s bash)"' >> /home/node/.bashrc
RUN echo 'eval "$(pixi/bin/pixi completion -s zsh)"' >> /home/node/.zshrc