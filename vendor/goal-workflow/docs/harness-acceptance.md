# Harness 验收追踪与可行性报告

快照日期：2026-10-01 UTC。依据：用户提供的集成计划 v0.5 第 7 节；首版宿主为 Codex CLI；用户指定保留 `$zh` 为主入口，目标平台为 macOS + Linux/WSL（不承诺原生 Windows）。此报告是滚动记录，不能替代最后一次发行物冻结后的复跑。

## 结论

已实现并在隔离夹具中验证若干核心控制、证据、Git、安装及原生 Serena 接缝。当前不能称 P0–P5 完成：真实 Codex 会话尚不能启动，真实 GitHub 平台写入验收被连接权限阻塞，两模式三组代表任务及完整交付/恢复/知识闭环尚未完成。单元通过、模拟平台或结构就绪不等于完整流程可用。

## 证据等级

- **R**：真实本地 Git / 子进程 / 文件系统 / 锁；对象是临时夹具，不是用户项目
- **N**：固定 Serena v1.7.0 原生 CLI；不是 Codex MCP 激活，也不证明语义 onboarding 完成
- **M-host**：真实进程执行，但模型/审查响应或 P0/知识接缝是明确模拟的夹具；具体哪些被模拟以测试文件说明为准
- **M-gh**：模拟 gh/API 响应或适配器回调，没有访问或修改真实 GitHub
- **S**：Schema、静态结构、指纹或解析检查；不证明工具真的执行过
- **B-host / B-gh**：真实宿主/真实平台被明确阻塞
- **U**：尚未执行或没有足够证据

表中测试缩写均指 `tests/harness/test_<文件>.py` 的 `test_<方法>`。测试通过只适用于对应列出的范围；每行的剩余缺口不会因为某个相关单元测试通过而关闭。

## 实际运行记录

- 独立聚合运行：2026-10-01，163 个 unittest 执行通过、0 跳过，47.292 秒，见 [完整日志](evidence/independent-tests-20261001.log)。该运行早于随后候选注册/串行入口等修改；不能作为最终冻结版本的测试证明，发行前须重跑。
- 云端稳定 CLI 实际失败日志：[socket 检查阻塞](evidence/codex-stable-cloud-blocker.log)。可在受支持本机运行 [宿主验收脚本](codex-host-acceptance.md)。

- 独立审查新增：runtime_audit、local_audit、workflow_audit、cli_audit；发现并推动修复了跨 worktree 崩溃接管、短父进程遗留子进程、psutil 回收导致超时退出码丢失、崩溃预算清零、旧 JUnit 假绿、交付对账信任被改证据、GitHub 入口缺锁及未知结果误记 observed 等问题。
- 本地组合失败测试真实建立两条分支，分别通过，再验证组合失败且目标引用不变；无 gh 测试在只含 Git 的 PATH 下运行，配置 GitHub remote 仍走 local。
- 原生 Serena 日志中的“12 tests”包含继承导致的重复：7 个独立方法，只有两个专门原生集成场景（生命周期与复制项目注册），不能写成 12 个独立原生场景。测试明确断言 `host_activated=False`、`onboarding_completed=False`。
- 原生测试需要显式设置 HARNESS_TEST_SERENA 与 HARNESS_TEST_SERENA_PYTHON。未设置时跳过是未运行，不能计通过。
- 实际 Codex：本环境 alpha 0.159.0-alpha.7 和官方 npm 稳定版 0.159.3 均进行了正常 read-only `exec` 探针。版本/help 可用；会话启动在 sandbox helper 处失败：`app-server socket directory must be a user-owned directory with mode 0700`。稳定版使用单独 CODEX_HOME/TMPDIR/XDG_RUNTIME_DIR 仍失败，未绕过安全设置，未复制凭据。没有模型或技能真实执行成功证据。
- GitHub：用户已指定 QZAiXH/zhiheng，并授权沙盒 Issue/分支/PR/合并。实际读取仓库、分支和规则成功；创建两个测试分支及测试 Issue 均返回 403 Resource not accessible by integration，没有成功写入。main 未受保护、rulesets 为空；严格合并保护配置变更不在现有授权内。已请求用户确认正常 gh 登录/凭据保存路径，当前阻塞是连接权限，而非缺少沙盒授权。尚无真实 PR/CI/merge_group/合并/撤销通过证据。

