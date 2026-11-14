# SteerTrace

**审视判断、追溯错误、让决策有据可依，强化你与 AI 协作时的思维方式。**

[English](README.md) · [文档中心](docs/README.md) · [Skill](skills/steer-trace/SKILL.md)

## 概述

SteerTrace 关注你如何定义问题、评估 AI 建议、作出取舍，以及解释不符合预期的结果。
它将关键判断与对话证据联系起来，发现假设与结论之间的缺口，提炼值得延续和强化的思维方式。

分析以交互式 HTML 报告呈现，包含核心发现、原始对话、错误归因和具体的思维强化方向。

## 快速体验

把下面这段话发给你的 Agent：

> 请从 https://github.com/MolMind/SteerTrace 安装 steer-trace 技能，
> 按仓库安装指南适配当前客户端，自动完成所需环境配置与可用性检查。

安装后直接说：

> 分析这个会话。

也可以通过客户端的技能入口调用 `steer-trace`。Agent 会完成分析并交付报告，读取规则如下：

1. **指定了文件或会话**：优先分析指定内容。
2. **说“分析这个会话”或直接调用 Skill**：默认获取当前会话。
3. **排除触发消息**：本次调用消息及之后的内容不进入分析。
4. **无法读取时才请求材料**：不会猜测最近的聊天，也不会用摘要代替原始记录。

## 你会获得什么

- **判断依据**：看清目标、假设与选择之间的联系。
- **错误归因**：区分有依据的解释和超出证据的推断。
- **思维强化方向**：结合本次具体判断，发现值得延续与强化的思考方式。
- **易读报告**：展开原话与上下文，支持搜索、筛选和打印为 PDF。

也可以指定其他会话、提供会话文件，或选择项目文档作为辅助证据。
具体流程见[手动使用](docs/guides/manual-workflow.md)，格式说明见[输入格式](docs/reference/input-formats.md)。

## 文档导航

| 文档 | 内容 |
| --- | --- |
| [安装指南](docs/guides/installation.md) | Agent 自动配置与手动安装说明 |
| [客户端适配](docs/guides/clients.md) | 不同客户端获取当前会话的方式 |
| [手动使用](docs/guides/manual-workflow.md) | 指定文件、项目文档与命令行流程 |
| [常见问题](docs/guides/troubleshooting.md) | 历史不可读、分支和校验问题 |
| [技术文档](docs/README.md) | 数据格式、分析规范、架构与验证 |

## 数据与依据

仅分析当前或明确指定的会话，以及指定文档。报告可能保留原话和业务内容，分享前请检查。
引用校验确认依据对应，不代表每项解释都正确。分析针对可见判断，不评价人格。

## 参与贡献

见[贡献指南](CONTRIBUTING.md)与[版本记录](CHANGELOG.md)。

## 许可证

[MIT](LICENSE) · 版权所有 © 2026 SteerTrace contributors。
随包 [Tabler Icons](https://tabler.io/icons) 同样采用 MIT 许可证，
已保留[上游许可声明](src/steertrace/assets/tabler-LICENSE.txt)。
