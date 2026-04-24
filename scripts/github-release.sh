#!/usr/bin/env bash

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

v=$(python -c "
import sys
try:
  import tomllib
except ImportError:
  import tomli as tomllib
with open('pyproject.toml', 'rb') as f:
  data = tomllib.load(f)
print(data['project']['version'])
") || exit
p=$(python -c "'--prerelease' if 'rc' in \"$v\" else '--latest' ") || exit

repo=$(basename $(git rev-parse --show-toplevel))
gh repo set-default https://github.com/munch-group/${repo} \
  && gh release create $p "v${v}" --title "v${v}" --notes "" \
  && echo -e "${GREEN}Released version v${v} ${NC}" \
  || echo -e "${RED}Failed${NC}"
