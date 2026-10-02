# 执衡 v0.5 使用指南（Codex CLI）

> `main` 是日常使用与持续开发分支。本文说明安装、配置、执行和失败处理；具体已验证范围与未完成项见[验证状态](VERIFICATION.md)，不以分支名称代替验收证据。

## 先看当前能用到哪一步

日常入口仍是 **`$zh`**。你可以安装全部技能，让 Codex 调查项目、整理知识、展示需求与实施计划。真正启动实现、独立审查、提交及交付前，必须完成当前项目、当前技能版本的能力验证与授权。

本版持续开发和修正。普通功能测试、安装、能力探针与真实业务交付是不同验收层级；当前版本的结果和未完成项请查阅[当前验证状态](VERIFICATION.md)与[历史验收追踪](../vendor/goal-workflow/docs/harness-acceptance.md)的对应提交证据。不要把安装成功或配置可解析当作生产可用证明。WSL 支持声明也须以实际平台验收为准。

## 1. 最短上手流程

### 1.1 准备

需要支持本地 skills 的 Codex CLI、Python 3.11+、Git 和 uv。GitHub 模式另需正常授权的 `gh`；local 模式不需要 GitHub 账号或 remote。Serena 固定使用 v1.7.0，接入细节见第 3 节。

命令示例使用 Bash，适用于 macOS、Linux；WSL 应在其 Linux 本地文件系统内操作。原生 Windows、NFS/SMB、FUSE、WSL 的 drvfs/9p 等不在当前初始化支持范围。工作树和公共 Git 目录都要满足文件系统检查。

### 1.2 从 main 安装

以下在终端运行。克隆会访问 GitHub；安装器只安装文件，不会启动模型、执行技能、创建 PR 或修改业务代码。

```bash
git clone --branch main --single-branch https://github.com/QZAiXH/zhiheng.git
cd zhiheng

# 先预览用户级安装，再执行
python3 tools/install-harness.py --destination "$HOME" --dry-run
python3 tools/install-harness.py --destination "$HOME"
```

如果只想给一个项目启用，**改用**项目级安装，不要同时执行两套示例：

```bash
# 替换为已存在的项目根目录，不是 .agents/skills 目录
python3 tools/install-harness.py --destination /path/to/project --dry-run
python3 tools/install-harness.py --destination /path/to/project
```

- 用户级安装位置：`~/.agents/skills`
- 项目级安装位置：`<项目>/.agents/skills`
- `--destination` 必须是已存在目录；不能传 `.agents/skills` 本身
- `--dry-run` 只展示安装集合与目标，不完成实际冲突、锁或可写性验证；以正式安装结果为准
- 不用旧 `tools/install.py install` 安装本版，它缺少十个增强组件

完整安装是 **17 个组件**：

- 对外七入口：`zh`、`zh-context`、`zh-plan`、`zh-implement`、`zh-debug`、`zh-review`、`zh-finish`
- 增强十组件：`harness-init`、`prd`、`prd-to-spec`、`to-design`、`to-issues`、`loop-it`、`review-it`、`note-it`、`walkthrough`、`ship-it`

打开目标项目中的新 Codex CLI 会话，确认 `$zh` 可发现，并请 Codex 确认实际加载目录。存在同名旧技能时先解决来源冲突，不要假定哪一份自动优先。

### 1.3 第一次发送给 Codex

以下是 **Codex 对话**，不是终端命令：

```text
$zh 接入当前项目。先只读调查，明确实际仓库、当前分支、目标分支和技能加载来源。
本次选 local 模式。请展示初始化草稿、Serena 知识维护范围、检查命令和缺失能力。
先不要启动付费模型演练、实现、提交、合并或推送；需要写入或调用模型时列出具体范围和预算让我确认。
```

先核对调查结果，再明确批准你要执行的初始化、知识维护和有限演练。示例本身不是执行证据；已有一次 Mac 真实 local 闭环通过，但你的项目仍须完成自己的前置检查。

### 1.4 条件齐备后开始第一个任务

```text
$zh 为订单列表增加按状态筛选，local 模式，目标分支 main。
沿用现有组件和接口约定，先展示计划、逐文件修改范围与验收条件。
新项目采用 controller_commit，先让我确认精确 allowed_paths。
请先停在计划和能力检查；真实执行的模型、调用次数与时限由我明确批准。
不推送远端，不自动重试。遇到失败先保留证据并报告。
```

