# Bounded P0 capability observations

`harness.p0.probe(config, controller=None)` returns a JSON-serializable observation report. It does not save the report, edit config, set `ready`, approve automation or install tools. Use the pinned project virtual environment: runtime probes depend on the existing filelock/psutil controller.

Required config: explicit `mode`, absolute existing `repository_root`, positive finite `limits.command_seconds`, `limits.stop_grace_seconds`, `limits.task_seconds`. `environment` is fingerprinted as the declared environment. Optional `p0.max_commands` is a positive integer, default 8, bounding this temporary probe sequence; it never increases the workflow's task retry budget. The controller records a reservation before launch, charges actual completed execution time, and conservatively accounts interrupted executions during recovery. Too-small total/command counts block later probes rather than resetting consumption.

Per-capability `status: verified` means only that named, narrowly described probe was actually observed. `blocked` preserves missing or failed probes. The report binds `config_sha256`, `declared_environment_sha256` and `observed_environment_sha256`; observed environment includes the actual OS/Python and successful version outputs. A hash associates bytes, not truth or authorization.

## Default probes and boundaries

- Enumerate the actual configured repository directory, without modifying it
- Find executables via `shutil.which`; observe bounded Git `--version`, Codex `--version`/`--help`, and (only in GitHub mode) gh `--version`
- Initialize a new temporary Git repo and run probes under its actual Controller
- Write/read/delete a synthetic file only in that temporary repo
- Start a synthetic sleeping parent and child; deliberately time it out through the runtime, then independently inspect recorded PID/start-time identities to confirm both are stopped
- Keep automation blocked for real host session start, independent review, native/remote stop, new-session resume, and semantic knowledge/onboarding readiness

Temporary probe artifacts are removed only when local execution is confirmed stopped. If stop remains uncertain, the report identifies the preserved directory for reconciliation. Local process-group proof does not prove Codex-native cancellation or that remote CI/queued operations stopped. Local mode never invokes gh or a GitHub API. GitHub version output does not establish authentication, repository access, merge rules, CI or `merge_group` behavior; those remain separate blocked capabilities.

`p0.executables` may identify the explicitly configured `git`, `codex`, or `gh` command/path. These are version/help probes of that actual executable, not package-origin attestation. The default Codex lookup also considers `host.executable`. Do not substitute a different host while claiming the intended Codex deployment was exercised.

## Optional actual Codex smoke command

To avoid treating arbitrary commands as sandboxed, `p0.smoke_argv` accepts only this exact shape, using the resolved Codex executable path:

```json
["/actual/path/to/codex", "exec", "--sandbox", "read-only", "--json", "--cd", "{worktree}", "Say that this is a P0 smoke check; do not modify files."]
```

`{worktree}` becomes the temporary repo. The final prompt must be nonempty and cannot begin with `-`; no caller-supplied additional flags/config overrides, arbitrary command, shell or sandbox-bypass option is accepted. Explicit `p0.model` and integer `p0.max_model_calls` (1..4) are also required. The controller adds the same model/review-model/low-reasoning/standard-tier options used by host drills and records the single charged invocation in `host_smoke_policy`. The actual CLI still must support these options and complete successfully within configured bounds. A successful command verifies only `host_command_smoke`. It does not synthesize native session IDs or promote independent-review/resume capabilities. No real host smoke session is started by the unit tests.

## Probing the actual project

Pass the actual matching entered `harness.runtime.Controller` to permit project-side effects. The probe checks the controller class, entered state, held run lock and matching root.

- An actual write/read/delete probe runs inside the repository's common Git directory through that controller, retaining a controller execution log. This proves that location is writable, not that every working-tree path is writable
- Native Serena probes use `knowledge.executable`, a dedicated `knowledge.serena_home`, and optional `knowledge.python_executable`, via the existing `SerenaAdapter`
- `p0.register_existing: true` explicitly requests native registration of an existing project under the controller. Without it, registration remains unverified; a project YAML file does not stand in for registration
- Actual pinned version, substantive core read and parsed native reference checks can succeed. Core/reference success still does not certify onboarding, correct knowledge, needed host activation or usable project constraints

Even read-style Serena commands may create cache/config, so the default no-controller probe does not call them. The default is read-only for the user's target project, not a claim that third-party native tools are side-effect free.

The returned `automation_readiness.status` remains `blocked` while required capabilities are unobserved. The optional real start/review/resume path below can establish those specific capabilities; native/remote cancellation and semantic knowledge readiness remain separate requirements before a trusted approval path can enable execution. Caller-supplied `ready: true`, capability JSON, hashes or summaries cannot erase these gaps. Persisting an observation record should use the existing locked state/report path, with no second authoritative readiness store.

Tests: `skills/harness-init/assets/project/.venv/bin/python -m unittest discover -s tests/harness -p 'test_p0.py' -v` from the enhanced repository root. Tests use only temporary fixtures; live Codex sessions, Serena registration and GitHub acceptance are not claimed.

