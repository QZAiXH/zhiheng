---
name: harness-init
description: Initialize, run, validate, recover, and hand off the goal-workflow harness in Codex CLI using explicit local or GitHub mode, native Serena knowledge, bounded execution, and commit-bound evidence. Use for harness setup or the enhanced goal-workflow pipeline; do not replace unrelated project workflows or assume an unprobed host is ready.
---

# Harness：Codex CLI 串行工作流入口

按用户提供的 v0.5 计划使用增强流程：`prd → 可选 SPEC/设计 → to-issues → loop-it → review-it → walkthrough → ship-it`。本技能携带独立工具环境、薄适配与数据合同；不把安装技能等同于目标项目已完成 P0，也不把模拟测试称作实际宿主或平台验收。

## 首次使用

1. 读取项目适用的规则，确认实际仓库、目标分支、任务范围、交付要求，以及明确的 `local` 或 `github` 模式。不能通过 remote 自动选模式；GitHub 认证失败不降级。
2. 定位本技能的 `assets/project`，用 `uv sync --locked --project <该目录>` 安装固定工具环境。不要把 Python 依赖写入业务项目。用 `uv run --locked --project <该目录> goal-harness --help` 查实际入口。
3. 新项目运行 `goal-harness init --repo <仓库> --mode local|github`；只生成未就绪的配置草稿及指纹，不覆盖现有 `.harness`、规则或记忆。已有状态必须先恢复对账。初始化、执行与知识修改共用实际 Git 公共目录的原生运行锁。
4. 按 [运行合同](references/workflow-contract.md) 和 [配置与数据字段](references/helper-contract.md) 补齐真实命令、有限预算、环境版本、任务和报告映射。任务卡采用上游 Markdown 模板，加稳定 `Task ID` 和 `[AC-*]` 验收 ID。本地 ID 可为非数字；缺依赖/环/重复 ID/路径冲突必须停止。
5. 用原生 Serena v1.7.0 完成注册、onboarding、实际项目阅读与记忆写入。维护模板不代表完成梳理。`core`、相关主题、项目命令和约束必须实际可读；原生引用分析明确无断链才通过，不能只看退出码。见 [知识与决策](references/knowledge.md)。保留已有知识，重要取舍沿用已附来源的 MADR 4.0.0 模板。
6. 在实际 Codex CLI 中演练执行、独立审查、停止/子进程退出和新会话续接；记录原始证据。仅 `--version`/`--help` 或 JSON 声明不足。缺少能力时停靠并指出需要用户完成的具体步骤。

## 命令与边界

命令均通过技能资产内 `goal-harness` 执行。`--bundle` 为配置与任务的执行快照，格式见 helper-contract。不要将命令中的占位符原样运行。

- `record-capabilities --bundle <file> --run <run-id> --tier live|simulation`：直接执行P0探针并记录绑定真实仓库、宿主、技能、依赖、配置与原始日志的能力收据；ready:true不再独自授权执行。live缺必要能力时blocked。simulation仅用于已提交专用标记且无remote的临时fixture，普通交付必须拒绝；fixture需显式--simulation交付
- `knowledge --bundle <file> --run <run-id> <action> --args '<JSON>'`：在同一监督控制器下执行原生 Serena create/register/maintenance/onboarding/read-core/references/readiness/write/edit/rename；现有记忆 edit/rename 要带 expected_sha256 与持久依据。onboarding 返回指引不代表实际梳理完成
- `approve-contract --bundle <file> --task <id> --run <run-id> --authorize`：记录已经批准的验收/配置基线；不允许实现分支自行批准弱化条件
- `preflight --bundle <file>`：校验模式、配置、有限预算、依赖、报告映射；不宣称环境已验证
- `run --bundle <file> --run <run-id> --attempt <attempt-id> [--implement]`：取得全周期运行锁，串行选择可执行任务；可启动配置的实现宿主，默认停在 verified 交接
- `validate --bundle <file> --task <id> --run <run-id> --attempt <id>`：在最新目标基线上形成隔离候选，实际执行检查与独立审查，保存输入、结果、原始日志和实际 Git 绑定；GitHub本地通过仍停validating，必须再经github verify取得当前平台检查才verified
- `reports --bundle <file> --task <id> --run <run-id> --results <observed.json>`：调用上游渲染器生成中文报告；在最终提交及验证前完成，之后生成会使旧验证失效
- `deliver --bundle <file> --task <id> --run <run-id> --target-worktree <path> --authorize`：仅用于已明确授权的本地交付；复核证据、源/目标和清洁工作区后只做 fast-forward
- `reconcile --bundle <file> --task <id> --run <run-id>`：查询实际 Git 状态；物理已合入与证明有效分别记录
- `recover --bundle <file> --run <run-id>`：核实已记录执行已停止；未知身份、仍活跃执行或远端未知结果必须阻塞，不删除旧锁强行接管
- `closeout --bundle <file> --task <id> --run <run-id>`：交付后核对任务交接和已提交的持久依据，再推进 completed
- `push --bundle <file> --task <id> --run <run-id> --authorize`：本地默认关闭；仅显式配置指定 remote/ref 且获授权才执行，超时先查远端实际引用
- `github --bundle <file> --run <run-id> <action> --args '<JSON>'`：GitHub 原生查询/对账/授权交付；参数遵循适配器实际帮助与代码，不猜接口。verify核对实际PR、受检对象和CI；complete-issue依据实际交付回写任务；wait-checks持久保存等待预算；cancel核实远端操作停止。所有有副作用操作先记录意图，结果未知不得重复创建或合并

