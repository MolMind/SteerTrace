# 手动使用与指定材料

日常可直接让 Agent“分析这个会话”。本页供需要指定文件、文档、范围或手动运行命令时参考。
命令在仓库根目录执行，示例路径需替换为实际路径；安装见[安装指南](installation.md)。

## 指定材料

可以告诉 Agent：

> 使用 steer-trace，分析 /actual/session.jsonl，结合项目 /actual/project 中的
> docs/plan.md 和 docs/results.md，生成 HTML 报告。

显式目标优先于当前会话；不要在指定文件不可读时悄悄换成当前会话。
历史文件默认导入全部保留对话，用户指定范围时遵循指定范围。

## 命令行流程

### 1. 导入会话

```bash
steertrace import --input /actual/session.jsonl --source auto \
  --output runs/conversation.json
```

当前会话使用 `capture`，以原始触发消息的 ID 为不包含端点：

```bash
steertrace capture --input /actual/session.jsonl --source auto \
  --before-message-id ACTUAL_MESSAGE_ID --output runs/current-conversation.json
```

ID 由客户端原始记录取得。也支持 `--before-text-file` 的唯一完整原文匹配。
具体读取和分支规则见[会话选择规则](../../skills/steer-trace/references/session-selection.md)。

### 2. 保存证据材料

```bash
steertrace prepare --conversation runs/conversation.json \
  --project /actual/project --docs docs/plan.md docs/results.md \
  --output runs/review-001
```

`--docs` 相对于项目目录，支持明确指定的 Markdown 文件或目录。
不提供该参数则没有文档证据，不代表允许扫描全部项目。

### 3. 由当前 Agent 分析

Agent 按 [Skill](../../skills/steer-trace/SKILL.md) 读取 `ANALYZE.md`、全部编号证据包、
事件模板与[分析约定](../reference/event-schema.md)，生成 `events.json`。
Python 不代替 Agent 完成语义分析，也不另行调用模型。

### 4. 校验与生成报告

```bash
steertrace validate --run runs/review-001 --events runs/review-001/events.json \
  --output runs/review-001/validation.json

steertrace report --run runs/review-001 --events runs/review-001/events.json \
  --output runs/review-001/report.html
```

浏览器打开 HTML 即可阅读。分析字段遵循[表达规范](../../skills/steer-trace/references/report-style.md)，
HTML 结构与交互由固定渲染器合成。程序校验引用对应，不证明全部解释正确。
运行目录不会覆盖；重复执行使用新输出位置。

## 人工构造示例

```bash
python scripts/demo.py runs/demo
```

打开 `runs/demo/report.html`。示例会话与分析均为人工构造，用于检查整理、校验和报告链路，
不是自动分析准确率或当前客户端会话读取能力的评测。
