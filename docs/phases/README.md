# 各阶段实施手册索引

本目录为 [实施计划.md](../实施计划.md) 的分阶段执行手册。每份文档采用统一 7 节结构，并整合 **harness**、**ECC-2.0.0** 双参考体系。

## 贯穿原则

1. **命令行先跑通再 UI**
2. **ReportOnly 先于 BlockMerge**
3. **审计工具也要被审计**（双轨：Semgrep/Bandit + AgentShield）

## 阶段文档

| 文档 | 里程碑 | 工期 | 要点 |
|------|--------|------|------|
| [phase-0.md](phase-0.md) | M0 | 3–5 天 | 环境、三参考认知、金丝雀、AgentShield baseline |
| [phase-1.md](phase-1.md) | M1 | 1–2 周 | CLI 原型、registry、双轨自审 |
| [phase-2.md](phase-2.md) | M2 | 2–3 周 | LLM verify、Prompt Defense、untrusted |
| [phase-3.md](phase-3.md) | M3 | 2–3 周 | Web 控制台、XSS 防护、雷达首屏 |
| [phase-4.md](phase-4.md) | M4 | 1–2 周 | 多语言、RulePack、config-audit Detector |
| [phase-5.md](phase-5.md) | M5 | 2 周 | CI/CD、SARIF、双轨扫描 |
| [phase-6.md](phase-6.md) | M6 | 2–4 周 | harness 沙箱、动态 PoC（可选） |
| [phase-7.md](phase-7.md) | M7 | 长期 | 企业能力、RBAC、合规 |

## 三参考项目对照

| 参考 | 路径 | 借鉴内容 |
|------|------|----------|
| 审计流水线 | `g:\ai安全审计\defending-code-reference-harness` | pipeline、verify、沙箱、untrusted 测试 |
| Agent 配置审计 | `g:\ai安全审计\ECC-2.0.0` + `ecc-agentshield` | SELF_AUDIT 轨2、config-audit、CI |
| 审查清单与规则 | `ECC-2.0.0/rules/`、`security-review` skill | RulePack、报告、verify prompt |
| 开发时审查 | `ECC-2.0.0/agents/security-reviewer.md` | skills/ 交互审计 |
| 控制台风格 | `G:\流量监测\参考项目\nginx-waf-ai` | 运维控制台布局 |

详见 [ECC-INTEGRATION.md](../reference/ECC-INTEGRATION.md)。

## 金丝雀策略

- 仅使用外部真实 AI 应用 repo（不提交进本仓库）
- 环境变量 `CANARY_PROJECT_PATH` 指向金丝雀路径
- 每阶段结束跑一次完整扫描，与 [SELF_AUDIT.md](../SELF_AUDIT.md) 快照对比

## 统一文档模板（7 节）

1. 阶段目标与边界
2. 任务拆解与交付清单
3. 架构与数据流
4. 难点与应对
5. 安全审计工具的自审要点
6. 测试策略
7. 验收标准与出口条件
