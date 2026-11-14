# 安装与环境配置

面向负责安装的 Agent，以及希望手动配置的用户。日常入口见[快速体验](../../README.zh-CN.md#快速体验)。

## Agent 安装流程

用户提供仓库地址后，由 Agent 完成以下工作，不要求用户先了解 Python 版本或命令：

1. 确认当前客户端支持 Skill、本地文件与命令执行，查看该客户端实际支持的安装位置和安装机制。
2. 将完整仓库获取到持久目录，优先复用已有 checkout，避免放在会自动清理的临时目录。
3. 检查可用 Python，创建隔离环境并安装本项目；所需版本和依赖以 `pyproject.toml` 为准。
4. 将 `skills/steer-trace/` 注册到客户端。支持链接时可链接到完整 checkout 中的 Skill 目录。
   若客户端安装器只复制 Skill 文件夹，还须保留完整 checkout，并确保 Agent 能定位其中的
   `docs/reference/event-schema.md`、运行脚本及 CLI。不要只安装单个 SKILL.md。
5. 验证 Skill 及其引用文档可读取，CLI 可运行，客户端的当前会话身份和历史读取入口实际可用。
   通过[人工构造示例](manual-workflow.md#人工构造示例)验证本地报告链路，不把它当作真实会话读取已验证。
6. 告知用户安装结果；如客户端需要重新加载或下一轮才发现 Skill，按该客户端的实际机制说明。
   确实缺少权限或环境能力时指出具体问题，不声称安装成功。

不要覆盖用户已有的同名 Skill、修改全局环境或自动安装采集 hook。已有安装先核对来源与状态。
有权读取的当前会话不能靠安装动作凭空获得，相关读取规则见[客户端适配](clients.md)。

## 手动安装

当前实现需要 Python 3.9+ 和 pip，无第三方运行时依赖。分析由调用 Skill 的 Agent 完成，
工具负责整理证据、校验引用和合成报告，无需另配模型 API Key。

macOS/Linux：

```bash
git clone https://github.com/MolMind/SteerTrace.git
cd SteerTrace
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
steertrace --version
```

Windows PowerShell：

```powershell
git clone https://github.com/MolMind/SteerTrace.git
cd SteerTrace
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\steertrace.exe --version
```

Agent 可直接使用环境内命令的绝对路径，无需依赖当前 shell 的激活状态。
macOS/Linux 源码运行也可使用 `PYTHONPATH=src python3 -m steertrace`。

安装 Python 工具和注册 Skill 是两个步骤。CLI 安装成功不代表客户端已经发现 Skill，
也不代表能够读取当前会话。客户端详情见[适配指南](clients.md)。

## macOS 与 Windows 安装验证

GitHub Actions 分别在 macOS、Windows 上执行 `python scripts/check_install.py`：
创建隔离环境、从仓库安装包、检查 CLI 和内嵌资源、复制 Skill 并验证配套文档、
在带空格和中文的路径中跑通人工构造报告。该检查不修改真实客户端配置，不依赖符号链接。

这验证操作系统层面的安装和本地运行链路；具体客户端的 Skill 发现与当前会话权限，
仍由安装 Agent 按客户端实际机制核对。完整 checkout 需保留，不能仅复制 Skill 后删除仓库。