后续确认应明确：实现范围、验收合同、模型及费用约束、是否允许本地提交与合并、是否允许远端操作。已有同一范围的明确批准可以沿用，不能把讨论、状态询问或业务问题的答复当作新授权。

## 2. 安装保护、升级与回退

安装器拒绝覆盖未托管的同名目录、用户修改过的受管文件、未恢复安装事务或活动工作流 checkpoint。遇到拒绝时保留现有内容，检查具体路径和安装清单；不要直接删除目录、改指纹或强行接管。

升级前先停止活动工作流并完成对账，保留本地编辑；确认源码是你要安装的确切版本。在源码目录运行：

```bash
python3 tools/install-harness.py --destination "$HOME" --action upgrade --dry-run
python3 tools/install-harness.py --destination "$HOME" --action upgrade

# 需要恢复上一代技能时
python3 tools/install-harness.py --destination "$HOME" --action rollback
```

项目级安装把 `$HOME` 换成原项目根目录。回退只恢复可验证的上一代技能文件，不撤销代码提交、PR、合并、任务记录或平台操作；没有可用备份时会阻止回退。已有工具 `.venv` 与缓存可能保留，升级/回退后仍须重新 `uv sync --locked` 并验证能力，不能沿用旧收据。

旧七技能版本不自动转换为新安装清单。迁移前阅读[安装说明](../tools/INSTALL.md)与[旧恢复说明](../tools/INSTALL-legacy.md)，保留自定义编辑和旧备份。选择任一 zh 入口会补齐全部 17 组件；`--skills harness-init` 只适合单独初始化/诊断，不能称为完整安装。

## 3. 初始化、知识与执行配置

### 3.1 找到独立工具环境

以下路径以用户级安装为例；项目级安装改成其真实加载路径，不能混用源码和已安装技能：

```bash
HARNESS_PROJECT="$HOME/.agents/skills/harness-init/assets/project"
uv sync --locked --project "$HARNESS_PROJECT"
uv run --locked --project "$HARNESS_PROJECT" goal-harness --help
```

`uv sync` 可能下载依赖，只安装独立工具环境，不应向业务项目加依赖。运行环境按 `uv.lock` 固定 filelock、psutil、jsonschema 和 Markdown。

### 3.2 初始化只是草稿

对已有非 bare Git 项目：

```bash
uv run --locked --project "$HARNESS_PROJECT" goal-harness init --repo /path/to/project --mode local --dry-run
uv run --locked --project "$HARNESS_PROJECT" goal-harness init --repo /path/to/project --mode local
```

GitHub 模式显式改用 `--mode github`；有 remote 不会自动选模式，认证失败也不会自动降级 local。

成功只生成 `.harness/config.json` 与 `.harness/manifest.json`，保持 `ready: false`。它不创建应用脚手架、不执行业务依赖安装、不创建 Git 仓库、不迁移数据库，也不生成完整任务 bundle。已有 `.harness` 或 checkpoint 会保留并要求恢复/审阅。初始化 dry-run 不取得运行锁，因此不证明锁可用。

### 3.3 由 Codex 整理完整 bundle，用户核对关键决定

目前没有“一条命令从草稿生成可立即执行项目”的自动向导。让 `$zh` 按[数据合同](../vendor/goal-workflow/skills/harness-init/references/helper-contract.md)整理实际执行快照，不要复制测试 fixture 或伪造成功 JSON。

至少核对这些内容：

1. 明确的 local/github、仓库身份和绝对根目录、实际 source/target 分支、已入库 SPEC
2. 真实加载的技能目录；经 `$zh` 进入时 `environment.entry_skill` 为 `zh`，`skills_path` 同时包含七入口及增强组件
3. 实际工具/系统版本、依赖锁指纹、宿主实现与独立审查命令；不能猜测 Codex CLI 支持的参数
4. 每项必需检查的参数数组、有限超时、最少执行数；测试必须产生本次新鲜 JUnit XML，不能复用旧报告
5. 显式有限预算：命令、停止宽限、实现、审查、总时间和尝试次数；GitHub 再配置 API、查询、CI 与队列等待预算。配置允许的修复上限不等于用户已批准自动重试
6. 稳定 Task ID、`[AC-*]` 验收 ID、完整依赖、明确任务目录及报告映射；不要把无关 README 放进任务扫描目录
7. 原生 Serena 位置、同一环境 Python、项目专用 Serena home、知识与报告的持久依据
8. `controller_commit` 的逐文件 `allowed_paths`，包括拟修改的测试、知识、报告和 ADR；报告映射本身不授予写权限

