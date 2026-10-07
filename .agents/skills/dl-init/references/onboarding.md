# 安装、记录与恢复

## 入口与路径

从当前技能路径定位助手；任意工作目录都可用绝对入口调用。先识别 target、本包完整源目录、skill-installer 脚本和现有 OpenWiki SKILL.md 的实际绝对路径，不绑定某台机器的用户目录。

助手使用 Python 3.9 及以上与 Unix 文件锁，适用于本包当前的 macOS / Linux 环境；其他平台需要宿主提供等价锁能力后再执行。

```text
python3 <dl-init>/scripts/project_init.py status --root <target>
python3 <dl-init>/scripts/project_init.py prepare --root <target> --bundle <本包的.agents/skills> --installer <skill-installer/scripts/install-skill-from-github.py> --openwiki-skill <openwiki/SKILL.md>
python3 <dl-init>/scripts/project_init.py instructions --root <target> --input <已编写的中文正文文件>
python3 <dl-init>/scripts/project_init.py wiki --root <target> --input <真实Wiki回执JSON>
python3 <dl-init>/scripts/project_init.py verify --root <target>
```

仅非 Git 项目在 prepare 增加 `--init-git`。已有父仓库时改用它的顶层，不创建嵌套仓库。助手不执行 Git commit。

安装范围为项目 `.agents/skills/`。固定清单由总控与初始化共享，包含阶段入口、可选 research / codebase-design、初始化 setup-matt-pocock-skills 和 retro 所需的 writing-for-agents。许可证与完整固定版本来源保留在 `.agents/vendor/mattpocock-skills/`。

助手复用 skill-installer 的 `--repo mattpocock/skills --ref <固定SHA> --path <整批所缺路径> --dest <本项目staging>`，核对其输出与 checkout 的全目录指纹，然后逐目录原子发布。它不实现 GitHub 下载器。每个已发布目录均可按内容恢复，既有不同内容不覆盖；不自动追随 main 或升级用户已有版本。

本包迁往其他项目时安装全部九个目录，保持兄弟技能和引用路径。上游以原目录内容安装；阶段需要的方法引用仍可从完整 checkout 读取。手动入口的 upstream 方法按 [适配规则](../../double-loop/references/dependencies.md) 使用。

## 状态

| 记录 | 所有者与用途 |
|---|---|
| `.workflow/project.json` | 初始化助手；接入版本、内容指纹、区块所有权、冲突、Wiki 回执指针 |
| `.workflow/dependencies.json` | 项目依赖；兼容原有 checkout 配置，新增项目安装绝对路径与 SHA-256 |
| `.workflow/onboarding/wiki-receipt.json` | 主 Agent 提供的实际 Host 结果；助手校验结构并保存 |
| `.workflow/runs/<run>/` | 后续总控的单次研发；不借用接入记录保存任务矩阵 |
| OpenWiki 原生控制文件 | OpenWiki 引擎；初始化助手不重写 |

`status` 只读，分开返回 `local_ready`、`wiki_ready`、`initialized`、`needs_git_baseline`、`ready_for_worktrees`。`verify` 尚不可执行时返回非零，详细说明问题；其文件校验不独立证明模型实际生效或 MCP 当前在线。

Git 允许无 HEAD，OpenWiki 也支持 unborn 仓库；研发状态助手和 Git worktree 仍需要首个提交。在获得项目提交授权前保持基线待办，不误报可执行。接入、讨论或安装调用本身不授权提交已有业务文件。

## 文件保护与重试

- 读取记录再加锁，锁后重新读取。只有一个初始化写入者；旧执行者仍活跃时协调后再恢复。
- 缺项从 `prepare` 重试；AGENTS 区块从 `instructions` 重试；Wiki 从原生 begin 恢复。已经完成的内容匹配即复用。
- 既有依赖配置、同名技能或托管区块不一致时保留，携实际差异提请决策；此时只补齐互不依赖的工作。
- `.gitignore` 与 `.openwikiignore` 只增补助手自己的标记区块，保留周围规则。精确排除外部技能、vendor、接入临时材料；已跟踪的技能业务源码及技能包自身源目录保持可见。检查用户否定规则覆盖时解决具体冲突。
- 临时安装只在 `.workflow/onboarding/tmp/dl-init-*`。正常退出由 TemporaryDirectory 清理；硬中断遗留目录只有在记录、进程和内容证明本次所有权且不再使用时才逐项清理。未知目录保留，不递归删除 vendor、技能或整个 `.workflow`。

现有 OpenWiki CLI / MCP / skill 优先复用。缺少 CLI 时先探索项目已有依赖、可用包管理器和 upstream 当前安装说明，安装进项目或工具隔离环境；不要默认全局安装或自制替代 Wiki。缺少安装器时使用宿主实际提供的官方 skill-installer；能力仍不可用则记录阻塞。
