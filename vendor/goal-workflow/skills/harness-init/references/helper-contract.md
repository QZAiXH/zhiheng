# Read-only helper contract v1

This is a small project-specific adapter contract, derived from the supplied plan v0.5 §§4, 5 and 7. It is not a knowledge format, workflow controller, or implementation of the complete P0–P5 plan. Serena and MADR retain their native formats.

## Commands and result semantics

The isolated standard-library helper requires Python 3.9+, while the packaged runtime requires Python 3.11+ and its locked tool environment. From the actual installed `harness-init/assets/project` directory, run:

```sh
uv run --locked python -m harness.harness_check scaffold --mode local
uv run --locked python -m harness.harness_check scaffold --mode github
uv run --locked python -m harness.harness_check preflight --bundle /absolute/path/bundle.json
uv run --locked python -m harness.harness_check evidence --bundle /absolute/path/bundle.json
# The source-distribution regression tests live in tests/harness, not in an installed scripts directory.
```

`scaffold` prints a JSON draft to stdout and does not create files. Its required environment values are empty, limits are null, and tasks/checks are empty deliberately: a draft fails preflight until actual P0 observations and requirements are supplied. It does not invent tool versions, budgets, or capabilities. The Python API is `scaffold(mode) -> dict`.

The other commands print `{version, command, ok, decision, errors, notice}`. Exit code 0 means consistency checks succeeded, 1 means blocked/invalid/unreadable, and 2 is argparse usage failure. Each error has `path` and `message`.

- Preflight success: `decision: configuration_consistent`
- Evidence success: `decision: eligible_for_independent_verification`
- Any failure: `decision: blocked`

Neither successful result is `verified`, delivered, completed, or permission to execute. Caller-supplied JSON can be fabricated. Matching report bytes proves only which bytes were supplied. A separate trusted verifier must inspect actual executions, Git, requirements, current environment, independent review and applicable platform records.

The enhanced-project package also provides `harness.contracts.Validator` and `evaluate_bundle(bundle, command="preflight" | "evidence")`. Its evidence gate additionally uses actual `jsonschema==4.26.0` Draft 2020-12 validation against the packaged `schemas/task-input.schema.json` and `schemas/task-result.schema.json`; there are exactly two task schemas, no knowledge schema. Its stdlib sibling is `harness/harness_check.py`. Run the enhanced project's tests with `python -m unittest discover -s tests/harness -p 'test_contracts.py'` from its root, using the locked project environment.

## Bundle envelope

Required top-level fields:

- `version`: integer `1`
- `config`: configuration below
- `tasks`: all relevant task definitions, including every declared dependency
- `checkpoint`: `null` for a new-run preflight, otherwise the checkpoint snapshot below
- `input`, `result`, `current`: required by `evidence`; preflight does not inspect result claims

Extra fields are extension metadata and grant no authority. Unknown limits are still checked for positive finite values. The bundle is a validation envelope, not a third persistent state store.

### Configuration

`config` contains:

- `mode`: explicitly `local` or `github`; never inferred from remotes or authentication
- `repository_id`: nonempty repository identity, such as `example/project`
- `repository_root`: existing absolute repository directory; report paths resolve here, not beside the bundle
- `environment`: nonempty `host`, `model`, `os`, `git`, `runtime`, `skills_revision`, `skills_path`, `dependency_lock_sha256`, `stop_method`, `lock_backend`. Record host/version together (initial target: actual Codex CLI version). The dependency-lock field is a lowercase 64-hex SHA-256. These are observations to verify independently, not proof that stop or lock capabilities work
- `limits`: every limit below, with no implicit defaults
- `checks`: one or more required check definitions

Local and GitHub limits: `command_seconds`, `stop_grace_seconds`, `implementation_seconds`, `review_seconds`, `repair_attempts`, `task_seconds`, `task_attempts`. GitHub also requires `request_seconds`, `query_attempts`, `ci_wait_seconds`, `merge_queue_wait_seconds`. All values must be finite and strictly positive; `*_attempts` must be integers, not booleans. `repair_attempts` is at most 2, preserving the source plan's repair cap. Limits are only validated here, never enforced by a timer or executor.

