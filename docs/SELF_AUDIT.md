# 工具自身安全审计记录（SELF_AUDIT）

> **原则：** 用 AI 写审计工具可以，不能用 AI 代替安全验证。  
> 本文件记录 `ai-code-auditor` 自身的安全扫描结果，贯穿阶段 1–7（里程碑 M8）。

## 双轨自审

| 轨道 | 工具 | 扫描对象 | 频率 |
|------|------|----------|------|
| **轨1 应用代码** | Semgrep + Bandit | `backend/` | 每批合并前 / PR |
| **轨2 Agent 配置** | `npx ecc-agentshield scan` | `.cursor/`、hooks、MCP、skills | 每批合并前 / PR |
| **轨3 开发时** | ECC `security-reviewer` agent | 本次改动文件 | 实现敏感功能时 |

## 基线检查项（源自 ECC `rules/common/security.md`）

### 提交前强制检查

- [x] `results/` 已在 `.gitignore`（M0 已添加）
- [x] 扫描路径白名单生效，拒绝 `..` 穿越（`path_validation.py` + 测试）
- [x] subprocess 使用参数数组，`shell=False`（`subprocess_runner.py` + `# nosec B603`）
- [x] 所有用户输入已校验（路径、项目 ID、scan 参数）（阶段 1 `load_project_config` / CLI）
- [x] API Key 仅环境变量，不进日志/前端/Git（`ANTHROPIC_API_KEY` + `LLM_CLIENT=mock` 测试门控）
- [x] untrusted 数据块隔离（`backend/prompts/untrusted.py` + 单元测试）
- [x] 上传前文件 denylist（`.env`、`*secret*` 等，`file_filter.py`）
- [x] 控制台输出 HTML 已转义（`escapeHtml()` + `textContent`；`test_escape_html.py` / `test_xss_findings.py`）

## 发现记录

| 日期 | 轨道 | 工具 | 严重度 | 文件/规则 | 描述 | 状态 | 负责人 |
|------|------|------|--------|-----------|------|------|--------|
| 2026-07-28 | 轨2 | AgentShield | — | — | M0：A (100/100)，尚无 `.cursor/` | accepted | — |
| 2026-07-28 | 轨1 | Semgrep | — | — | M0 docs 阶段：0 发现 | accepted | — |
| 2026-07-28 | 轨1 | Semgrep | — | — | M1 `backend/`：0 发现 | accepted | — |
| 2026-07-28 | 轨1 | Bandit | low | B404/B603 | `subprocess_runner.py` 安全封装内 subprocess 调用 | accepted | — |
| 2026-07-28 | 轨1 | Semgrep | — | — | M2 `backend/`：0 Critical（自扫） | accepted | — |

**状态：** `open` | `fixed` | `accepted` | `false_positive`

## AgentShield 评分历史

| 日期 | 评分 | 等级 | 命令 | 备注 |
|------|------|------|------|------|
| 2026-07-28 | 100 | A | `npx ecc-agentshield scan --path g:\ai安全审计\ai-code-auditor` | M0/M1：尚无 `.cursor/` |
| 2026-07-28 | 100 | A | 同上 | M1 复扫：无变化 |

## 金丝雀回归快照

金丝雀项目：`G:\小说创作助手-v3`（`novel-assistant-v3`）  
环境变量：`CANARY_PROJECT_PATH=G:\小说创作助手-v3`

| 阶段 | 日期 | 总发现数 | Critical | High | 备注 |
|------|------|----------|----------|------|------|
| M0 baseline | 2026-07-28 | 138+ | 9 | 34+ | 手动扫描，见下方分项 |
| M1 pipeline | 2026-07-28 | 122 | 0 | 1+ | `python -m backend.core.pipeline run novel-assistant-v3` |
| M2 pipeline | 2026-07-28 | 122 raw / ~122 verified | 0 | 1+ | quick 模式 + `LLM_CLIENT=mock` verify/triage/report |
| M3 web console | 2026-07-29 | — | — | — | FastAPI @ `127.0.0.1:8787` + 雷达首屏 |
| M4 multi-language | 2026-07-29 | TBD | TBD | TBD | gitleaks + npm + eslint + config_audit + THREAT_MODEL.md |
| M5 CI/SARIF | 2026-07-29 | TBD | TBD | TBD | `ai-auditor` CLI + SARIF + GitHub Actions |
| M6 sandbox | 2026-07-29 | TBD | TBD | TBD | Docker PoC 默认关闭；`--enable-sandbox` |