bundle 顶层包含 `version: 1`、`config`、`tasks`，新任务的 `checkpoint` 为 `null`；`evidence` 还需要实际 `input/result/current`。初始化的 config 文件**不是**可直接传给 `--bundle` 的完整对象。

### 3.4 Serena：先实际阅读，再维护，再按需读取

首版增强流程以 **Serena v1.7.0 为唯一可写项目记忆源**，保留原有 `.zhiheng`、项目文档和历史记录作为只读来源/导航；不会自动删除或迁移。

由 `$zh-context` 经持锁 Controller 完成实际项目注册、原生 onboarding 指引、代码/文档阅读、core 和相关主题记忆写入。onboarding 返回说明、维护模板存在、记忆列表非空都不代表梳理完成。具体原生安装和配置遵循 [Serena 固定来源与知识合同](../vendor/goal-workflow/skills/harness-init/references/knowledge.md)，本项目的 uv 环境不自动安装完整 Serena。

日常按当前阶段读取 core、相关模块主题、项目命令、约束及必要决策，不把所有历史一次性灌入上下文。适配器提供 `read-core`，没有通用 `read-topic` CLI 子命令；相关主题通过当前宿主实际可用的 Serena 原生读取能力访问，不能杜撰命令。

- 新记忆：要求已核实、能长期读取的依据
- 编辑/重命名已有记忆：先读当前内容，带 `expected_sha256` 前像和持久依据，保留用户编辑；重命名用原生引用传播
- `references` 要解析实际引用分析结果，不能只看退出码；`mem:` 无断链不等于事实正确
- 重要设计取舍使用附带的 MADR 4.0.0 模板，沿用项目 ADR 目录，没有时使用 `docs/decisions`；只保留一份决策正文，记忆和报告链接它
- 知识、说明和报告必须在最终候选验证前完成；验证后再改文件会让旧证据失效

### 3.5 能力收据与模型费用

`preflight` 通过仅表示配置结构一致。真正运行前，当前项目须有绑定仓库、宿主、加载技能、配置、依赖锁及原始日志的 **live 能力收据**，以及已批准的验收合同。不要手改 `ready`、复制旧收据或用 simulation 解锁普通交付。

`record-capabilities --tier live` 会运行探针，不是只读展示命令；开启宿主演练时会调用真实模型。必须先明确批准模型、调用次数和时限。当前 P0 宿主演练按实现固定 low reasoning/default service tier，同一模型贯穿开始、独立审查、续接与可选取消；最多四次启动，不等于四次 API 请求，也不是人民币/美元硬上限。没有实际 usage 时费用未知，失败或超时不能推断为零费用。未批准不得启动，不自动重试或换模型。

P0 先校验显式模型/调用预算参数，再运行可观测的免费原生前置检查；这些必需项失败时跳过真实宿主演练并记录零调用。已派发但缺最终报告时调用数可能未知，不能写成零。该门禁不承诺一切无法 ready 的情况都零费用：model_commit 的模型 Git 权限和最终语义接受证据仍有独立缺口。

新草稿推荐 `controller_commit`：模型在既定 sandbox 内只改允许文件并测试，Controller 审计后提交到明确任务源分支。`allowed_paths` 只能是唯一、精确的仓库相对文件名，不支持目录、通配符、绝对路径、`..`、符号链接或 Git 元数据。

`core.autocrlf` 按 Git 最终生效值判断：有效的 `input`／`true` 仍不支持；项目明确配置的 `false` 可以覆盖上层同名值。被覆盖的来源仍参与指纹与变化检查。这种配置调整必须符合项目的换行约定，不能为了通过检查自动修改全局或项目策略，也不代表其他 Git 执行策略获得了支持。

旧配置省略 `host.commit_mode` 时仍按 `model_commit`；它需要真实模型沙箱内 stage/commit 的证明，现有只读宿主演练不足，当前该 live 能力保持 blocked。不要把切换模式当作绕过安全审查的办法。

Controller 会拒绝不支持的 Git hooks、filters、签名及特殊执行型策略，不会偷偷禁用项目策略。详情见 [Controller 提交边界](../vendor/goal-workflow/skills/harness-init/references/controller-commit.md)。worktree 只是代码/分支隔离，**不是操作系统安全边界**；Controller 权限与模型 sandbox 权限不能互相推断。本文不提供关闭 sandbox 或全局放权命令。

## 4. 从设计到交付：你会看到什么

通常只用 `$zh`，由它按任务路由：

