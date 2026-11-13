# SteerTrace

**看清使用 AI 时的判断依据，理解错误怎样发生，改进下一次思考。**

SteerTrace 是一个分析 AI 使用过程中思维判断与错误归因的 Skill。它结合你指定的
Agent 会话和项目文档，梳理你如何定义问题、评估 AI 建议、作出取舍，以及发现问题后
如何解释和纠正错误。分析聚焦每个判断有什么依据、推断在哪里超出了证据，帮助你识别
值得延续和强化的思维方式，并以 HTML 报告呈现。

[English](../README.md) · [判断分析 Skill](../skills/collaboration-judgment-review/SKILL.md)

## 目录

- [概述](#概述)
- [主要功能](#主要功能)
- [环境要求与安装](#环境要求与安装)
- [快速体验](#快速体验)
- [在 Codex 等客户端中使用](#在-codex-等客户端中使用)
- [复盘自己的会话](#复盘自己的会话)
- [支持的输入与限制](#支持的输入与限制)
- [数据与隐私](#数据与隐私)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [开发与贡献](#开发与贡献)
- [许可证](#许可证)

## 概述

项目由本地 Python 命令行工具与 Agent Skill 组成。Python 工具负责导入会话、冻结材料、
校验引用和生成报告；当前客户端里的 Agent 负责分析，无需额外配置模型 API Key。
当前版本为 0.1.0，仓库尚未提供 MCP 服务或客户端插件。

使用 AI 时，提出问题、接受答案、要求修改和确认结果，都包含人的判断。
SteerTrace 关注这些判断背后的依据与推理，尤其是在结果出错或不符合预期时，
你如何从现象推断原因，又凭什么决定下一步。

它围绕以下问题组织分析：

- **问题如何定义**：目标、约束和验收标准是否明确？后续判断依据的是最初目标还是临时假设？
- **建议如何评估**：接受或否定 AI 方案时依据了什么？是否把表达自信、局部成功或未经验证的说法当成充分证据？
- **错误如何归因**：现有证据能否区分需求表达、人的决策、AI 输出和执行环境等可能来源？是否过早认定了某个原因？
- **判断如何修正**：新证据出现后，哪些假设被保留或推翻？下一次应在哪个决策点增加什么检查？

例如，某个样本通过后就认定方案普遍有效，分析会指出从局部结果推到通用结论时
缺少了哪些证据；出现失败后直接认定“模型能力不行”，则需要检查材料是否足以排除
需求歧义、输入缺失或执行条件等其他解释。原因无法确定时应保留不确定性。

分析只依据可见的对话与文档，不重建未表达的内心思维，也不凭先后顺序断言因果。
结论针对本次具体判断，不能由单次会话推断一贯习惯，也不评价人格和智力。

## 主要功能

- **梳理判断依据**：将目标、假设、选择与后续回应联系起来，区分原话、解释和验证结果。
- **检查错误归因**：指出归因中有证据支持的部分、未经验证的推断和仍不能确定的原因。
- **指出推理问题**：说明具体判断的问题、可能代价和更好的行动；证据不足时不强行批评。
- **提炼思维强化方向**：呈现值得延续的思维方式，结合具体情境说明目标意识、证据意识与验证边界的价值，最多三项。
- **离线阅读报告**：生成独立 HTML，支持手机阅读、搜索、筛选、目录跳转和打印为 PDF，
  无需服务器、远程字体或图表服务。

报告按“阅读导引、核心结论、判断与归因、判断过程、思维强化方向”展开。
界面采用简约配色、圆润内容区与自然留白；桌面导读支持滚动与点击切换，手机使用步骤按钮。
对话与文档可通过点击或键盘展开，图标随状态变化；支持减少动态效果与无 JavaScript 阅读。

不确定性与覆盖范围保留在内部分析文件中，必要限定融入对应结论，不单独展示冗长限制章节。

引用校验只检查引用与结构，不证明解释正确、方案有效或建议必然带来改善。
报告区分人的要求、AI 的方案、人的选择与授权、文档记录和已观察到的结果。

## 环境要求与安装

需要 Python 3.9 或以上版本及 pip，无额外运行时第三方依赖。
完整复盘流程需要能读取本地文件、执行终端命令的 Agent 客户端。

克隆仓库并从源码安装（macOS/Linux）：

```bash
git clone https://github.com/MolMind/SteerTrace.git
cd SteerTrace
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell 可用 `python -m venv .venv` 创建环境，使用
`.venv\Scripts\Activate.ps1` 激活，再执行上述 pip 命令。

macOS/Linux 下也可不安装，直接用 `PYTHONPATH=src python3 -m steertrace` 代替
后续命令中的 `steertrace`。

## 快速体验

安装后，在仓库根目录运行：

```bash
python scripts/demo.py runs/demo
```

用浏览器打开 `runs/demo/report.html`。示例对话与分析均为人工构造，用于展示报告和
校验流程。重复运行请换一个输出目录，程序不会覆盖已有材料。

## 在 Codex 等客户端中使用

在 Codex 或其他支持本地文件和终端的 Agent 客户端中打开仓库，直接指定 Skill 即可。
例如发送：

> 请读取并使用 skills/collaboration-judgment-review/SKILL.md，复盘
> /path/to/session.jsonl 会话。项目目录为 /path/to/project，文档限定为
> docs/plan.md 和 docs/results.md。使用本仓库的 .venv/bin/steertrace，
> 最终生成 runs/review-001/report.html。

客户端工作目录不在仓库中时，请提供绝对路径。Windows 中工具路径为
`.venv\Scripts\steertrace.exe`。Skill 引用的仓库文档也需要保持可访问，不能只复制
一个 SKILL.md 就认为安装完整。此方式无需客户端专用的 Skill 安装步骤。

仅支持 MCP 的客户端需要额外开发 MCP 适配层；本仓库尚未提供该能力。
仅支持聊天的客户端需要你手动执行命令，并在步骤之间传递证据材料与分析结果。
安装工具不会自动扫描客户端的全部会话，需要明确指定导出文件。

## 复盘自己的会话

以下命令均在仓库根目录执行。将示例路径替换为实际会话与项目目录。

**1. 导入指定会话**

```bash
steertrace import --input /path/to/session.jsonl --source auto \
  --output runs/conversation.json
```

**2. 保存本次材料**

```bash
steertrace prepare --conversation runs/conversation.json \
  --project /path/to/project --docs docs/plan.md docs/results.md \
  --output runs/review-001
```

`--docs` 指定相对于项目目录的 Markdown 文件或目录；不提供文档列表时不收集文档证据。

**3. 让当前 Agent 分析**

让 Agent 按照[判断分析 Skill](../skills/collaboration-judgment-review/SKILL.md)读取
`runs/review-001/ANALYZE.md`、全部编号证据包和事件模板，生成
`runs/review-001/events.json`。这一步需要 Agent 的语义分析，不会由 Python 自动完成。

**4. 校验并生成报告**

```bash
steertrace validate --run runs/review-001 --events runs/review-001/events.json \
  --output runs/review-001/validation.json

steertrace report --run runs/review-001 --events runs/review-001/events.json \
  --output runs/review-001/report.html
```

用浏览器打开最终 HTML。正文措辞遵循[报告规范](../skills/collaboration-judgment-review/references/report-style.md)，
布局与交互由固定模板提供。

## 支持的输入与限制

支持带角色标记的通用 JSON、指定的 Codex JSONL 和基本父子链结构的 Claude Code JSONL。
不保证覆盖所有历史版本、远程会话或专有存储格式。Claude 分支有歧义时需要明确指定
`--leaf-id`；缺失或压缩历史会影响覆盖范围。

会话文件默认上限为 128 MiB，JSONL 单条记录默认上限为 8 MiB。文档仅收集项目目录内
明确指定的 Markdown，数量与大小也有限制。完整格式、分支处理和参数说明见
[输入格式与覆盖范围](input-formats.md)。

## 数据与隐私

只读取明确指定的会话和文档，不自动发现账户里的所有历史。会话与报告默认放在
Git 忽略的 `runs/` 中。凭据脱敏是基础保护，业务内容、路径与原话仍可能保留，分享前请检查。
Agent 读取材料时，遵循所在平台和模型服务的数据政策。

用户提交要求、AI 提出方法、用户选择和同意继续是不同的参与方式。报告不会将 AI 方案
全部归为人的思考，也不会因为一句“继续”认定用户理解所有细节。文档记录不等于本次
重新测试，缺少讨论也不代表没有思考。

## 项目结构

```text
src/steertrace/                       命令行、导入、校验及 HTML 资源
skills/collaboration-judgment-review/ Agent 工作流程与报告规范
scripts/demo.py                      人工构造示例的完整流程
examples/synthetic/                  示例会话、文档和分析
tests/                              导入与报告流程测试
docs/                               输入格式、事件规范和架构文档
runs/                               本地输出，不提交到 Git
```

## 常见问题

- **找不到 steertrace 命令**：激活虚拟环境，或直接运行 `.venv/bin/steertrace`；
  Windows 使用 `.venv\Scripts\steertrace.exe`。
- **提示输出已存在**：更换输出文件或运行目录，程序不会覆盖已有材料。
- **Claude 会话分支不明确**：导入时通过 `--leaf-id <uuid>` 选择分支。
- **会话不完整，prepare 拒绝继续**：先确认覆盖范围；接受已披露的缺失后，
  才使用 `prepare --allow-partial`。
- **引用校验失败**：对照冻结证据修正分析，不要修改证据来让校验通过。

运行 `steertrace --help` 或 `steertrace <子命令> --help` 查看参数。

## 开发与贡献

在仓库根目录执行测试，并用新目录运行公开示例：

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python scripts/demo.py runs/another-demo
```

贡献前请阅读 [CONTRIBUTING.md](../CONTRIBUTING.md)。提交问题时附上命令、Python 版本
和错误信息，使用人工构造样本，避免提交私人会话、截图、凭据或生成目录。

更多说明：[版本记录](../CHANGELOG.md) · [技术架构](architecture.zh-CN.md) · [事件分析规范](event-schema.md) ·
[实现验证说明](implementation-validation.zh-CN.md)。

## 许可证

本项目采用 [MIT 许可证](../LICENSE)。版权所有 © 2026 SteerTrace contributors。
允许使用、复制、修改、分发及商业使用，但须保留版权声明和许可声明。
软件按原样提供，不附带担保，完整条款以 LICENSE 文件为准。

随包 SVG 图标来自 [Tabler Icons](https://tabler.io/icons)，采用 MIT 许可证。
[上游版权与许可声明](../src/steertrace/assets/tabler-LICENSE.txt) 随包分发，并内嵌于生成报告。
