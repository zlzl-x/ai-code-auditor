# 三参考项目认知笔记（阶段 0）

> 阶段 0 产出。对照 [phase-0.md 附录 A](phases/phase-0.md) 与 [ECC-INTEGRATION.md](reference/ECC-INTEGRATION.md)。

## 一句话分工

- **harness**：教「怎么审别人的代码」— find → verify → report 流水线
- **ECC**：教「怎么审 AI 工具链本身 + 开发时把关」— AgentShield + security-reviewer
- **ai-code-auditor**：产品化整合两者，面向个人 AI 应用 repo 的独立审计平台

## 三参考对照表

| 维度 | harness | ECC-2.0.0 | ai-code-auditor |
|------|---------|-----------|-----------------|
| 定位 | 代码漏洞流水线 | AI 环境运营系统 | 独立审计平台 |
| 扫描对象 | 源码 | `.cursor/`、hooks、MCP | AI 应用 repo |
| 核心借鉴 | pipeline、verify、沙箱、untrusted | AgentShield、RulePack、Prompt Defense | 产品化整合 |
| 关键路径 | `harness/cli.py`、`prompts/` | `skills/security-scan/`、`agents/security-reviewer.md` | `backend/core/` |

---

## 1. defending-code-reference-harness

### 流水线形态（find → verify → report）

| 阶段 | 作用 | ai-code-auditor 映射 |
|------|------|---------------------|
| Recon | 威胁建模、分区 focus area | `stages/recon.py` |
| Find | 规则 + Agent 发现，允许噪声 | `find_rules` + `find_llm` |
| Verify | 对抗式 grader 降误报 | `verify_llm` |
| Triage | 去重、分级、FP 过滤 | `triage` |
| Report | 可读报告 + 修复建议 | `report_md` |

### 最佳实践要点

1. **先映射再扫描**：大项目先做 `/threat-model`，再按组件分区扫描
2. **发现与验证分离**：发现阶段允许噪声；验证阶段用对抗式 grader 降误报
3. **验证器是承重件**：廉价规则门控在前，LLM 验证在后；验证环境与发现环境隔离
4. **并行需分区**：多 Agent 并行时，每个 Agent 必须有明确的 `focus_areas`
5. **Judge 模式**：finder + critic + judge 三角色降误报（`/triage`）

### 安全与沙箱

- 约束必须在**代码**中强制执行，不能仅靠 prompt
- 自主 Agent 在 gVisor 容器内运行，egress 仅限 Claude API
- 不把凭证路径（`~/.aws`、`.env`）挂载进 Agent 环境
- Windows 无 gVisor → 阶段 0–5 纯静态；动态验证放 WSL2/CI（阶段 6）

### 与 Python/JS 的差异

harness 默认 C/C++ + ASAN；ai-code-auditor 只借鉴**流水线形态与 verify 分离思想**，检测器换 Semgrep/Bandit/gitleaks + LLM。

---

## 2. ECC-2.0.0

### AgentShield（轨2）

- 扫描对象：`.cursor/`、`CLAUDE.md`、`settings.json`、`mcp.json`、`hooks/`、`agents/*.md`
- 命令：`npx ecc-agentshield scan --format text`
- **不用于**扫业务 Python/TS 代码（那是轨1 Semgrep/Bandit 的职责）

### security-reviewer（轨3 开发时）

- 实现敏感功能后主动调用
- **Prompt Defense Baseline**：防角色劫持、密钥泄露、不可信外部数据
- OWASP Top 10 checklist → 阶段 2 verify prompt 与阶段 4 RulePack 来源

### 能力归属速查

| 能力 | 优先借鉴 |
|------|---------|
| 流水线、verify 对抗 | harness |
| Agent/MCP/hooks 配置审计 | ECC AgentShield |
| OWASP checklist | ECC rules + security-review |
| 密钥扫描 | gitleaks |
| 动态 PoC | harness sandbox |

---

## 3. 流量监测控制台

### 控制台 UX 参考（nginx-waf-ai/control-panel.html）

| 元素 | 实现要点 | ai-code-auditor 映射 |
|------|----------|---------------------|
| 布局 | 固定侧边栏 + 主内容区 | 概览 / 扫描 / 发现 / 规则 / 项目 / 设置 |
| KPI 卡片 | 今日拦截数、Top IP | Critical/High/Medium/Low 发现数 |
| 事件表 | 最近安全事件 | 审计发现列表 |
| 实时流 | WebSocket 威胁流 | 扫描进度与新发现流 |
| 模式切换 | DetectionOnly vs Blocking | ReportOnly vs BlockMerge |
| 引擎状态 | WAF 引擎卡片 | Semgrep / Bandit / LLM 状态 |

### 阶段划分写法

流量监测计划采用「阶段 0–7 + 每阶段任务清单 + 验收标准 + 出口条件」结构，ai-code-auditor 的 `docs/phases/` 沿用同一模式。

---

## 4. 威胁模型认知（实施计划第 5 节）

### 用 AI 写审计工具的风险

- 功能优先、安全后置；默认信任输入
- 危险写法：`subprocess` 拼 shell、路径未校验、API Key 硬编码
- **原则：用 AI 写代码可以，不能用 AI 代替安全验证**

### 本地部署 ≠ 无风险

| 攻击来源 | 本地工具会不会中招 |
|----------|-------------------|
| 外网直接打 API | 低（绑定 127.0.0.1） |
| 扫描的恶意/被污染项目 | **会** |
| 浏览器 XSS 打本地控制台 | **会** |
| LLM 请求上传商业机密 | **会**（数据出本机） |

### 双轨自审

| 轨道 | 工具 | 扫描对象 |
|------|------|----------|
| 轨1 应用代码 | Semgrep + Bandit | `backend/`、金丝雀 repo |
| 轨2 Agent 配置 | AgentShield | `.cursor/`、hooks、MCP |
| 轨3 开发时 | security-reviewer | 本次改动文件 |

---

## 5. 环境变量

```bash
CANARY_PROJECT_PATH=G:\小说创作助手-v3
```

金丝雀项目为 TypeScript/Electron monorepo，配置见 `projects/novel-assistant-v3/config.yaml`。