原生清理/重命名/只读补充实测日志：[4 项真实原生测试](evidence/durable-cleanup-20261001.log)。第五项受管项目拒绝无 Controller 的原生调用在后续聚合中验证，不能混入这份较早的四项日志。

已使用运行环境的安装升级/回退实测：[10 技能与原 .venv 保留](evidence/install-used-runtime-20261001.log)。pyvenv.cfg SHA-256 前后相同；这验证文件安装生命周期，不证明 Codex 实际技能调用。

## P0–P6 范围与退出条件

| 阶段 | 当前范围 | 状态/剩余退出条件 |
|---|---|---|
| P0 | 固定源版本、环境与工具探针、CLI 能力与原生知识入口 | 部分；真实 Codex 执行/审查/新会话/停止被阻塞，GitHub 能力待连接写入权限与规则确认；未建立两模式真实任务基线与工期测量 |
| P1 | review helper 退出码、审查失败分支、依赖与文档路由 | 隔离回归已运行；真实 Codex review 与平台依赖仍未验 |
| P2 | 初始化、自包含资产、合同、运行/状态锁、限额、报告定位 | 隔离控制与安装测试；实际 Codex 技能发现/加载、完整 onboarding 和环境声明仍待验 |
| P3 | 共享串行入口、本地候选/检查/审查门禁、GitHub 适配、证据 | 真实 Git + 模拟 host/platform；真实两模式模型任务闭环与交付前知识语义更新仍待验；本地可选 push 已在真实 bare remote 夹具验证 |
| P4 | 崩溃、遗孤、CAS、对账、预算、持久依据 | 本地故障测试已运行；真实宿主取消/平台未知操作和清理后知识可核实的完整场景待验 |
| P5 | 安装测试资产与矩阵；安装后 uv 环境升级/回退回归已真实复跑通过 | 未通过；两模式各小功能/异常修改/依赖组及真实交付恢复、耗时/人工/成本对比未完成；不得宣布首版全量验收通过 |
| P6 | 并行 graph、资源隔离与组合验证 | 后续可选，依赖 P5；本次不启动，不计为已实现 |

## 原计划第 7 节逐项追踪

以下保留源场景和必须观察结果，逐行映射当前证据。全部状态均为“限定范围已验证 / 部分 / 未运行”的细分，不存在一栏泛化“全部通过”。

### 共享和模式验收（24 行）