GitHub mode additionally requires `github: {server, repository, gh_version, baseline_policy}`. The first three are nonempty strings; the policy is `strict`, `merge_queue`, or `review_only`. `review_only` declares a capability gap and cannot authorize merge. Local mode requires no `gh`, remote or credentials; this helper never invokes them in either mode.

Each check is `{id, kind, argv, timeout_seconds}`. `kind` is `test` or `tool`; `argv` is a nonempty array of strings that this helper never runs; `timeout_seconds` is positive and no greater than `command_seconds`. Test checks also require integer `min_executed >= 1`. All configured checks are required; inapplicable checks must be excluded from the independently approved contract before execution. The identifier `review` is reserved.

### Tasks and report paths

A minimal task:

```json
{
  "id": "task-login",
  "dependencies": ["task-api"],
  "acceptance_ids": ["AC-login", "AC-errors"],
  "reports": {
    "note": "docs/task-login.html",
    "walkthrough": "tasks/walkthrough-task-login.md",
    "delivery": "docs/delivery-task-login.md"
  }
}
```

IDs (tasks, runs, attempts, checks and acceptance entries) use `[A-Za-z][A-Za-z0-9._-]{0,127}`. Numeric platform issue numbers are not canonical task IDs; e.g. use `gh-123`. IDs are case-sensitive and must be unique in their scope. File/title changes do not require changing the ID. Dependencies must be explicit unique IDs, all present in `tasks`; `graphlib.TopologicalSorter` rejects self-cycles and longer cycles. Missing external/page-boundary dependencies block rather than disappear. A DAG does not prove dependency completion or delivery into the downstream baseline.

The three report mappings are mandatory and globally unique across tasks. Paths must be normalized portable repository-relative paths, without absolute paths, `..`, `.`, empty components, backslashes, drive/URI colons, control characters, trailing dots/spaces, or Windows device names. NFC-normalized, case-folded paths are compared to avoid common cross-platform collisions; file/directory ancestor collisions also fail. Existing symlink components and non-regular files fail. Mapping paths need not exist yet. Path safety is a read-time check only, not a filesystem sandbox or guarantee against later path replacement.

### Checkpoint snapshot

```json
{
  "mode": "local",
  "repository_id": "example/project",
  "task_id": "task-login",
  "run_id": "run-one",
  "attempt_id": "attempt-one",
  "revision": 7,
  "consumed": {"task_seconds": 12, "attempts_started": 1, "repair_attempts": 0}
}
```

Mode/repository must match the config; task must exist. Revision and consumed amounts are nonnegative, and attempt counts are integers. Consumed totals cannot exceed configured limits. Equality is accepted for auditing an already completed attempt; it does not authorize another dispatch. The helper neither increments state nor resets budgets, acquires locks, stops old processes, reconciles remote operations, or claims atomic updates.

## Input, result and current bindings

All three snapshots contain the same identity fields:

`mode`, `repository_id`, `task_id`, `run_id`, `attempt_id`, `checkpoint_revision`

They must exactly match the checkpoint; `checkpoint_revision` equals checkpoint `revision`. Delayed old attempts and stale revisions therefore fail consistency checks. The helper does not read a live authoritative checkpoint or perform compare-and-swap.

All three contain the same `binding`:

```json
{
  "H": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "T": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "C": "cccccccccccccccccccccccccccccccccccccccc",
  "C_kind": "commit",
  "spec_sha256": "<64 lowercase hex characters>",
  "checks_sha256": "<64 lowercase hex characters>",
  "environment_sha256": "<64 lowercase hex characters>",
  "task_sha256": "<64 lowercase hex characters>"
}
```

The angle-bracket strings above are documentation placeholders and intentionally invalid. `H` is the source commit, `T` the observed target baseline, and `C` the actual tested combination commit/tree. `C_kind` is `commit` or `tree`; Git object IDs have 40 or 64 lowercase hex characters. Different SHA algorithms are accepted but equivalence is never inferred. There is no `D` inference: actual delivery needs a separate verified Git/platform fact.

