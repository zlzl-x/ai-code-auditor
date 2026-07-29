#!/usr/bin/env bash
# Sandbox setup for ai-code-auditor dynamic PoC verification.
set -euo pipefail

step() { printf '\n== %s ==\n' "$*"; }
ok() { printf 'ok  %s\n' "$*"; }
warn() { printf 'warn %s\n' "$*"; }

step "OS check"
if [ "$(uname -s)" != "Linux" ]; then
  warn "Non-Linux host detected. Run sandbox PoCs in WSL2 or Linux CI."
else
  ok "Linux host detected"
fi

step "Docker check"
if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found; install Docker Desktop (WSL2) or Docker Engine" >&2
  exit 1
fi
docker info >/dev/null
ok "docker daemon reachable"

step "Pull probe image"
docker pull python:3.12-slim

step "Network isolation probe"
docker run --rm --network none python:3.12-slim python -c "print('ok')"
ok "network-none container works"

step "Optional gVisor"
if command -v runsc >/dev/null 2>&1; then
  ok "runsc detected (optional hardening available)"
else
  warn "runsc not installed; using default Docker runtime"
fi

ok "Sandbox setup complete"
