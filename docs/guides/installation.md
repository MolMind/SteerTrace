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

## 稳定版本与自动更新

推荐使用管理安装：稳定源码、Python 环境和客户端 Skill 作为同一版本一起切换。
首次需保留一个官方 checkout 用于运行引导脚本，并指定客户端实际支持的 Skill 目录。
以下路径为示例，Agent 必须先核实客户端目录，不能直接照搬。

```bash
python3 scripts/update.py --install-root "$HOME/.local/share/steertrace" --skill-dir /实际客户端技能目录/steer-trace --force-check
```

Windows PowerShell：

```powershell
python scripts/update.py --install-root "$env:LOCALAPPDATA\SteerTrace" --skill-dir "C:\实际客户端技能目录\steer-trace" --force-check
```

初次安装需要已有稳定 GitHub Release 和两个官方附件。仓库只有源码或 Release 尚未发布时，
脚本会说明未安装，不能声称已经自动更新。可用前面的手动方式体验开发源码。
管理安装保留源码和独立环境；安装到客户端的 Skill 内含 `.steertrace-install.json`，
记录当前 Python、源码与安装根目录。Skill 每次调用先使用该记录执行更新，自动查询缓存
24 小时；手动检查可加 `--check-only`，明确更新则加 `--force-check`。
成功后使用输出中的新 Python 和源码路径，并重新读取 Skill。客户端若需要刷新发现，
按其实际机制处理，不假定当前会话会自动重载。

### 迁移已有安装

没有更新入口的旧 Skill 不会自行获得新规则，必须先更新一次。
Agent 先从官方仓库取得包含 `scripts/update.py` 的源码，保留旧安装并核对真实来源。
对没有本地修改、且为复制安装的 Skill，可使用匹配旧文件的 checkout 证明其来源：

```bash
python3 /新版引导仓库/scripts/update.py --install-root /独立安装目录 --skill-dir /实际客户端技能目录/steer-trace --adopt-from /匹配旧技能文件的仓库 --force-check
```

不要求 `--adopt-from` 的源码是最新；它用于核对当前 Skill 副本，而新安装始终来自
最新稳定 Release。链接安装需先按客户端机制显式迁移为副本；脚本不会修改链接指向的源码。
有定制时先保存并迁移定制，不删除旧安装来绕过保护。
成功升级保留旧 Skill 备份及旧环境；只更新本工具的安装，不改全局 Python 或其他技能。
原先的普通 pip 安装或 editable 环境仍保留，但后续使用管理安装返回的新环境。

受支持旧版升级失败可继续；低于已知最低支持版本则暂停新分析。断网时不能证明已经最新，
也不会清除缓存中已知的强制升级要求。若进程意外退出留下 `update.lock`，确认没有升级进程
运行后再移除锁重试。需要回退时，在无升级进程运行的条件下恢复匹配的旧 Skill 备份和安装
记录；不能仅替换 Skill 却继续使用不匹配的新工具环境。