| ID | 原计划场景 | 原计划必须观察结果 | 实际测试 | 等级 | 证据边界/待办 |
|---|---|---|---|---|---|
| A01 | 测试进程返回非零 | 原始失败被保留；任务不取得 verified 状态，不进入交付成功分支；有服务器合并检查时该检查失败 | `runtime_audit.test_failed_command_preserves_exit_code; review_helper.test_nonzero_tests_preserved; local_audit.test_failed_combination_check_does_not_move_target` | R | 隔离退出码与目标不动已验证；真实服务器检查未验 |
| A02 | 审查修复轮数耗尽仍有 Blocking 问题 | 转为 blocked，保存发现与下一步；不会继续走通过分支 | `workflow_audit.test_blocking_review_never_verifies; workflow_audit.test_exhausted_review_attempts_never_fallthrough` | M-host | 固定审查响应验证门禁；真实 Codex 审查/修复循环未验 |
| A03 | 必需检查被跳过、报告缺失或测试意外执行零条 | 验收不完整；不能凭其他检查为绿而通过 | `local_audit.test_zero_skipped_and_missing_reports_fail; local_audit.test_stale_successful_junit_cannot_certify_new_command; contracts.test_tool_zero_evaluation_blocks` | R+S | 真实命令/XML 与结构门禁已验；业务测试覆盖需逐任务确定 |
| A04 | 验证后源提交、目标基线、规范或检查配置变化 | 旧证据被判过期，重新验证受影响部分及最终组合 | `local_audit.test_target_moves_and_old_evidence_is_rejected; local_audit.test_stale_spec_checks_and_environment_fail; contracts.test_every_binding_component_rejects_drift` | R+S | 本地引用/规范/配置漂移已验；真实 PR head/CI 漂移未验 |
| A05 | GitHub 原生依赖或本地文件依赖尚未完成 | 两种模式分别验证：依赖任务不启动，能说明具体阻塞来源 | `tasks.test_missing_dependency_never_silently_dropped; github.test_native_plus_body_closed_and_cross_repository; contracts.test_valid_nontrivial_dependency_graph` | R+M-gh+S | 本地解析与平台响应模拟已验；真实前后依赖任务串行交付未验 |
| A06 | 依赖在首批分页外、已关闭、不存在或成环 | 分别查询并解释；不漏读、不自动删除约束，closed 不直接等同交付成功 | `github.test_pagination_filters_prs; github.test_cycles_block_even_closed; tasks.test_cycles_and_self_dependencies; tasks.test_missing_dependency_never_silently_dropped` | M-gh+R | 分页/closed/缺失/环在夹具中验证；真实 API 分页未验 |
| A07 | GitHub 创建 PR 成功后进程中断 | 恢复时核对并复用已有 PR，不重复创建 | `github.test_create_recovery_reuses_pr_after_timeout; cli_audit.test_unknown_return_value_blocks_repeat_mutation` | M-gh | 模拟已成功但响应超时与重复阻断；真实创建后中断未验 |
| A08 | 本地提交成功或可选推送成功后进程中断 | 恢复时核对已有提交和引用，不重复生成提交或误报交付 | `local_audit.test_successful_remote_push_with_old_intent_is_reconciled; local_audit.test_nonnumeric_id_candidate_and_authorized_ff_delivery; runtime_audit.test_crash_recovery_preserves_attempt_and_consumed_budget` | R | 真实本地 bare remote 已成功但保留旧 intent 的恢复已验；精确引用对账复用并更新 observed，不重推 |
| A09 | 目标分支已合入但 checkpoint 未更新 | 查询实际 Git/平台状态，正确推进，不重复合入 | `local_audit.test_nonnumeric_id_candidate_and_authorized_ff_delivery; workflow_audit.test_cli_reconcile_cannot_promote_tampered_evidence` | R+M-host | 真实目标对账及伪造证据阻断已验；平台已合并未写 checkpoint 未真实演练 |
| A10 | checkpoint 损坏或发生过期修订号回写 | 不覆盖有效状态；明确报告冲突或进入恢复流程；运行互斥另按下表验收 | `runtime_audit.test_stale_revision_and_attempt_cannot_write; runtime_audit.test_mode_mismatch_and_corruption_preserve_checkpoint` | R | 隔离真实 CAS/坏文件保留已验 |
| A11 | 重新打开会话，只提供交接文件 | 能复原验收条件、决策理由、未决问题和下一步，无需重读整段聊天 | `无真实 Codex 新会话成功记录` | B-host | CLI 会话启动前失败；仅交接文件的新会话恢复未执行 |
| A12 | 提出无证据或与现有规范冲突的知识候选 | 保留候选与冲突，不能直接写成永久事实 | `knowledge.test_temporary_untracked_external_and_traversal_rejected; workflow_audit.test_native_not_ready_cannot_reach_checks_or_review` | R+M-host | 持久依据结构拒绝已验；规范冲突的模型语义判定未验 |
| A13 | Serena 重命名、断链及只读记忆 | 验证原生引用更新及只读项边界；断链报告进入验收失败，不能只看 CLI 退出码 | `durable_cleanup.test_native_rename_propagates_mem_reference; durable_cleanup.test_guarded_native_edit_and_rename_preserve_neighbors; durable_cleanup.test_native_tool_readonly_boundary_is_respected; knowledge.test_native_lifecycle_preservation_and_broken_reference` | N+R | 原生 rename 引用传播、受控 edit/rename、只读拒绝和断链转换均实测；不宣称对直接文件编辑形成权限隔离 |
| A14 | 重复初始化或项目已有维护模板 | 已有模板和记忆不被覆盖；全局与项目模板的有效来源明确 | `init_project.test_user_config_is_preserved_and_needs_review; knowledge.test_native_lifecycle_preservation_and_broken_reference` | R+N | 重复初始化/自定义维护模板保留已验；个人全局模板优先级仍需实际宿主确认 |
| A15 | 新工作区读取已交付知识 | 注册/激活已有项目后读取入库记忆与 ADR，文件保持原样；不依赖原机器的个人全局记忆或缓存 | `durable_cleanup.test_cleanup_then_clean_clone_keeps_native_knowledge_and_sources; knowledge.test_copied_native_project_requires_registration` | N+R | 真实干净 Git clone、全新 Serena home 注册/core/ADR/报告字节与持久引用已验；Codex 新会话语义读取仍被宿主阻塞 |
| A16 | 知识依据已改变但引用仍有效 | 语义复核发现不一致并更新/撤回结论；引用检查通过不能代替该复核 | `knowledge.test_durable_reference_binds_actual_git_commit_and_bytes; workflow_audit.test_mutated_check_log_invalidates_evidence` | R | 字节漂移可检出；有效链接下事实矛盾的语义复核未验 |
| A17 | 技能、依赖锁文件或运行环境变化 | 预检识别差异，旧验证不会被直接沿用 | `capabilities_audit.test_actual_skill_instruction_edit_expires_receipt; capabilities_audit.test_host_script_and_config_changes_expire_receipt; capabilities_audit.test_installed_code_or_dependency_fingerprint_drift_is_rejected; contracts.test_every_binding_component_rejects_drift` | R+S | 真实 SKILL.md/宿主脚本/配置漂移拒绝已验，代码/锁摘要比较通过模拟漂移验证；真实宿主升级全过程待验 |
| A18 | 全新安装、选择性安装、重复初始化、升级回退 | 入口可用、版本可追溯、用户修改保留、恢复旧版本后状态兼容性明确 | `install.test_full_chain_install_copies_only_packages; install.test_selective_harness_is_self_contained; install.test_upgrade_and_rollback_verify_manifest_and_backup; install.test_user_edit_blocks_upgrade_and_rollback` | R | 隔离安装测试已验；真实安装后 uv 可用；已用过的 .venv/lib64 符号链接回归已修复，实际 10 技能升级/回退成功且 pyvenv.cfg 哈希不变。Codex 真实发现/调用、旧 checkpoint 迁移兼容另行验收 |
| A19 | 本地仓库没有 remote、没有 gh、没有 GitHub 凭据 | 完整跑通任务、依赖、实现、验证、交付和恢复，不调用 GitHub API | `local_audit.test_nonnumeric_id_candidate_and_authorized_ff_delivery; local_audit.test_local_github_remote_does_not_require_gh_or_push; workflow_audit.test_simulated_review_allows_verified_but_not_delivery` | R+M-host | 无 remote 的真实 Git 原语、无 gh 的本地路径已验；真实模型全任务链未验 |
| A20 | 本地模式配置了指向 GitHub 的 remote | 仍按 local 执行，不查询 Issue/PR/CI；默认不推送 | `local_audit.test_local_github_remote_does_not_require_gh_or_push; init_project.test_default_local_never_uses_remote_or_gh` | R | PATH 无 gh 且 remote 指向 GitHub 的本地候选/检查/交付已验；不执行 push |
| A21 | GitHub 认证或必需检查查询失败 | 保持失败或阻塞，不自动切换 local，不将未知结果当作通过 | `github.test_native_query_failure_not_fallback; github.test_timeout_and_malformed_fail_closed; github.test_checks_exact_sha_skipped_missing; workflow_audit.test_github_local_checks_alone_never_mark_generic_verified` | M-gh | 模拟认证/查询/未知结果及 GitHub 本地验证不提前标 verified 已验；真实连接读取可用但写入 403；正常 gh 登录路径待确认 |
| A22 | 恢复时配置模式与 checkpoint 不一致 | 拒绝混用进度，明确指出匹配配置或新建运行的路径 | `runtime_audit.test_mode_mismatch_and_corruption_preserve_checkpoint; contracts.test_mode_mismatch_and_no_inference` | R+S | 真实 checkpoint 模式不符拒绝已验 |
| A23 | 本地任务文件被重命名或验收内容改变 | 稳定 ID 仍可定位；要求改变时重建输入并使相关旧证据失效 | `tasks.test_rename_keeps_id_and_reports_but_refreshes_source_path; workflow_audit.test_task_change_invalidates_evidence; reports.test_local_nonnumeric_rename_stable` | R+M-host | 稳定 ID/源路径更新/要求指纹失效已验；完整任务改名后续跑未验 |
| A24 | 本地模式显式启用向指定 remote 推送 | 验证过的提交推送到配置位置，并核对远端引用；不使用托管平台 API | `local_audit.test_explicit_local_push_uses_actual_bare_remote_and_reuses_commit; local_audit.test_successful_remote_push_with_old_intent_is_reconciled` | R | 真实本地 bare Git remote、显式授权、目标引用核对、重复复用与漏写 checkpoint 对账已验；未测试外部网络认证/服务商传输 |

