# AI Application Security Rules

Custom Semgrep rules for AI-assisted applications:

- `prompt-injection.yaml` — prompt concatenation, dangerous eval
- `tool-overreach.yaml` — unrestricted shell/MCP patterns

Referenced by verify prompts in `backend/prompts/defense_patterns.md`.