`spec_sha256` is the digest of the complete applicable specification snapshot, including acceptance and strong constraints. The caller must independently compute and refresh it. Other digests are recalculated by the helper from the supplied current config/task:

- `checks_sha256 = check_fingerprint(config)`: canonical JSON of `{checks: config.checks, limits: config.limits}`, plus `github: config.github` in GitHub mode; changing limits or baseline policy invalidates old evidence too
- `environment_sha256 = fingerprint(config.environment)`
- `task_sha256 = fingerprint(the selected complete task object)`

`fingerprint(value)` is SHA-256 over UTF-8 `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`. Use the supplied function rather than assuming every language serializes numbers identically. The stored JSON's indentation/key order is irrelevant. Task extensions, such as source-content fingerprint and source path, are included, so requirement changes invalidate evidence; a renamed file still resolves the same ID and reports but should produce a refreshed input snapshot.

Input also has `required_acceptance_ids`, exactly the task's acceptance IDs, and `required_check_ids`, exactly the configured check IDs. Both arrays are unique and nonempty. Current is an independently re-observed snapshot supplied by the caller; simply copying input into current is not independent verification.

## Result records

Result has common identity/binding fields plus `stop_reason: "completed"`, `unresolved_items: []`, `checks`, `review`, and `acceptance`. Cancellation, timeout, exhausted-budget and unknown outcomes block eligibility.

Each check record has:

```json
{
  "id": "unit",
  "status": "passed",
  "exit_code": 0,
  "run_id": "run-one",
  "attempt_id": "attempt-one",
  "binding": "<full binding object, not this placeholder>",
  "report": {"path": "reports/unit.txt", "sha256": "<64 lowercase hex characters>"},
  "counts": {"executed": 4, "passed": 4, "failed": 0, "skipped": 0}
}
```

Every configured check must have exactly one result. `status` must be `passed`, and the recorded integer exit code must be 0; booleans and string `"0"` fail. Run, attempt and full binding are checked on every check and review, not just the aggregate. A test requires integer counts, executed at least its positive minimum, failed/skipped zero, and `executed == passed + failed` (skipped is separate). Tool checks instead require integer `counts: {evaluated: n, failed: 0}` with `n > 0`; project adapters must define what their evaluated metric means. Merely preparing a command is not evidence of execution.

Every check/review report must be a unique safe path to an existing nonempty regular file within the repository, and its SHA-256 must match the actual bytes. Reports are read without executing or interpreting their contents. Their text can still be false, unrelated, or attacker-controlled: a hash is not authenticity. Missing, changed, oversized or empty reports fail.

`review` contains `status: "completed"`, `independent: true`, `run_id`, `attempt_id`, full `binding`, `report`, `unresolved_items: []`, and `findings`. Each finding has `{severity: "Blocking" | "Warning" | "Info", summary: nonempty string, resolved: boolean}`. Any unresolved Blocking finding or review unresolved item blocks. Claiming `independent: true` cannot prove independence; check the real reviewer and evidence outside this helper. Resolved findings still require independent evidence of correction in the current review.

Each acceptance result is `{id, status: "passed", evidence_ids: [check IDs and/or "review"]}`. There must be exactly one entry per required acceptance ID, with one or more valid evidence references. Mapping an acceptance requirement to a check ID does not prove that the check actually tests the requirement; that remains semantic review.

## Hard limits and intentionally unsupported claims

- Bundle: UTF-8 JSON, at most 2 MiB, nesting at most 32. Duplicate object keys and non-finite constants fail
- Each report: 1 byte through 8 MiB; no artifact execution
- At most 500 tasks, 100 checks, 500 acceptance IDs/results/findings, 500 dependency IDs, 100 argv elements, and 4096 characters per general string
- No subprocesses, shell/Git commands, network, GitHub/Serena calls, report generation, writes, locks, state transitions, delivery or cancellation in this helper
- No proof of actual versions, host isolation, baseline ancestry/combination, source content, real test execution, reviewer independence, merge policy enforcement, dependency delivery, or long-term archive accessibility
- No semantic proof that rules were preserved or that knowledge is correct; no new knowledge exchange format
- No automatic downgrade from GitHub to local, no fabricated PR, no successful decision based only on self-reported JSON

