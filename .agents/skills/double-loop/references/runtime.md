# 运行协议与辅助脚本

只有总控写状态。子 Agent 报告交接文件，总控顺序保存。状态和依赖图使用 Python 标准库与 graphlib；清理中的 Markdown 引用解析复用成熟的 markdown-it-py，版本固定在 [requirements.txt](../scripts/requirements.txt)。Git/gh 与 OpenWiki 使用现成能力。脚本不运行模型、项目测试、Git 提交、Wiki 写入或 PR 发布。

## 本次配置

主 Agent 创建中文说明的 JSON 配置，字段如下；值由本次动态推荐和宿主探索产生，不从本包复制固定模型：

| 字段 | 内容 |
|---|---|
| `confirmed`、`confirmation` | 用户确认为 true；后者记录确认内容或消息依据 |
| `roles` | `design`、`implementation`、`review`，各含 `model`、`effort`、`context: "fresh"`、`rationale` |
| `stage_roles` | `knowledge`、`delivery` 各选上述一个角色 |
| `capabilities` | `explicit_model`、`explicit_effort`、`fresh_context` 为 true；`models` 为 `{模型ID: [支持强度]}`；`max_children` 为宿主实际并发上限；`evidence` 记录能力来源 |
| `concurrency` | 本次子 Agent 并发上限，不超过宿主上限 |
| `endpoint` | `pr` |
| `initialization.wiki_host`（可选） | 首次接入未完成时的 Wiki Host，含 model / effort / context / rationale；服从实际能力与集中确认 |

先用 `validate-config --input <文件>` 验证，然后 `init --root <目标Git根> --run-id <运行名> --config <文件>`。目标必须有初始提交；缺少时先按项目授权建立 Git 基线。技能包本身不因生成技能自动建仓库或提交。

脚本路径相对本包为 `../scripts/workflow_state.py`，调用时用其实际绝对路径，避免依赖 shell 的当前目录。

清理和测试需安装引用解析依赖。推荐用 uv 在隔离环境运行：uv run --with-requirements <本包scripts/requirements.txt> python <脚本路径> <命令>。也可使用已有项目虚拟环境安装同一依赖；不安装到系统全局 Python。其余命令可直接用 Python 运行。

## 目录与状态

`.workflow/runs/<run-id>/` 保存 `config.json`、`state.json`、需求摘要、规格、`tasks/`、交接与 `scratch/`。既有项目文档规则优先；有长期价值的资料迁入项目持久目录后更新指针。暂存状态不应默认加入 Git，采用精确暂存或项目已授权的 ignore 规则。首次 dl-init 只增补自己的精确 ignore 区块，正常研发不扩大用户规则。

项目接入的 `.workflow/project.json` 与 `.workflow/onboarding/` 属于 dl-init，不用 run-id。遇到缺依赖、Wiki reload 或 Git 基线不足，先恢复接入再恢复任务；Wiki 自己的队列仍由引擎接续。

任务字段是 `id`、`blocked_by`、`status`；状态为 `pending`、`running`、`reviewing`、`done`、`blocked`。done 表示验收、审查、集成均完成；前置任务未 done 时不得开始后续任务。首次形成任务图及变更后用 checkpoint 校验。

阶段为 `planning`、`design-review`、`executing`、`integrating`、`verifying`、`knowledge`、`delivering`、`cleaning`、`complete`、`blocked`。阶段转换由总控判断证据，脚本校验任务与清理门槛，不替代审查。

`checkpoint --input <更新JSON>` 接收本次需要更新的字段：`phase`、`tasks`、`retained_paths`、`verification`、`knowledge`、`delivery`、`dispatches`、`notes`、`blocker`。保留运行身份、配置指纹与所有权清单，更新版本指纹，原子替换状态。提交、新代码或输入变化后保存检查点；在记录新指纹前先处理旧证据是否失效。

验收记录 `verification` 包含 `status: "passed"` 和非空 `evidence` 路径列表。知识记录 `knowledge` 包含 `status: "complete"` 或 `"noop"` 和非空 `evidence`，保存真实 OpenWiki 完成回执或无需更新依据。交付记录 `delivery` 包含 `status: "pr_created"`、HTTPS `pr_url`、已推送且已核查的 `commit`。这些记录都须由实际工具结果产生，不能为通过脚本自行填写成功。

需要自动清理时将规格、ADR、验收文件、Wiki 回执和完成摘要列入 `retained_paths`。脚本拒绝缺失的保留文件与证据，并检查被清理草稿的稳定替代位置。

## 命令

所有操作运行目录的命令均使用 `--root <Git根> --run-id <运行名>`：

| 命令 | 用途 |
|---|---|
| `preflight --dependencies <文件>` | 只读依赖预检，不要求运行目录 |
| `validate-config --input <文件>` | 只读矩阵校验 |
| `init --config <文件>` | 创建运行；已有同名运行时拒绝覆盖 |
| `checkpoint --input <文件>` | 校验并原子保存阶段、任务与真实结果 |
| `reconfigure --config <文件>` | 确认新的矩阵后保存配置修订，清除旧验收结论并回到验证 |
| `register --path <相对路径> --kind temporary或durable --reason <原因> [--extract-to <稳定路径> ...]` | 文件创建前登记所有权；已存在文件拒绝认领 |
| `seal --path <相对路径> [--extract-to <稳定路径> ...]` | 文件创建后锁定 SHA-256；草稿实质变化后由总控重新核对并封存 |
| `resume` | 只读检查配置、HEAD、工作区与就绪任务，报告证据是否过期 |
| `cleanup` | 只读预览可删与暂缓项 |
| `cleanup --apply` | 写删除日志后执行符合条件的文件清理；可重试 |

自动删除仅限运行 `scratch/` 下提前登记的单个临时文件；临时目录、外部临时文件和 worktree 按交付清理规则单独核验。注册和删除都拒绝符号链接、路径逃逸和受保护位置。

## 交接与恢复

交接包含输入版本、任务/阶段、产物指针、已完成工作、执行命令与结果、未解决问题、下一步；只携必要事实和决策。调度记录区分请求配置与宿主实际回报。

`resume` 比较最后检查点与当前 HEAD 和工作区内容。它包含未提交及未被忽略的新文件，并额外检测 .workflow 下的需求、规格、任务、证据和依赖配置，即使这些文件被 Git 忽略。仅排除每运行的 state.json、单独校验的 config.json、scratch、handoffs 和原子写入临时文件；变化返回 `verification_stale: true`。交接文件统一放在 handoffs 下。被项目 ignore 的其他外部输入或构建产物由总控另外核对。普通 checkpoint 检测到内容变化时，未明确提供新证据的旧验收和知识成功记录会清空。

清理前核对当前 HEAD 等于交付提交，版本指纹与检查点一致，任务均 done，知识与验收记录完整。分支和 PR 不由清理脚本删除。状态原子写入支持中断恢复，但不支持多个状态写入者并发覆盖。

init 在临时目录完成整组记录后原子发布；发布前中断可用同一 run-id 重试。重新配置前先收集或停止旧 Agent，再调用 reconfigure；配置与状态分别原子替换，不一致时用已确认配置重新运行 reconfigure，不重复确认同一矩阵。complete 阶段要求每份登记临时文件都有删除或暂缓结果。