### M6 动态验证与沙箱

| 项 | 状态 | 备注 |
|----|------|------|
| verify_sandbox stage | OK | triage 后条件执行；默认关闭 |
| SandboxRunner | OK | `--network none`、只读快照、资源限制 |
| egress allowlist | OK | `backend/sandbox/egress.py` |
| verifiable filter | OK | high/critical + CWE/rule 命中 |
| CLI `--enable-sandbox` | OK | Linux/WSL2 + Docker |
| SANDBOX.json | OK | results 目录产物 |
| setup_sandbox.sh | OK | `scripts/setup_sandbox.sh` |
| sandbox CI | OK | `.github/workflows/sandbox.yml` |

**Windows 用户：** 在 WSL2 中运行 `ai-auditor scan --enable-sandbox`。

### M5 CI/CD 接入

| 项 | 状态 | 备注 |
|----|------|------|
| CLI `ai-auditor` | OK | `scan` / `self-audit` / `knowledge refresh` |
| SARIF Reporter | OK | 无 evidence；JSON schema 2.1.0 |
| JSON Reporter | OK | `--include-evidence` 可选 |
| 基线对比 | OK | `baselines/<project>/<branch>.json`；默认仅 new |
| ReportOnly / Block | OK | 默认 `report_only`；`block` + `--fail-on` |
| PR Comment 模板 | OK | 纯 Markdown，`--pr-comment-out` |
| GitHub Actions | OK | `.github/workflows/self-audit.yml`、`audit.yml` |

**CLI 示例：**
```powershell
$env:LLM_CLIENT="mock"
ai-auditor scan --project novel-assistant-v3 --format sarif -o audit.sarif --baseline main --report-mode report_only
ai-auditor scan --project novel-assistant-v3 --mode deep --lang zh   # verify: v4-pro, translate: v4-flash
ai-auditor self-audit
```

**CI 注意：** 不在 workflow 中 `echo` secrets；`AUTO_LLM_CURATE` 默认关闭。

### M4 多语言与配置审计

| 项 | 状态 | 备注 |
|----|------|------|
| gitleaks detector | OK | 证据 `redact_secret()` 打码 |
| npm_audit detector | OK | 需 `package.json` + `npm` |
| eslint_security detector | OK | 需 `npx` + eslint 配置 |
| config_audit (AgentShield) | OK | `.cursor/` 或 `.claude/` 存在时运行 |
| ECC RulePack | OK | `rules/python/`, `rules/javascript/`, `rules/ai-app/` |
| THREAT_MODEL.md | OK | recon 阶段生成 |
| GitHub Release 雷达 | OK | `backend/knowledge/fetchers/github.py` |
| auto_backlog.json | OK | `knowledge/auto_backlog.json` |
| AUTO_LLM_CURATE | OK | `AUTO_LLM_CURATE=true` + `DEEPSEEK_API_KEY` |
| rules reload 加固 | OK | 拒绝 `rules/` 外路径 |

**前置条件：**
- Node.js / `npm` / `npx`（npm audit、eslint、ecc-agentshield）
- `.tools/gitleaks.exe` 或 `GITLEAKS_PATH`
- 可选：`GITHUB_TOKEN`（GitHub Release 防 rate limit）

**验收命令：**
```powershell
$env:LLM_CLIENT="mock"
pytest tests/ -m "not slow" -v
python -m backend.core.pipeline run novel-assistant-v3 --mode quick
```

### M3 Web 控制台

| 项 | 状态 | 备注 |
|----|------|------|
| FastAPI + SQLite | OK | `backend/main.py` + `backend/models/` |
| 技术雷达首屏 | OK | `GET /api/knowledge/feed` |
| 扫描 WebSocket | OK | `WS /api/scans/{id}/stream` |
| Findings triage | OK | `PATCH /api/findings/{id}` |
| XSS 防护 | OK | `escape_html` + 前端 `textContent` |
| API Key 不进前端 | OK | Settings 仅 `api_key_configured` 布尔值 |
| 绑定 localhost | OK | `uvicorn --host 127.0.0.1` |

**启动：**
```powershell
$env:LLM_CLIENT="mock"   # 可选
uvicorn backend.main:app --host 127.0.0.1 --port 8787
```

### M2 分项（verify + triage + report）