These checks cover a subset of the plan's fault matrix with synthetic fixtures. They do not constitute P0, live GitHub/local end-to-end acceptance, stopping/lock recovery tests, or release approval. The test fixture builder in `test_harness_check.py` (enhanced copy: `tests/harness/test_contracts.py`) is a complete executable example; all versions, Git objects, reports and reviews there are explicitly synthetic.

## Local Markdown task reader

`harness.tasks.load_tasks(repository_root, task_directories, report_mapping=None)` reads only explicitly configured repository-relative directories and returns canonical tasks sorted by stable ID. The controller passes its `task_directories` setting, for example `[".autoresearch/issues/login", ".autoresearch/issues/admin"]`; there is no fallback that scans all documentation. Every `.md` file inside a selected directory is treated as a task, and an unrelated/malformed README there blocks loading rather than being silently skipped. Choose dedicated feature task directories. Directories must exist and cannot overlap, escape the root, or contain symlink paths.

`parse_task(path, repository_root, report_mapping=None)` reads one task without proving its dependency graph is complete. `TaskParseError.errors` contains `{path,message}` diagnostics. Use `load_tasks` for graph validation. This reader performs no writes, state changes, scheduling or Git/API operations.

The existing upstream `to-issues` local Markdown sections are retained. Add only an explicit `Task ID` section and stable acceptance IDs, and replace local numeric dependency references with stable IDs:

```markdown
# Log in with a valid password

## Task ID
task-login

## Description
Authenticate and preserve the user's session.

## Demo path
Submit a valid password and show the signed-in screen.

## Acceptance Criteria
- [ ] [AC-success] A correct password creates a session.
  The cookie preserves the project's existing security constraints.
- [ ] [AC-errors] Invalid credentials expose no account details.

## Blocked by
task-api, task-storage

## Priority
high

## SPEC Reference
specs/login.md §2
```

Use explicit `None` when unblocked, or comma-separated stable IDs / one `- task-id` per line. Blank, malformed, duplicate, mixed `None`, legacy `#NN`, missing or cyclic dependencies fail. Task IDs never come from filename sequence numbers. Existing `[x]` checkboxes are accepted as task content but never treated as authoritative progress or delivery. Required sections are Task ID, Description, Demo path, Acceptance Criteria and Blocked by; Priority and SPEC Reference remain optional. When present, Priority is high/medium/low.

The canonical object contains `id`, `title`, `description`, `demo_path`, `source_file`, `source_sha256`, full Markdown `content`, `acceptance_criteria: [{id,text}]`, `acceptance_ids`, `dependencies`, `reports`, and optional `priority` / `spec_reference`. Continuation text, constraints and unknown sections survive in full `content`; acceptance continuation lines also remain with their criterion. The source SHA-256 hashes original UTF-8 bytes. The complete task object enters `task_sha256`, so changes to requirements or source location cause a fresh input snapshot.

`report_mapping`, when provided, is keyed by stable task ID with `{note,walkthrough,delivery}` values. Otherwise the default mapping is `docs/task-<id>.html`, `tasks/walkthrough-<id>.md`, `docs/delivery-<id>.md`. Renaming a task file or changing its title leaves that task's stable ID and report mapping intact. The reader rejects unsafe and colliding report paths before returning tasks.

Task files are regular UTF-8 `.md` files, 1 byte through 1 MiB each, with at most 500 files in the selected directories. It is a strict adapter for the documented template, not a general Markdown parser; malformed structure, duplicate required headings, unclosed fences, missing stable IDs and unreadable files must be repaired or explicitly migrated rather than guessed.

## 执行控制器扩展字段（已实现入口）

只读 helper 的结构通过不表示运行就绪。实际 `goal-harness validate/run` 还需要：