| 你的需要 | 对外入口 | 增强流程及结果 |
| --- | --- | --- |
| 接入/刷新项目知识 | `$zh-context` | harness-init、原生 Serena、缺口与事实 |
| 只制定方案 | `$zh-plan` | PRD → 按需 SPEC/设计与 MADR → 任务卡和 AC |
| 实现或修复 | `$zh-implement` / `$zh-debug` | loop-it 串行推进依赖已满足的任务 |
| 独立验收 | `$zh-review` | 新会话 review-it，Blocking/Warning/Info |
| 收尾 | `$zh-finish` | note-it、walkthrough、ship-it、实际交付对账 |

小且明确的任务可用简短计划；复杂需求先调查和澄清。新页面、布局或关键业务交互应有可操作预览，确认具体版本和范围后再接真实功能，不能用构建成功替代浏览器验收。缺少浏览器或独立新会话能力时明确停靠，不把原对话切换技能当作独立审查。

当 Controller 已派发 task/worktree 时，实现者直接完成本步骤，不再调用 run/probe、启动任务循环或另建工作区，不自行做业务独立审查。controller_commit 下禁止模型 stage/commit/发布；walkthrough/knowledge 以候选说明回传，只有明确允许的文件路径才可写入。完成指定修改和测试后及时返回，不能承诺固定时限必然足够。

测试失败、零条测试、意外 skip、缺报告、未知 CI、未解决 Blocking 都不能通过。每个阶段报告真实状态和剩余缺口；`verified` 不是 `delivered`，交付成功也需完成知识、依据和交接核对才能 `completed`。依赖解除要以成果已进入下游实际基线为准。

### local：本地交付

local 默认不调用 gh、不建 PR、不推远端。实现 → 隔离候选检查与独立审查 → verified 停靠；明确获准后才向干净目标 worktree 做 fast-forward 交付，随后对账和 closeout。目标前进、用户工作区不干净或证据过期时停下，不 reset、覆盖或隐式 stash。

请求示例：

```text
$zh 在已批准任务与当前有效验收证据范围内继续。
验收通过后，允许提交本次修改并本地合并到 main，完成整合核对后清理任务工作区。
不推远端；如证据失效、权限受阻或出现范围外变化，先停下报告。
```

### GitHub：源分支、草稿 PR、CI 与合并

显式 github 模式下按受控步骤推进：本地候选验证 → `push-source` → `create-pr`（默认 draft）→ 有界 `wait-checks` → `verify` → 获本次授权后 `ready` → 获合并授权且实际规则满足后 `merge` → `reconcile` → 获授权后 `complete-issue` → `closeout`。

发布源分支、创建 PR、转为待审、合并、关闭 Issue 是不同操作，不能互相推导授权。不要用普通 `git push` 绕开 Controller；源分支已发布只表示 `source_published`，不代表远端验收或交付。认证失败保留 github 模式和失败证据，不自动改为 local。

### 免费私有仓库：保留 PR/CI，人工合并

不要求先购买分支保护。选择明确的 `github.baseline_policy: "review_only"` 作为人工交付策略，凭据与权限允许时仍可发布源分支、保留 PR 和真实 CI 证据。无规则、套餐不支持、403 无权读取是不同事实；都不能伪装成已证明严格规则，也不自动购买套餐、改可见性或改权限。

自动合并停靠后，向用户交付 PR、当前源/目标 SHA、CI 和独立审查结果及风险。用户明确决定并手动合并后，控制器仍要核对实际交付提交 D、tree 与目标祖先关系；若对象或目标变化，先重验。仅看到 PR/Issue 已关闭不能标记 delivered/completed。

## 5. 终端命令速查（可选）

通常让 `$zh` 维护这些参数。以下均是当前 CLI 支持的形状，不是从空项目可直接跑通的脚本；占位值必须来自已批准的实际 bundle/任务/运行记录。带 `--authorize` 或 JSON `authorized:true` 只是记录已有批准，不能凭参数自行创造授权。

先准备真实值：

```bash
BUNDLE=/absolute/path/to/approved-bundle.json
RUN=run-one
TASK=task-one
ATTEMPT=attempt-one
```

结构检查与帮助：

```bash
uv run --locked --project "$HARNESS_PROJECT" goal-harness preflight --bundle "$BUNDLE"
uv run --locked --project "$HARNESS_PROJECT" goal-harness tasks --bundle "$BUNDLE"
uv run --locked --project "$HARNESS_PROJECT" goal-harness knowledge --help
uv run --locked --project "$HARNESS_PROJECT" goal-harness github --help
```