| 产物 | 状态 | 备注 |
|------|------|------|
| `raw_findings.jsonl` | OK | find_rules (+ find_llm deep) |
| `verified_findings.jsonl` | OK | verify_llm 门控 high/low-confidence |
| `TRIAGE.json` | OK | 去重 + FP 候选 |
| `AUDIT_REPORT.md` | OK | markdown reporter |
| `scan_meta.json` | OK | 含 `tokens_in` / `tokens_out` / `models_used` |

### M2 LLM 人工抽检（占位）

| 抽检数 | FP 率 | 备注 |
|--------|-------|------|
| 10 | TBD | 需真实 API Key 运行后填写 |

### M1 分项（流水线产出）

| 工具 | 发现数 | 代表规则 | 备注 |
|------|--------|----------|------|
| Semgrep | 1 | `spawn-shell-true` @ `rebuild-native.mjs` | 与 M0 一致 |
| Bandit | 121 | B603/B101 等 @ `.cursor/skills` | 仅 Python skills |

### M0 分项明细

| 工具 | 扫描范围 | 总发现 | Critical | High | Medium | Low | 备注 |
|------|----------|--------|----------|------|--------|-----|------|
| Semgrep 1.171.0 | `apps/` + `packages/` | 1 | 0 | 1 | 0 | 0 | 手动 baseline |
| Bandit 1.9.4 | `.cursor/skills/` | 121 | 0 | 0 | 1 | 120 | 手动 baseline |
| gitleaks 8.24.2 | 全 repo | 16 | — | — | — | — | 手动 baseline |
| AgentShield 1.5.0 | 金丝雀 `.cursor/` | 363 | 9 | 33 | 129 | 184+8 info | 等级 F (34/100) |

## 工具链版本

| 工具 | 版本 | 状态 |
|------|------|------|
| Python | 3.12.6 | OK |
| Semgrep | 1.171.0 | OK |
| Bandit | 1.9.4 | OK |
| gitleaks | 8.24.2 | OK（`.tools/gitleaks.exe`） |
| ecc-agentshield | 1.5.0 | OK（npx） |
| Docker | 29.5.3 | OK |

## 测试与覆盖率（M6）

- 单元 + 集成：**95+ passed**（`pytest -m "not slow and not sandbox"`）
- 新增：`tests/sandbox/test_egress_allowlist.py`、`test_verifiable_filter.py`、`test_sandbox_runner.py`、`test_verify_sandbox.py`
- Linux CI：`pytest tests/sandbox/ -m sandbox`

## 测试与覆盖率（M5）

- 单元 + 集成：**85+ passed**（`LLM_CLIENT=mock`）
- 新增：`test_sarif_schema.py`、`test_sarif_escape.py`、`test_baseline_diff.py`、`test_cli_exit_codes.py`、`test_pr_comment.py`、`test_cli_scan.py`
- CLI entry point：`ai-auditor`（`pyproject.toml` `[project.scripts]`）

## 测试与覆盖率（M4）

- 单元 + 集成：**60+ passed**（`LLM_CLIENT=mock`）
- 新增：`test_severity_mapping.py`、`test_gitleaks_parser.py`、`test_config_audit.py`、`test_npm_audit_detector.py`、`test_rules_reload.py`、`test_github_fetcher.py`、`test_backlog.py`、`test_knowledge_curate.py`、`test_threat_model.py`
- Detectors：`semgrep`, `bandit`, `gitleaks`, `npm_audit`, `eslint_security`, `config_audit`

## 测试与覆盖率（M3）

- 单元 + 集成 + 安全：**43+ passed**（`LLM_CLIENT=mock`）
- 新增：`test_api.py`、`test_api_websocket.py`、`test_escape_html.py`、`test_xss_findings.py`
- Web 控制台：`http://127.0.0.1:8787`

## 测试与覆盖率（M2，历史）

## 测试与覆盖率（M1，历史）

- 单元 + 集成：21 passed
- E2E 金丝雀：`tests/e2e/test_canary_scan.py` passed
- `backend/core/` 覆盖率：**93%**（目标 ≥80%）

## 响应协议

发现 **Critical** 时：

1. 停止相关功能开发
2. 修复并复扫双轨
3. 若涉及密钥泄露，立即轮换
4. 全库检索同类问题

## 相关文档

- [实施计划 第 5 节](实施计划.md#5-工具自身安全与本地部署威胁模型)
- [ECC 整合说明](reference/ECC-INTEGRATION.md)
- [三参考认知笔记](reference/COGNITION-NOTES.md)
- [各阶段实施手册](phases/README.md)
