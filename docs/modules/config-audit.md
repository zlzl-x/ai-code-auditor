# Config Audit Module

The `config_audit` detector wraps `ecc-agentshield` to scan agent configuration:

- `.cursor/` skills, rules, hooks
- `.claude/` settings
- MCP server definitions

## Enablement

Listed in `modules.yaml` detectors. Skipped at runtime unless `.cursor/` or `.claude/` exists in the project root.

## Command

```bash
npx ecc-agentshield scan --path <project_root> --format json --min-severity medium
```

Findings are normalized with `source=agentshield`.