`tasks` 只适用于 local，读取显式任务目录；GitHub 任务通过 `github tasks/graph` 读取。`preflight` 不是执行批准。

以下会写控制器记录，部分会启动模型、检查、原生工具或修改 Git；**仅在对应门禁和授权齐全后执行**：

```bash
# 记录已批准合同，不替用户作决定
uv run --locked --project "$HARNESS_PROJECT" goal-harness approve-contract --bundle "$BUNDLE" --task "$TASK" --run "$RUN" --authorize

# 启动已配置宿主；不是安装后就可运行的验收捷径
uv run --locked --project "$HARNESS_PROJECT" goal-harness run --bundle "$BUNDLE" --run "$RUN" --attempt "$ATTEMPT" --implement

# 针对已有候选单独验证，会执行检查和独立审查
uv run --locked --project "$HARNESS_PROJECT" goal-harness validate --bundle "$BUNDLE" --task "$TASK" --run "$RUN" --attempt "$ATTEMPT"

# 只有 local 且证据仍有效、已授权时才能交付
uv run --locked --project "$HARNESS_PROJECT" goal-harness deliver --bundle "$BUNDLE" --task "$TASK" --run "$RUN" --target-worktree /path/to/project --authorize
uv run --locked --project "$HARNESS_PROJECT" goal-harness reconcile --bundle "$BUNDLE" --task "$TASK" --run "$RUN"
uv run --locked --project "$HARNESS_PROJECT" goal-harness closeout --bundle "$BUNDLE" --task "$TASK" --run "$RUN"
```

不要连续照抄所有步骤：`run` 会推进其配置流程，`validate` 是对已有候选的独立入口，应按实际状态选择；失败后先诊断，不靠重复命令重置预算或状态。

原生知识读取/引用核查也进入 Controller 并可能产生 Serena 缓存：

```bash
uv run --locked --project "$HARNESS_PROJECT" goal-harness knowledge --bundle "$BUNDLE" --run "$RUN" read-core
uv run --locked --project "$HARNESS_PROJECT" goal-harness knowledge --bundle "$BUNDLE" --run "$RUN" references
```

GitHub 参数中的任务 ID、PR 编号和 remote 必须来自实际任务；示例仅展示发布与核验，不授予外部写入权限：

```bash
uv run --locked --project "$HARNESS_PROJECT" goal-harness github --bundle "$BUNDLE" --run "$RUN" push-source --args '{"task_id":"task-one","remote":"origin","authorized":true}'
uv run --locked --project "$HARNESS_PROJECT" goal-harness github --bundle "$BUNDLE" --run "$RUN" verify --args '{"task_id":"task-one","number":123}'
uv run --locked --project "$HARNESS_PROJECT" goal-harness github --bundle "$BUNDLE" --run "$RUN" reconcile --args '{"task_id":"task-one","number":123}'
```

`reconcile` 会实际查询平台和 Git，并可能 fetch 目标引用，不是纯离线检查。更完整字段以[helper contract](../vendor/goal-workflow/skills/harness-init/references/helper-contract.md)及当前 `--help`/适配器为准。

## 6. 暂停、恢复与故障定位

### 暂停和续接

当前 CLI 没有 `pause` 或通用 `resume` 子命令。向 `$zh` 明确要求暂停，使用当前宿主已验证的停止路径；控制器需要核实所记录进程及子进程退出。终端退出、没输出或对话停止不等于所有本地/远端执行停止。

在新会话中提供任务 ID、bundle 路径、原 run/attempt、当前源/目标引用、checkpoint、原始证据、剩余预算与未决操作。主 worktree 的 `.loop-state.json` 是权威进度，公共 Git 目录保存运行锁与执行身份；不要同时为同一增强任务运行旧 `zh/scripts/task.py` 状态机。

```bash
uv run --locked --project "$HARNESS_PROJECT" goal-harness recover --bundle "$BUNDLE" --run "$RUN"
```

`recover` 核对旧执行已停止，不代表自动续跑或清零费用/尝试次数。若身份未知、进程活跃或远端结果未明，保持 blocked。确认实际状态和预算后再决定下一步；不要删除锁、checkpoint 或日志来“重置”。如果实现超时留下脏工作区，当前没有自动续接该实现的公开入口；换 attempt 也不能绕过已存在源分支。保留现场手动停靠，不能把其中测试 exit 0 当作已形成候选提交或整轮成功。

Controller 提交结果未知时，先取日志中精确 operation ID：

