# AI Application RulePack

Rules under `rules/ai-app/` target agentic applications:

- Prompt injection via string concatenation (`prompt-injection.yaml`)
- Dangerous `eval` / `exec` (`prompt-injection.yaml`)
- MCP / tool overreach (`tool-overreach.yaml`, `env-leak.yaml`)
- Environment secret logging (`env-leak.yaml`)

Recommended detectors: `semgrep`, `config_audit`, `gitleaks`.