### 六项补充验收（17 行）

| ID | 补充项 | 原计划场景 | 原计划必须观察结果 | 实际测试 | 等级 | 证据边界/待办 |
|---|---|---|---|---|---|---|
| B01 | 补充 1 | 新项目只生成 `memory_maintenance`，记忆列表非空且引用检查无错 | 知识仍未就绪；执行原生 onboarding 指引后，实际写入并读取 `core` 与必要主题才通过 | `knowledge.test_maintenance_only_is_not_core_readiness; knowledge.test_native_lifecycle_preservation_and_broken_reference; workflow_audit.test_missing_native_knowledge_config_refuses_without_mock` | N+R+M-host | 模板不等于就绪、原生写读已验；Codex 执行完整 onboarding 未验 |
| B02 | 补充 1 | 重复 onboarding；已有项目从干净副本注册 | 保留已有知识和规则；不依赖个人全局记忆；缺必要入口或读取失败时明确阻塞 | `knowledge.test_native_lifecycle_preservation_and_broken_reference; knowledge.test_copied_native_project_requires_registration` | N | 模板保留/副本注册已验；必要主题语义充分性待实际宿主 |
| B03 | 补充 1 | 单模块任务与跨模块任务分别启动、续接新会话 | 先提供名称和入口，再按需读正文；单模块任务不默认加载无关主题，跨模块任务可扩展读取；两者的强约束和验收条件完整 | `workflow-contract.md 与 knowledge.md 静态要求；无成功模型读取轨迹` | S+B-host | 单/跨模块按需读取、新会话强约束完整保留未执行 |
| B04 | 补充 2 | 两个入口同时从同仓库或其关联 worktree 启动 | 只有一个进入有副作用执行；另一个不修改 Git、不创建 PR，也不启动第二个执行者 | `runtime_audit.test_live_controller_blocks_related_worktree; init_project.test_common_lock_excludes_another_worktree; cli_audit.test_active_controller_prevents_github_mutation` | R+M-gh | 真实 filelock/关联 worktree 互斥已验；GitHub 写操作仅模拟回调 |
| B05 | 补充 2 | 控制进程退出但子进程仍在写文件；随后尝试恢复 | 先识别并停止旧执行；无法确认停止就 blocked。PID 被复用时不误杀无关进程，不删除锁文件强行接管 | `runtime_audit.test_orphan_record_blocks_recovery_from_related_worktree; runtime_audit.test_reused_pid_identity_is_not_owned; runtime_audit.test_crash_recovery_preserves_attempt_and_consumed_budget` | R | 真实 SIGKILL+遗孤+接管阻断+预算保留已验；不误认 PID 出生身份 |
| B06 | 补充 2 | 已结束的 attempt 迟到回传结果；持锁期间人工修改 Git 引用 | 旧结果不能推进状态；人工改动被交付前复核识别，锁不被误当作全局写保护 | `runtime_audit.test_stale_revision_and_attempt_cannot_write; local_audit.test_target_moves_and_old_evidence_is_rejected; workflow_audit.test_cli_reconcile_is_idempotent_after_actual_delivery` | R+M-host | 迟到回写/外部引用变化/已交付重复对账均验证；重复对账不会把有效 delivered 降为 blocked |
| B07 | 补充 3 | 验证通过后，源不变而目标分支前进；或 PR head 改变 | 原验证不能直接用于交付；GitHub 由严格检查/队列和 head 约束阻止过期交付，本地重建并验证候选 | `local_audit.test_target_moves_and_old_evidence_is_rejected; github.test_checks_detect_race` | R+M-gh | 本地目标前进拒绝已验；平台严格规则和 head 变化仅响应模拟 |
| B08 | 补充 3 | 两条分支各自通过但组合测试失败 | 两种模式都阻止成功交付；本地目标引用保持原值，保存组合失败证据 | `local_audit.test_failed_combination_check_does_not_move_target` | R | 两分支单独命令通过、真实组合命令失败且目标不变已验；GitHub 组合场景未真实执行 |
| B09 | 补充 3 | GitHub 使用合并队列；或 squash/rebase 改变最终 SHA | 核对真实受检对象和必要 `merge_group` 结果；排队不算完成；实际交付可关联已验证内容，否则重新验证或阻塞 | `github.test_merged_queue_requires_merge_group_evidence; github.test_delivered_commit_not_target_reachable_is_blocked; github.test_source_target_delivery_semantics` | M-gh | 队列/重写 SHA/可达性映射为模拟；真实 merge_group、squash/rebase 尚未验 |
| B10 | 补充 3 | 本地交付前目标工作区变脏或不能快进；人工合入内容与候选不符 | 保留用户文件且不强制改引用；实际合入事实单独记录，未核实内容不解锁下游 | `local_audit.test_dirty_target_is_preserved; local_audit.test_target_moves_and_old_evidence_is_rejected; workflow_audit.test_cli_reconcile_cannot_promote_tampered_evidence` | R+M-host | 脏目标保留、引用漂移、假证据阻断已验；真实人工非等价合入仍需场景 |
| B11 | 补充 4 | 本地任务使用非数字 ID、修改标题或重命名任务文件 | note-it、walkthrough、交付报告持续定位同一任务和产物；不请求 Issue 号，不执行 gh，不生成假 PR 链接 | `reports.test_local_nonnumeric_rename_stable; tasks.test_rename_keeps_id_and_reports_but_refreshes_source_path; local_audit.test_local_github_remote_does_not_require_gh_or_push` | R | 非数字 ID/改名报告映射/无 gh 已验 |
| B12 | 补充 4 | 两任务重复 ID/输出路径；GitHub 原有报告继续更新 | 本地预检报告冲突；GitHub 的 `docs/issue#XXXX.html`、原 walkthrough 与 Issue/PR 链接保持兼容 | `reports.test_duplicate_and_path_collision; reports.test_github_legacy; contracts.test_casefold_and_ancestor_report_collisions` | R+S | 本地冲突和 GitHub 原格式报告已验；真实 Issue/PR 链接平台访问不在此测试内 |
| B13 | 补充 5 | 测试或审查不退出、派生子进程；执行中收到取消 | 限额触发或取消后停止派发与交付，保存证据，并在支持的停止路径中确认本次执行及子进程退出 | `runtime_audit.test_timeout_preserves_failure_and_budget; runtime_audit.test_sigint_cancels_owned_execution_and_records_reason; runtime_audit.test_short_parent_cannot_leave_unobserved_same_group_child; review_helper.test_review_timeout_is_failure` | R+M-host | 真实本地超时/SIGINT 取消/子进程清理已验；真实 Codex 取消、跨会话宿主停止未验 |
| B14 | 补充 5 | CI/队列长期 pending；多次恢复或重试 | 到总等待/尝试上限后停止等待并保存原因，恢复不重置已消耗预算；未取得通过证据不交付 | `runtime_audit.test_budget_survives_new_controller; runtime_audit.test_crash_recovery_preserves_attempt_and_consumed_budget; contracts.test_github_wait_limits_required` | R+S | 本地预算/恢复已验；真实 CI/队列长期 pending 的累计等待循环未验 |
| B15 | 补充 5 | PR 创建/合并请求超时，或取消时远端操作已执行 | 查询真实结果再更新状态；不重复操作，不将“本地已停止等待”表述为“远端已取消” | `github.test_create_recovery_reuses_pr_after_timeout; github.test_authorized_merge_pending_then_timeout_reconciled; cli_audit.test_unknown_return_value_blocks_repeat_mutation` | M-gh | 模拟创建/合并超时与未知阻断已验；真实远端撤销/失败后对账未验 |
| B16 | 补充 6 | 候选知识只有临时日志、会消失的提交或即将到期的 CI 链接 | 持久化必要依据并核实后才固化；归档未完成则保留候选，不能靠引用检查无错绕过 | `knowledge.test_temporary_untracked_external_and_traversal_rejected; knowledge.test_durable_reference_binds_actual_git_commit_and_bytes` | R | 临时/未入库/外链-only 拒绝和提交证据已验；已有外部持久归档迁移未演练 |
| B17 | 补充 6 | 清理 `.harness/runs/`、模拟 CI 产物到期，再从干净仓库副本读取 | 记忆、ADR 和必要报告仍可访问并支持结论；本地场景无需 GitHub；不能访问的必需依据有明确复核结果 | `durable_cleanup.test_cleanup_then_clean_clone_keeps_native_knowledge_and_sources` | N+R | 实际删除 runs 与模拟到期 CI 目录，再真实 clone、原生注册/read core、校验 ADR/报告字节；缺失引用明确拒绝。语义结论支持度仍非模型实测 |

