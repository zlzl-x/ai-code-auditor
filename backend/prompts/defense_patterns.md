# Defense Patterns Reference

Patterns referenced by verify prompts and ai-app rules:

| Category | Examples |
|----------|----------|
| Injection | SQL/command injection, prompt injection via user content |
| XSS | Unescaped HTML/JS in rendered output |
| Secrets | Hardcoded API keys, tokens, passwords |
| Tool overreach | Unrestricted shell/MCP/tool execution |
| SSRF | User-controlled URLs fetched server-side |

See `rules/ai-app/` for Semgrep rule definitions.
