# Python RulePack

Semgrep rules under `rules/python/` cover:

- Hardcoded secrets and API keys
- `subprocess` with `shell=True`
- Unsafe `pickle` deserialization

Run via the `semgrep` detector (included in default `modules.yaml`).