```bash
uv run --locked --project "$HARNESS_PROJECT" goal-harness commit-reconcile --bundle "$BUNDLE" --run "$RUN" --task "$TASK" --operation operation-one
```

该命令查询已发生事实，不重试提交。只有已证明 CAS 成功、精确内容/策略仍匹配且仅 index 同步缺失时，才可能在新鲜收据和明确授权下使用 `commit-recover-index`；不能换 operation ID 重发提交。GitHub ready 不确定时用 `reconcile-ready`，PR/合并/Issue 不确定时按其实际记录对账，不重复创建或发送。

### 常见阻塞

| 现象 | 正确下一步 |
| --- | --- |
| `$zh` 不出现或加载旧内容 | 核对有效 `.agents/skills` 来源与完整 17 组件，打开新会话；不盲目重装覆盖 |
| 安装报同名冲突/修改/事务未完成 | 保存用户编辑、旧清单和备份，按安装说明审查迁移 |
| init 报已有 `.harness` / checkpoint | 保留现场并恢复对账，不重复初始化 |
| uv 下载、启动失败 | 保留错误和版本，区分网络、依赖与宿主权限；不跳过锁文件或关闭 sandbox |
| `/dev/fd`、锁或文件系统拒绝 | 记录真实系统/挂载/权限，保持原生锁，不用软锁或删除锁绕过 |
| preflight 通过但运行 blocked | 检查 live 收据、知识、合同和模式；不要手改 ready |
| 技能、配置、宿主、检查或源/目标变化 | 旧证据可能过期；重新批准必要变化并取得当前证据 |
| 测试非零、skip、零测试、无新报告 | 定位真实原因；不修改断言、删旧报告或豁免检查来变绿 |
| 独立审查/浏览器能力缺失 | 明确“无法验证”，保留候选；不降格为自评 |
| Controller 拒绝 hooks/filters/签名 | 保留项目策略并说明不支持，不自动改全局/仓库配置 |
| Controller 拒绝 `core.autocrlf=input` 等内容转换策略 | 当前受限提交协议不支持这些策略；保留原配置并停止，不手改收据或把禁用转换当作通用修复 |
| GitHub 403、无规则或未知 CI | 区分鉴权/可见性/规则缺口；停止相应步骤，人工交付也需当前证据 |
| 超时或远端结果未知 | 查询原操作实际结果，保留消耗和证据，不自动重试 |

提交问题时提供脱敏后的版本、模式、Task/Run/Attempt/Operation ID、准确错误、受影响阶段与必要日志摘要。不要公开凭据、个人绝对路径或原始敏感实机日志。

## 7. 如何判断真的完成

一次任务至少应分别报告：

1. 实现：改了哪些已批准文件，实际候选是哪一个
2. 验收：检查执行数/失败/skip、独立审查、必要浏览器与 GitHub CI 的真实结果
3. 交付：仅 verified 停靠，还是已证明交付到本地/远端目标；实际 D 是什么
4. 收尾：知识和报告是否可长期读取、Issue/交接是否完成、工作区是否安全清理
5. 缺口：模拟、未测、受阻与未获授权的事项

8ccb840 已有一次 Mac 真实 local 模型闭环通过。完整计划仍缺同基线双模式各三组真实任务等验收；28 项暂停测试与独立安全复核未完成，WSL 未实际执行，真实 GitHub 产品自动整链不能用人工平台测试或模拟替代。不能把代码合入 main、本指南或普通回归通过当作“全部验收完成”，详情见[当前验证状态](VERIFICATION.md)。

### 延伸阅读

- [安装、升级与恢复](../tools/INSTALL.md)
- [统一增强路由](../zh/references/harness-integration.md)
- [工作流合同](../vendor/goal-workflow/skills/harness-init/references/workflow-contract.md)
- [配置与任务数据合同](../vendor/goal-workflow/skills/harness-init/references/helper-contract.md)
- [Serena 与 MADR](../vendor/goal-workflow/skills/harness-init/references/knowledge.md)
- [Controller 提交职责](../vendor/goal-workflow/skills/harness-init/references/controller-commit.md)
- [能力探针的证明边界](../vendor/goal-workflow/skills/harness-init/references/p0-probe.md)
- [当前验收状态](VERIFICATION.md)
- [历史逐项验收记录](../vendor/goal-workflow/docs/harness-acceptance.md)

本文命令按当前源码的实际 parser、分发和参数契约离线核对；没有为编写指南调用真实模型、运行新一轮原生测试或实施任何远端操作。参数可解析不代表当前项目已经满足执行条件。
