# Sandbox Dynamic Verification

Optional Docker-based PoC verification for high/critical, verifiable findings.

## Requirements

- Linux or WSL2 (Windows native is **not** supported for PoC execution)
- Docker Engine / Docker Desktop
- Optional: gVisor (`runsc`) for stronger isolation

## Setup

```bash
bash scripts/setup_sandbox.sh
```

## Usage

Sandbox is **off by default**.

```powershell
$env:LLM_CLIENT="mock"
ai-auditor scan --project novel-assistant-v3 --enable-sandbox
```

Or via pipeline API:

```python
run_scan("novel-assistant-v3", enable_sandbox=True)
```

## Safety constraints

- Containers use `--network none` by default
- No `--privileged` or `--network host`
- Read-only snapshot mount at `/work`
- No `.env` or `backend/data/` mounts
- Logs are sanitized (no host absolute paths)
- Egress allowlist via `SANDBOX_EGRESS_ALLOWLIST` when network is enabled

## Outputs

- `SANDBOX.json` in scan results directory
- `AUDIT_REPORT.md` section **Sandbox Verification**