## Optional real start / independent-review / resume drills

Set `p0.run_host_drills: true` and explicitly provide absolute `p0.output_dir`, `p0.model`, and integer `p0.max_model_calls` (1..4) to enable `harness.codex_probe.run_host_drills`. Missing model/budget blocks before host calls or drill artifacts. No model calls occur through this path when the toggle is absent/false. Each start, independent review, exact resume and optional cancellation call explicitly uses the same model, overrides `review_model`, and sets `model_reasoning_effort="low"` and `service_tier="default"`. These invocation-only settings do not edit user configuration. The report and per-call logs record this policy; the caller must authorize the chosen model, for example `gpt-6.1-sol`.

The call budget counts started Codex processes, including failed starts, not underlying API requests, tokens or currency; a process can perform several inference turns. Three calls complete start/review/resume; cancellation needs a fourth. A smaller budget stops further calls with explicit blocked capabilities. `run_host_drills: true` and `smoke_argv` are mutually exclusive; specifying both blocks before any probe execution. Include sufficient `p0.max_commands` and total time for version/IO/stop probes plus these calls (local normally 8 commands; GitHub adds the gh version probe). Per-call timeout remains `limits.command_seconds`; no budgets are silently increased.

The module uses the observed Codex CLI command surface, checked with the installed 0.159.0-alpha.7 help during implementation. It does not assume all versions support it: unsupported flags, unavailable configured models, authentication failure and unexpected event formats block with retained evidence. It does not select a different model, copy credentials, ignore existing rules/config, use an ephemeral session for a resume test, or disable a sandbox.

1. Start an actual `codex exec --sandbox read-only --json --cd <temporary-repo>` session. Require a unique native `thread.started.thread_id` UUID, completed turn and exact random final nonce marker
2. Start a fresh independent read-only `exec` process/session. It must successfully read the actual tiny `fixture.py` and `acceptance.md`; public command-execution events must contain both source contents. Its final JSON must identify the known failing `AC-discount`, actual/expected values and line-2 defect. This is a scoped review-capability drill, not a substitute for a later project's real independent review
3. Invoke `exec` with the parent read-only/root flags followed by `resume --json <exact-returned-id> <prompt>`. The new prompt deliberately omits the nonce. Require the same session UUID and exact recalled original nonce, establishing real session continuity rather than a caller's assertion

Only public JSONL output is parsed; the helper never reads Codex's private session storage. A failed initial session prevents the dependent calls. Review failure can still leave an independently useful resume result. Stop-unknown state prevents further dispatch. There are never more calls than the explicit budget (at most four including cancellation), no retry/model substitution after an auth/model error, and every outcome is explicit.

A unique `host-drills-<id>` directory beneath the requested output directory retains complete raw logs, fixture/spec files and `report.json`. Returned descriptors hash saved bytes; the report itself is hashed externally to avoid a self-hash. Config and declared-environment digests bind the record to its input. If the output directory lies inside the target project, its matching entered Controller is required before creating it. Otherwise it is an explicitly supplied artifact destination. Temporary working files can be removed after confirmed local stop; durable report references point to copied artifacts.

These observations can mark `host_session_start`, `host_independent_review` and `host_session_resume` verified for this actual configured host. Successful process exits do not exercise cancellation. `host_native_stop` remains blocked unless a separate real owned-host cancellation/remote reconciliation exercise establishes it; the synthetic parent/child process drill never fills that gap. Semantic knowledge/onboarding and applicable GitHub capability gaps likewise remain separate. The explicit actual cancellation path below can establish the local CLI stop capability; remote cancellation remains outside its claim. The aggregate is still blocked while any required gap remains; a JSON capability claim or `ready: true` cannot fill one.

`tests/harness/test_codex_probe.py` uses an explicitly simulated executable solely to test protocol parsing, nonce continuity, session separation, failure handling and artifact hashes. Passing those tests is not a live Codex, model, auth or P0 acceptance claim. Run it with the project's pinned virtual environment.


## Optional fourth actual owned-Codex cancellation drill

Set `p0.run_host_cancel_drill: true` together with `p0.run_host_drills: true`, explicit `p0.model`, and `p0.max_model_calls: 4`. Supply positive finite `cancel_startup_seconds`, `cancel_total_seconds` and `cancel_sleep_seconds`. Startup must be shorter than total, total no larger than `limits.command_seconds`, and the synthetic sleep must outlast that total but remain within the P0 task budget. Increase the explicit `p0.max_commands` if needed for the fourth call; the implementation never silently expands it.

