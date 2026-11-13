# zhiheng

zhiheng 是一套本地优先的软件开发 Harness 技能：`zh` 负责跨阶段协调，另外 16 个 `zh-*` 技能可以按任务单独调用。技能指令以英文编写；项目任务状态使用协议约定的中文值。它把需求、决定、实施、审查、验收和交付连接到项目自己的任务入口，业务代码和测试目录仍遵循项目所用框架的惯例。

本仓库提供 17 个技能、共享规则与模板、`validate`／`snapshot`／`compare` 三个本地工具，以及源码、来源和验证说明。当前版本为 `0.1.0`。可安装的插件包由权威 `skills/` 源码生成；本地审计运行资料不进入插件包。

## 开始使用

需要 Codex 插件功能、Python 3.11+ 和可在 `PATH` 中执行的 Git。工具依赖装在单独的 Python 虚拟环境中，不改变业务项目的依赖。

在本仓库根目录运行：

```sh
python3 tools/build_package.py
python3 tools/check_package.py
codex plugin marketplace add "$PWD"
codex plugin add zhiheng@zhiheng-local
codex plugin list --json
```

本地 marketplace 配置在 `.agents/plugins/marketplace.json`，指向生成的 `dist/zhiheng/`。检查 `plugin list` 中的 `zhiheng@zhiheng-local` 已安装且启用。修改 `skills/` 后，先重建包，再按当前客户端的插件安装流程刷新安装副本；运行时加载的是安装缓存。插件包内含 17 个 `SKILL.md` 及其共享资源。插件布局和本地 marketplace 的约定见 [OpenAI 插件封装说明](https://developers.openai.com/plugins/build/plugins)；本仓库的命令以[实际安装检查](docs/verification.md)为准。

如果只想在某一个项目本地使用技能，可以从本仓库根目录复制完整技能树：

```sh
mkdir -p /absolute/path/to/project/.agents/skills
cp -R skills/. /absolute/path/to/project/.agents/skills/
```

`zh` 目录包含所有阶段共用的规则、模板和工具，复制阶段技能时也必须保留。项目本地复制与插件安装任选一种适合当前工作环境的方式；在项目中核对实际能否发现并读取目标技能。

## 选择入口

在 Codex 请求里显式调用，例如：

```text
$zh 根据 docs/tasks/T-20261114-001/README.md 的有效需求完成开发、审查、验收和本地交付。
$zh-init 接入这个已有项目，找到当前任务需要的规则、运行和验证入口。
$zh-spec 只把已确认的决定整理成可实施规格，先不要写业务代码。
$zh-review 只审查这次变更与已确认规格、项目规范的符合情况。
$zh-resume 核对当前产物和证据，留下可由下一位执行者接续的记录。
```

意图明确时也可以由各入口的 `description` 自动选择。只委托一个阶段，就在该阶段的完成边界返回；例如 `zh-spec` 不会因写完规格而自动开始实施。普通小改动不必建立完整任务图。项目采用本系列后，跨阶段内部引用指向本系列的对应技能。

| 入口 | 主要用途 |
|---|---|
| [`zh`](skills/zh/SKILL.md) | 协调整项任务、选择可执行切片、接收阶段结果并检查总体交付目标 |
| [`zh-init`](skills/zh-init/SKILL.md) | 接入已有项目，或按已定技术栈建立可运行的新项目 |
| [`zh-discuss`](skills/zh-discuss/SKILL.md) | 澄清未决需求、业务规则和重要设计取舍 |
| [`zh-research`](skills/zh-research/SKILL.md) | 对有边界的技术或项目事实做可追溯调查 |
| [`zh-domain`](skills/zh-domain/SKILL.md) | 明确术语、实体关系、生命周期、权限和数据归属 |
| [`zh-arch`](skills/zh-arch/SKILL.md) | 比较模块职责、接口、依赖方向和结构约束 |
| [`zh-prototype`](skills/zh-prototype/SKILL.md) | 用交互原型或隔离实验回答尚未确定的设计问题 |
| [`zh-spec`](skills/zh-spec/SKILL.md) | 将已确认决定整理成带可观察验收条件的规格 |
| [`zh-plan`](skills/zh-plan/SKILL.md) | 将规格拆成有真实依赖和检查入口的实施切片 |
| [`zh-implement`](skills/zh-implement/SKILL.md) | 实施有效规格或已分配切片并返回实际产物与检查结果 |
| [`zh-tdd`](skills/zh-tdd/SKILL.md) | 按真实失败测试、最小实现和复验推进已确认行为 |
| [`zh-debug`](skills/zh-debug/SKILL.md) | 复现、定位和修复缺陷或性能退步 |
| [`zh-review`](skills/zh-review/SKILL.md) | 由独立上下文分别核对 Standards 与 Spec 两轴 |
| [`zh-verify`](skills/zh-verify/SKILL.md) | 对照当前完成条件逐项核对产物、检查和审查证据 |
| [`zh-deliver`](skills/zh-deliver/SKILL.md) | 将已接受工作交付到约定的本地或 Git／平台终点 |
| [`zh-release`](skills/zh-release/SKILL.md) | 按项目已有发布入口执行版本发布、部署或恢复 |
| [`zh-resume`](skills/zh-resume/SKILL.md) | 暂停、交接或恢复时核实有效需求、实际状态和下一步 |

## 项目知识和任务文件

`zh-init` 先盘点已有资料，再建立**当前任务必需**的入口。`AGENTS.md`、`docs/README.md` 用于全局约束和知识导航；领域、架构、ADR、工作流、开发与验证资料有固定定位约定，但根据涉及范围逐步出现。它不会在每次接入时生成整套空目录。项目已有 Wiki、规格或任务系统时，以有效来源为权威，由本地入口引用。

持续跟踪的任务沿用项目已有合适的本地位置；没有约定时使用：

```text
docs/tasks/T-YYYYMMDD-NNN/
├── README.md          # 身份、修订、状态、目标、来源、完成条件与产物入口
├── spec.md            # 需要可执行规格时
├── plan.md            # 需要多个实施切片时
├── verification.md    # 实际验证后
└── checkpoint.md      # 需要暂停或交接时
```

原始运行资料在真正执行时按 `.harness/runs/<task-id>/<run-id>/` 隔离。任务入口保留到这些资料的指针。总体任务身份、修订和状态由 `README.md` 管理，切片状态和依赖由 `plan.md` 管理。状态值为 `待处理`、`执行中`、`待验收`、`已完成`、`阻塞`、`已暂停`、`已取消`、`已取代`；只有核对当前版本的产物、检查和验收依据后才记 `已完成`。模板位于 [`skills/zh/assets/templates/`](skills/zh/assets/templates/)。

例如在业务项目根目录建立一个待处理任务：

```sh
mkdir -p docs/tasks/T-20261114-001
cp /absolute/path/to/installed/zh/assets/templates/task.md docs/tasks/T-20261114-001/README.md
```

随后把模板中的 ID、目标、授权范围、有效来源、完成条件及检查入口改成这个任务的真实内容。`/absolute/path/to/installed/zh` 是实际安装包中的 `skills/zh`；如果采用项目本地复制方式，它就是项目的 `.agents/skills/zh`。

## 本地记录检查工具

创建独立工具环境，并从**实际安装的** `zh` 位置安装依赖：

```sh
python3 -m venv /absolute/path/to/zhiheng-tool-venv
/absolute/path/to/zhiheng-tool-venv/bin/python -m pip install \
  -r /absolute/path/to/installed/zh/scripts/requirements.txt
```

先在业务项目的 `docs/tasks/T-20261114-001/scope.json` 保存如下内容。此例假设项目确有 `src/` 和 `tests/`，请按实际核对范围修改：

```json
{
  "schema_version": 1,
  "root": "../../..",
  "paths": ["src", "tests"],
  "sources": [],
  "checks": [],
  "conditions": {"environment": "local"}
}
```

`root` 相对 scope 文件解析，`paths`、`sources` 及检查证据路径相对该 root；应填写实际存在且属于本次核对范围的文件。`conditions` 是调用者声明，不是工具探测到的环境事实。

然后在业务项目根目录运行；把两个绝对路径替换为本机位置：

```sh
TOOL_PY=/absolute/path/to/zhiheng-tool-venv/bin/python
ZH_TOOL=/absolute/path/to/installed/zh/scripts/harness.py
TASK=docs/tasks/T-20261114-001/README.md

"$TOOL_PY" "$ZH_TOOL" validate --task "$TASK" --format json
"$TOOL_PY" "$ZH_TOOL" snapshot --task "$TASK" \
  --scope docs/tasks/T-20261114-001/scope.json \
  --output docs/tasks/T-20261114-001/manifest.json
"$TOOL_PY" "$ZH_TOOL" compare --task "$TASK" \
  --manifest docs/tasks/T-20261114-001/manifest.json --format json
```

`validate` 检查任务、计划、来源、依赖、链接及验收记录的结构；`snapshot` 按声明范围采集内容指纹和 Git 状态；`compare` 对照清单指出不变、变化、缺失或无法核对的项目。三个命令不执行项目测试，也不代替业务验收；实际检查日志应由项目先运行并写入任务可引用的位置。

内容或任务修订变化后重新采集清单，再比较新的适用范围。使用 `"$TOOL_PY" "$ZH_TOOL" --help` 查看完整字段。退出码 `0` 表示本次核对无问题，`1` 表示结构缺口或差异，`2` 表示输入、依赖或运行错误。

## 开发、验证与反馈

在本仓库根目录，用已安装工具依赖的 Python 执行：

```sh
/absolute/path/to/zhiheng-tool-venv/bin/python tools/run_checks.py
```

该命令重建精简包、检查 17 个入口与资源、运行单元测试并编译脚本。固定上游版本、改造与许可见[来源说明](docs/sources.md)及[三张来源表](docs/upstream-adoption.tsv)。[验证总表](docs/verification.md)区分本地隔离基础检查与尚未进行的业务项目实测；反馈按[反馈入口](docs/feedback.md)记录请求、版本、预期、实际产物和复验结果。

真实项目的迁移、发布和恢复以该项目的配置及知识入口为准。`zh-release` 需要对应环境和授权，不能仅凭本仓库的隔离样例判定业务发布成功。

源码仓库保留 `skills/`、`tools/`、`tests/` 和维护文档。`dist/zhiheng/` 可由构建命令再生成；开发期间的 `docs/evidence/`、`docs/reviews/`、`docs/tasks/` 审计资料在本地另行保留，不作为插件或源码提交内容，其中可能包含宿主缓存及第三方运行副本。