## `$zh` 外层集成

已独立审阅 zhiheng-current 的七个 `$zh*` 路由与共享 harness-integration 合同：旧资料保留为来源，增强流程只用一个 checkpoint/锁/知识写入口。统一安装器把七个入口和十个增强组件作为 17 项安装；任一 zh 选择自动补齐完整依赖，不覆盖未知同名技能。

[外层仓库测试日志](evidence/zh-wrapper-tests-20261001.log)：28 项通过（22 原独立流程回归 + 6 统一安装/依赖检查），6.674 秒。该日志使用刷新前 vendor 快照，发行前仍需按最终 vendor 复跑；并不证明真实 Codex 已发现 `$zh`。

## 目标平台边界

Linux/WSL 使用 POSIX 原生锁/进程与本地文件系统；本次实际执行环境是 Linux。macOS 是用户要求支持的平台，必须完成原生文件系统探测/锁/进程/安装及 Codex 实机验收后才能标支持已验证。单纯模拟 sys.platform 或分支覆盖不得写为 macOS 实测。`$zh` 是对外主入口；goal-workflow 上游技能作为内部流程组件，不改变用户已选入口。

## 继续验收需要的条件

1. 可正常运行 Codex CLI 的用户/受支持环境：先用普通 read-only 模式启动测试，确认登录与模型可用；然后在沙盒项目运行技能发现、任务输入、独立审查、停止、续接。无需放宽系统安全策略。
2. 已授权的 GitHub 沙盒 QZAiXH/zhiheng 需要修复正常连接写入权限；无需重新选择仓库。gh 登录/保存须沿已经发出的授权问题继续，不复制凭据。严格分支保护/队列规则的新增或修改须另行授权；现有 main 无保护且 rulesets 为空。
3. 两模式相同基线的三组代表任务、项目实际测试命令与限制；完成真实首次通过率/返工/人工/耗时/成本记录。
4. 发行前冻结文件、保存完整测试日志和版本指纹，再复跑。安装/升级/回退测试在临时目录中成功不证明用户已有安装或历史 checkpoint 已迁移。
5. 尚未有证据的功能应继续实现/测试，或明确记录阻塞并请求所需帮助；不能以手册描述、schema 合格、模拟返回或原生组件探针充当 P5 发布证明。
