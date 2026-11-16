# 文档中心

用户入口：[中文介绍](../README.zh-CN.md) · [English](../README.md)。

## 使用指南 · guides/

- [安装与环境配置](guides/installation.md)：供安装 Agent 或希望手动配置的用户阅读。
- [客户端适配](guides/clients.md)：原生会话读取、当前会话识别与权限边界。
- [手动使用](guides/manual-workflow.md)：指定材料、命令行流程和人工构造示例。
- [常见问题](guides/troubleshooting.md)：定位、分支、覆盖范围和引用校验。

## 格式与约定 · reference/

- [输入格式与覆盖范围](reference/input-formats.md)
- [事件分析规范](reference/event-schema.md)

## 开发与验证 · development/

- [技术架构](development/architecture.zh-CN.md)
- [首版验证记录](development/validation.zh-CN.md)
- [判断分析回归案例与评审判据](development/judgment-validation.zh-CN.md)
- [产出质量对比评测](development/quality-benchmark.zh-CN.md)：24 案例、配对材料、七维匿名评审。
- [第二轮优化与复测](development/round2-optimization.zh-CN.md)：事实核对、预定方向适用性、匿名重复评测。
- [贡献指南](../CONTRIBUTING.md)

Agent 运行规范位于 [Skill](../skills/steer-trace/SKILL.md)，其中的
[会话选择规则](../skills/steer-trace/references/session-selection.md)、
[判断分析方法](../skills/steer-trace/references/analysis-method.md)与
[报告表达规范](../skills/steer-trace/references/report-style.md)作为执行依据。
