# ECC-2.0.0 整合说明

> 本文档说明如何将 [ECC-2.0.0](g:\ai安全审计\ECC-2.0.0) 的安全能力与 `ai-code-auditor` 结合，避免与 [defending-code-reference-harness](g:\ai安全审计\defending-code-reference-harness) 职责重叠。

## 三参考项目分工

| 维度 | ECC-2.0.0 | defending-code harness | ai-code-auditor |
|------|-----------|------------------------|-----------------|
| 定位 | AI 编程环境运营系统 | 代码漏洞发现流水线 | 独立审计平台 |
| 扫描对象 | `.cursor/`、hooks、MCP、agent 配置 | 被测 repo 源码 | 你的 AI 应用 repo |
| 引擎形态 | Skill + Agent + `ecc-agentshield` | Python pipeline + 沙箱 | Detector + pipeline + 控制台 |

**一句话：** harness 教「怎么审别人的代码」；ECC 教「怎么审 AI 工具链本身 + 开发时怎么把关」。

## 可借鉴模块

| ECC 模块 | 路径 | 借鉴方式 |
|----------|------|---------|
| AgentShield | `ECC-2.0.0/.cursor/skills/security-scan/SKILL.md` | SELF_AUDIT 轨2；阶段 4 `config-audit` Detector；阶段 5 CI |
| security-reviewer | `ECC-2.0.0/agents/security-reviewer.md` | Prompt Defense → `find_llm`/`verify_llm` |
| security-review | `ECC-2.0.0/.cursor/skills/security-review/SKILL.md` | OWASP checklist → 报告章节 |
| rules/*/security.md | `ECC-2.0.0/rules/` | 阶段 4 RulePack 文案来源 |
| verification-loop | `ECC-2.0.0/.cursor/skills/verification-loop/SKILL.md` | CI 质量门顺序 |
| hooks | `ECC-2.0.0/.cursor/hooks/` | 开发时保护；产品在 pipeline 层实现同类约束 |

## 不建议照搬

- 把整个 ECC 搬进 ai-code-auditor
- 用 `security-audit.ts` 正则替代 gitleaks
- 用 AgentShield 扫业务 Python 代码
- 把 ECC hooks 直接当产品功能

## 各阶段融入摘要

| 阶段 | ECC 融入 |
|------|---------|
| 0 | 阅读 security-scan / security-reviewer；AgentShield baseline |
| 1 | 双轨 SELF_AUDIT；不在此阶段集成 AgentShield Detector |
| 2 | Prompt Defense Baseline + 危险模式表 |
| 3 | 报告 UX、XSS 自测清单 |
| 4 | RulePack 提炼；**config-audit Detector** |
| 5 | CI 双轨扫描 |
| 6 | 几乎无（跟 harness 沙箱） |
| 7 | 团队 `.cursor/` 合规扫描 |

## 能力归属速查

| 能力 | 优先借鉴 |
|------|---------|
| 流水线、verify 对抗 | harness |
| untrusted 数据包裹 | harness `test_untrusted.py` |
| Agent/MCP/hooks 配置审计 | ECC AgentShield |
| OWASP checklist | ECC rules + security-review |
| 密钥扫描 | gitleaks |
| 动态 PoC | harness sandbox |

## 命令速查

```bash
# 轨2：扫 agent 配置
npx ecc-agentshield scan --format json --min-severity medium

# 轨2：HTML 报告
npx ecc-agentshield scan --format html > security-report.html

# 可选深度分析（需 ANTHROPIC_API_KEY）
npx ecc-agentshield scan --opus --stream
```

## 相关文档

- [SELF_AUDIT.md](../SELF_AUDIT.md)
- [phases/README.md](../phases/README.md)
- [实施计划.md](../实施计划.md)
