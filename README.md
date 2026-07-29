# AI Code Auditor

面向个人 AI 应用开发者的**本地代码安全审计平台**：规则引擎初筛、LLM 深审验证、结构化报告落盘，支持 Web 控制台与 CI 接入。

> 设计原则：**规则先行、AI 深审、人工确认、先报告后阻断**

---

## 项目背景

随着 AI 应用（Agent、MCP、Skills）快速普及，传统 SAST 工具在以下方面存在明显短板：

| 痛点 | 本项目的应对 |
|------|-------------|
| 静态规则误报多 | 多 detector 初筛 + `verify_llm` 二次裁决降误报 |
| AI 特有风险覆盖弱 | Agent 配置审计（AgentShield）、Prompt 注入规则包 |
| 难以接入个人工作流 | CLI + SARIF + 基线对比 + GitHub Actions |
| 审计工具自身也需安全 | 双轨自审（Semgrep/Bandit + AgentShield） |

本项目借鉴 [defending-code-reference-harness](https://github.com/google/security-hardening) 的流水线形态（find → verify → report），针对 **Python / JavaScript / AI 应用配置** 做多阶段审计，默认本地部署，API Key 仅通过环境变量配置。

---

## 核心能力

| 模块 | 说明 |
|------|------|
| **审计流水线** | `recon` → `find_rules` → `find_llm` → `verify_llm` → `triage` → `report_md` |
| **检测器** | Semgrep、Bandit、gitleaks、npm audit、eslint security、config_audit（AgentShield） |
| **LLM 层** | DeepSeek / Anthropic；deep 模式语义发现 + 结构化 verify |
| **报告** | Markdown / SARIF / JSON；支持中文报告翻译 |
| **Web 控制台** | FastAPI + SQLite；扫描进度 WebSocket、发现 triage、技术雷达 |
| **CI 集成** | 基线对比、PR Comment 模板、`report_only` / `block` 门控 |
| **沙箱验证** | Docker 动态 PoC（可选，`--enable-sandbox`，Linux/WSL2） |
| **知识雷达** | RSS / GitHub Release 聚合，驱动规则演进 backlog |

---

## 项目结构

```
ai-code-auditor/
├── backend/                    # 核心后端
│   ├── api/                    # FastAPI 路由、扫描服务
│   ├── cli.py                  # `ai-auditor` 命令行入口
│   ├── core/                   # 流水线、注册表、基线、LLM 工厂
│   ├── detectors/              # Semgrep / Bandit / gitleaks 等
│   ├── stages/                 # recon / find / verify / triage / report
│   ├── reporters/              # Markdown / SARIF / JSON / PR Comment
│   ├── prompts/                # LLM Prompt + untrusted 数据隔离
│   ├── sandbox/                # Docker PoC 验证（可选）
│   ├── knowledge/              # 技术雷达抓取与打分
│   └── main.py                 # Web 服务入口
│
├── frontend/                   # 控制台静态页面
├── rules/                      # 自定义 Semgrep 规则包（python / js / ai-app）
├── projects/                   # 待扫描项目配置（每项目一个 config.yaml）
├── docs/                       # 实施计划、阶段手册、自审记录
├── tests/                      # 单元 / 集成 / E2E / 沙箱测试
├── .github/workflows/          # CI：self-audit、audit、sandbox
├── modules.yaml                # 检测器、流水线、LLM 模型配置
├── pyproject.toml
└── .env.example
```

### 扫描产物目录（每次扫描独立落盘）

```
results/<project-id>/<timestamp>/
├── recon.json                  # 项目侦察：语言、入口、focus areas
├── THREAT_MODEL.md             # 威胁模型草稿
├── raw_findings.jsonl          # 规则 + LLM 原始发现
├── verified_findings.jsonl     # LLM verify 后
├── TRIAGE.json                 # 去重与 FP 候选
├── AUDIT_REPORT.md             # 人读报告
├── AUDIT_REPORT.zh.md          # 中文报告（--lang zh）
└── scan_meta.json              # 扫描元数据（token、模型、耗时）
```

---

## 环境要求

| 依赖 | 用途 | 必需 |
|------|------|------|
| Python ≥ 3.11 | 运行时 | ✅ |
| [Semgrep](https://semgrep.dev/) | 静态分析 | ✅ |
| [Bandit](https://bandit.readthedocs.io/) | Python 安全 | 推荐 |
| [gitleaks](https://github.com/gitleaks/gitleaks) | 密钥泄露 | 推荐 |
| Node.js / npm / npx | npm audit、eslint、AgentShield | 推荐 |
| Docker | 沙箱动态验证 | 可选（WSL2/Linux） |

---

## 安装

```bash
git clone https://github.com/zlzl-x/ai-code-auditor.git
cd ai-code-auditor

# 创建虚拟环境（推荐）
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
# source .venv/bin/activate

pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY（或 ANTHROPIC_API_KEY）
```

---

## 使用说明

### 1. 注册待扫描项目

在 `projects/<project-id>/config.yaml` 中配置：

```yaml
name: my-ai-app
path: /absolute/path/to/your/repo
languages: [python, javascript, typescript]
exclude:
  - "**/node_modules/**"
  - "**/dist/**"
scan_mode: quick          # quick | deep
fail_on: critical         # CI 阻断阈值（可选）
focus_areas:
  - path: src/api/
    description: "API 入口"
```

### 2. 命令行扫描

```bash
# 快速扫描（跳过 find_llm，适合 CI）
ai-auditor scan --project my-ai-app --mode quick

# 深度扫描（含 LLM 语义发现 + verify）
ai-auditor scan --project my-ai-app --mode deep

# 中文报告
ai-auditor scan --project my-ai-app --mode deep --lang zh

# 输出 SARIF（GitHub Code Scanning）
ai-auditor scan --project my-ai-app --format sarif -o audit.sarif

# 与基线对比，仅报告新增发现
ai-auditor scan --project my-ai-app --baseline main --format sarif -o audit.sarif

# 测试模式（不调用真实 LLM API）
# Windows PowerShell
$env:LLM_CLIENT="mock"
ai-auditor scan --project demo-project --mode quick
```

也可直接调用流水线模块：

```bash
python -m backend.core.pipeline run <project-id> --mode deep --lang zh
```

### 3. Web 控制台

```bash
# 可选：测试时不消耗 API
# $env:LLM_CLIENT="mock"

uvicorn backend.main:app --host 127.0.0.1 --port 8787
```

浏览器打开 `http://127.0.0.1:8787`：

- 首页：技术雷达动态
- 扫描：发起扫描、WebSocket 实时进度
- 发现：查看与 triage 告警
- 设置：模型配置（API Key 仅显示是否已配置，不回传明文）

### 4. 自审与知识刷新

```bash
# 对审计工具自身运行测试 + Semgrep + Bandit + AgentShield
ai-auditor self-audit

# 刷新技术雷达 RSS / GitHub 源
ai-auditor knowledge refresh
```

### 5. CI 集成示例

```yaml
# .github/workflows/audit.yml（仓库内已提供参考）
- name: Security scan
  env:
    LLM_CLIENT: mock
  run: |
    ai-auditor scan --project my-app --format sarif -o audit.sarif --report-mode report_only
```

默认 **`report_only`**：只出报告不阻断合并；误报收敛后可改为 `block` 并设置 `--fail-on critical`。

### 6. 沙箱动态验证（可选）

```bash
# 需要 Linux / WSL2 + Docker
ai-auditor scan --project my-app --enable-sandbox
```

---

## 配置说明

### `modules.yaml`

```yaml
detectors:
  - semgrep
  - bandit
  - gitleaks
  - npm_audit
  - eslint_security
  - config_audit

pipeline:
  - recon
  - find_rules
  - find_llm      # 仅 deep 模式执行
  - verify_llm
  - triage
  - report_md

llm:
  provider: deepseek
  screening_model: deepseek-v4-pro
  verify_model: deepseek-v4-pro
  translate_model: deepseek-v4-flash
  confidence_threshold: 0.8
```

### 环境变量（`.env`）

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥（默认 provider） |
| `ANTHROPIC_API_KEY` | Anthropic 密钥（可选） |
| `LLM_CLIENT=mock` | 测试/CI 模式，不调用真实 API |
| `GITHUB_TOKEN` | 技术雷达 GitHub 抓取（可选，防 rate limit） |
| `GITLEAKS_PATH` | gitleaks 可执行文件路径（可选） |

完整示例见 [`.env.example`](.env.example)。

---

## 开发与测试

```bash
# 运行测试（排除慢速金丝雀扫描）
pytest tests/ -m "not slow" -v

# 类型检查与覆盖率
pytest tests/ -m "not slow" --cov=backend --cov-report=term-missing

# 金丝雀回归（需设置外部项目路径，不提交进仓库）
# $env:CANARY_PROJECT_PATH="D:\path\to\your-ai-app"
# pytest tests/e2e/ -m slow -v
```

---

## 安全提醒

- **切勿**将 `.env`、`results/`、本地数据库提交到 Git（已在 `.gitignore` 中排除）
- API Key 仅通过环境变量或 Web 设置页写入本机，不进日志与前端
- 扫描路径有白名单校验，拒绝 `..` 路径穿越
- 被审计代码作为 untrusted 输入，经 `<untrusted_data>` 隔离后送入 LLM

详见 [`docs/SELF_AUDIT.md`](docs/SELF_AUDIT.md)。

---

## 文档索引

| 文档 | 内容 |
|------|------|
| [`docs/实施计划.md`](docs/实施计划.md) | 完整路线图与架构设计 |
| [`docs/phases/README.md`](docs/phases/README.md) | 分阶段实施手册（M0–M7） |
| [`docs/SELF_AUDIT.md`](docs/SELF_AUDIT.md) | 工具自身安全审计记录 |

---

## 许可证

本项目仅供个人学习与本地安全审计使用。使用前请遵守目标项目许可及 LLM 服务商条款。

---

## 作者

[zlzl-x](https://github.com/zlzl-x)