- `config.ready`：P0 已经按实际宿主与项目核实后的操作条件；不得通过任意填写 true 替代原始探针记录。当前真实宿主验收缺口见验收矩阵
- `config.host.implementation_argv`、`review_argv`：参数数组，不经 shell 展开。允许 `{worktree}`、`{task_id}`、`{prompt}`、`{input}`、`{output}`；review 另有 `{schema}`。使用已验证的实际 Codex 路径与参数
- Codex review 示例数组：`["codex", "exec", "--sandbox", "read-only", "--json", "--cd", "{worktree}", "--output-schema", "{schema}", "--output-last-message", "{output}", "{prompt}"]`。实际宿主帮助不支持的参数不得照抄；这里只展示当前经过帮助核查的形状
- 实现宿主应使用已验证的隔离工作区写入权限，不能用 bypass sandbox/approval；`run --implement` 建立新的源工作树并让宿主在该分支完成提交
- `config.knowledge`：`executable` 为固定 Serena 1.7.0 原生命令绝对路径；`python_executable` 为同一 Serena 环境的 Python（注册桥接需要）；`serena_home` 为明确的项目隔离 Serena 用户目录。不要复用未知个人全局记忆
- `task.source`、`task.target`：真实 Git 分支；`task.spec`：仓库相对、非符号链接的规范文件；`task.durable_evidence`：已入库的来源文件列表；`task.reports`：唯一 note/walkthrough/delivery 路径映射
- `config.checks[].kind == "test"` 时实际执行入口还需 `junit`：候选工作树内全新的相对 JUnit XML 路径。既有报告不重用、不删除。执行零条、skip、失败、没有新报告均拒绝通过
- `config.task_directories`：本地任务 Markdown 的显式相对目录列表；`goal-harness tasks --bundle ...` 只扫描该范围，不把全部文档当任务
- `config.push` 缺省关闭。启用时显式 `enabled:true`、命名 `remote` 与完整 `ref:refs/heads/...`，执行还需用户已授权的 `--authorize`
- GitHub 最终交付证明需要 `config.github.remote` 对应实际仓库的 Git remote，用于读取 D 与目标引用；只有平台自报 merged 不足以解除依赖

在实现前，用 `approve-contract --bundle ... --task ... --run ... --authorize` 记录已经过用户/项目评审的任务、SPEC、检查及预算内容基线。此命令不能自动给实现分支的新弱化条件背书；改变要求时先获得所需批准，再记录新基线，历史保留。

主状态与一次工具调用的结构不同：`.loop-state.json` 是控制器权威进度，含 schema_version、revision、mode、run_id、attempts、commands_started、spent_seconds、tasks；helper 接收的 checkpoint 是本次任务的只读归一化快照，不是第二份权威进度。

正常命令按实际执行耗时计入累计预算；启动前已持久保存预留和开始次数。中断后无法恢复精确耗时时保守计入预留或可观察经过时间。任务尝试数与命令执行上限分别限制，`config_limits` 根据任务数值派生有界的命令上限，恢复不能自动清零。

## P0能力收据硬门槛

`ready:true`只是期望配置，不能独自开启实际执行。先调用 `record-capabilities`：该入口直接运行组件/宿主探针，不接受调用者提供的成功JSON。收据绑定实际仓库公共目录、模式、配置/检查/预算、宿主可执行文件及脚本、Python/包版本、依赖锁、实际加载的SKILL.md和参考文件，以及留存的原始日志。`environment.skills_path`须是真实加载目录；以$zh为入口时设置`entry_skill:"zh"`并让该目录包含zh与增强依赖。

live收据必须具有真实开始/独立审查/恢复/停止、原生知识读取和项目写入等证据，并提供已授权的、已入库的语义知识审阅记录。缺项保持blocked。配置`p0.run_host_drills:true`启用真实Codex演练，取消演练另显式启用`run_host_cancel_drill`，具体有限参数见p0-probe.md。

simulation收据只允许系统临时目录内、无remote、已提交`.harness-simulation`且内容为`isolated-harness-fixture`的显式fixture。结果持续标记simulation；普通deliver和任何远端写操作不能使用它。隔离fixture交付必须另带`--simulation`，不代表生产交付验收。