The controller creates a uniquely named bounded sleep fixture in its isolated temporary repo. The real configured Codex process must issue a public `command_execution` event containing that marker, and the controller's journal must contain a live PID/start-time identity whose actual command line names that fixture and marker. Only after both observations does the watcher send SIGINT to the verified owned process group. It then requires the same sleep-child identity in the final journal and independently rechecks that every recorded owned process stopped. A trace without a real owned child, a child without a host command trace, missed startup, timeout-only termination or unknown stop remains blocked.

The exact receipt key is `host_native_stop`, with explicit scope `configured_local_cli_and_owned_descendants` and `remote_cancellation_verified: false`. This proves only interruption of the configured local CLI and its owned descendants. It never attests cancellation of remote model services, detached jobs, CI or queued merges. Raw logs and the synthetic cancellation fixture are retained and hashed. Simulated-executable tests cover success and missing-proof failures without claiming live host acceptance.

## Actual read-only GitHub capability path

In GitHub mode, `harness.github_probe.probe_github` runs actual bounded reads through the existing GitHub adapter and entered temporary controller. Require explicit `github.target_branch`, a resolved gh executable, `p0.output_dir`, positive `limits.request_seconds`, and a finite `p0.github_total_seconds` (defaults to the configured CI wait bound). `p0.github_max_requests` defaults to 50 and must be 1–100; the global P0 command/time budgets still apply. GitHub probes commonly need more than the default eight total P0 commands, so provide the measured explicit budget. No automatic retries reset consumption.

`github_authenticated_capabilities` records actual auth status/user identity, repo read/push permissions, paginated task list, a real task/dependency read, PR list/sample reads, immutable-commit check/status queries, and active workflow/source reads. Existing checks can be missing or unsuccessful without pretending they passed: read access and business-check success are separate facts. Empty task lists require a configured `github.probe_issue_number` or an existing pilot issue to exercise task reads. Optional `github.probe_pr_number` chooses an actual PR sample. No API write is executed, and observed permissions do not claim a completed write exercise.

`github_automatic_merge_rules` is a separate capability. In `review_only`, it is not applicable and unavailable server rules do not block readable/manual handoff. In `strict` or `merge_queue`, actual target rules, server-enforced required check names and successful commit-bound results must be observed; configuration booleans such as `rules_verified` are ignored. Queue mode additionally requires an actual successful `merge_group` run for the target and selected active workflow, its required checks, and unchanged workflow source compared with the current target. An unavailable/absent rule, missing check, missing queue event or workflow drift blocks only that automatic-merge capability. The actual merge entry must still re-query the rules and current refs later.

Workflow sources are read from their actual immutable target commit. Use `github.probe_workflow_paths` to explicitly select at most 25 active workflow files when needed; `github.probe_merge_group_sha` optionally narrows the queue observation. API failures, unknown responses and timeouts remain blocked, never equivalent to an empty dependency list or success. Local mode never invokes this path.

Detailed records are returned as `github_probe`, with `logs[*].stdout` and `.stderr` `{path,sha256,bytes}` descriptors and `report_path`/`report_sha256`. These are retained under the explicitly supplied output directory and bound by the capability-receipt code. The simulated gh tests make no live GitHub API requests or platform changes.

### macOS temporary-path aliases

Produced temporary roots are canonicalized at creation. For an explicitly supplied artifact path, the guard only recognizes macOS's first-component `/var` → `/private/var` or `/tmp` → `/private/tmp` alias when running on Darwin and the actual symlink target is verified exactly. After that narrow substitution, every remaining component is still checked for symlinks; unknown alias targets, link chains, inner user-controlled links and `..` remain refused. User artifact paths are never indiscriminately resolved and accepted. Portable tests simulate these system aliases without modifying system paths; native macOS CI remains the platform validation.

### Private repositories and unavailable server rules

Repository visibility and product-plan entitlements do not select the workflow mode. An authorized private repository can still use implementation, explicit source publication, draft PRs, current CI evidence, and a manual merge handoff. `github_authenticated_capabilities` is the required GitHub capability; `github_automatic_merge_rules` is separately observed and is not a global execution prerequisite, including when a requested strict/queue policy is currently unavailable. Use the explicit `review_only` policy for the intended manual handoff workflow.

An empty successful native rule query means no enforcing rule was observed. HTTP 403 or another failed query means rule visibility/access is unknown, not that rules are absent. Both prevent automatic merging unless fresh native enforced-rule evidence is available; neither fabricates an enforcement capability or silently changes the mode. Do not purchase a plan, change repository visibility, or edit protection rules as a fallback without the user's separate authorization. After an authorized manual merge, reconcile the actual delivered commit/tree/target ancestry before Issue completion or downstream code dependencies.

All model invocations explicitly pass `--disable multi_agent` to prevent delegated subagent calls outside the stated invocation budget. This is an invocation-only setting, not a change to personal configuration. The portable host fixture handoff includes its exact working directory, test argv, prior actual test logs and independent review logs so a fresh session can verify the recorded state.