不要把 `evidence` 的 `eligible_for_independent_verification` 当作 verified。它只做结构、文件哈希和快照一致性检查；真实验证由受控执行、独立审查和实际 Git/平台记录共同产生。

## 执行不变量

- 严格区分 H（源）、T（目标）、C（实际受检组合）和 D（实际交付）。源/目标/任务/规范/检查/预算/环境变化使相应证据失效
- 测试非零、报告缺失、意外跳过、零条测试、未知 CI、未解 Blocking 均不得通过。修复最多两轮且受累计预算限制；耗尽保存 blocked 与下一步
- 所有子进程执行有有限时限与停止宽限。控制器在启动前持久保存本次时间预留与开始次数，正常结束按实际耗时累计；崩溃后按预留/可观测经过时间保守计费，恢复不清零历史
- 运行锁覆盖恢复至退出，所有相关 worktree 共用。权威 `.loop-state.json` 位于主 worktree；公共 Git 目录另存执行身份日志，防止从其他 worktree 绕过恢复
- 停止以 PID 加启动时间等身份核实，确认本次进程及子进程退出后才继续。平台实现面向 macOS 与 Linux/WSL 的原生 POSIX 能力；当前真实测试在 Linux 完成，macOS 只有模拟平台测试、尚未实机验收，WSL 也须在实际发行版完成 P0。详见[平台支持与验证边界](references/platform-support.md)。网络/分布式文件系统、原生 Windows、跨机器和任意脱离会话的守护执行不在支持范围
- 验收合同不能由待验收分支自行削弱；沿项目基线审查配置变更。工具结构化输出不是独立可信来源
- 仅 verified、PR 已开、Issue 已关或分支已推送不解除代码依赖。必须核对成果已交付到下游实际基线
- GitHub 自动合并需要实际查询到严格 required checks/reviews 或合并队列规则；队列要检查 merge_group。`match-head` 不能冻结目标；能力缺失停在可审阅结果
- 本地不依赖 gh、GitHub 账号或 remote；不得生成假 PR/Issue。不要重置/覆盖用户工作区或强推引用
- 知识和说明必须先进入最终候选，再验证；临时日志不能作唯一长期依据。清理前检查引用，必要输出先入持久归档；换干净副本后仍应可读

收据的环境/宿主文件、实际已加载SKILL.md与引用、检查/预算配置、代码/依赖锁或探针原始日志改变后必须重新探测；不能通过复制旧收据或更改ready字段绕过。P0真正的Codex启动、独立审查、同ID恢复和取消演练须保存原始JSONL，模拟宿主协议测试不能替代它们。

## 恢复与交接

恢复前先读实际 Git、任务快照、原始检查/审查记录、checkpoint 与远端操作标识；不要从聊天猜完成状态。保留旧 attempt 和损坏文件，不重复创建已成功的提交、PR 或合并。报告当前状态、阻塞证据和最小下一步。

需要新 Codex 会话时交接任务完整验收、规则、当前引用、证据路径、决策理由、未决问题和剩余预算。只有实际宿主接口验证过的创建/恢复/取消路径才可自动调用；否则清楚地停在人工交接。

## 开发及验收范围

参考 [完整源计划](references/integration-plan-v0.5.md) 的第 3/4/5/7 节追溯阶段、合同、不变量与测试矩阵。该源计划的相对研究链接仅为原始出处，未随附的材料不得声称已读取。P0–P5 必须分别完成 local 和 github 实际试点，不能用一个模式替代另一个。P6 并行仅在首版验收后按用户范围推进，不擅自启动。
