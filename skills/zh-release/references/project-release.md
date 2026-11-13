# Project release knowledge

Read this when entering a release task, designing deployment changes, or writing back verified operational findings. This resource defines what to discover; commands, manifests, and configuration remain authoritative in the business project.

## Locate durable authority

Follow the project's task entry, `docs/README.md`, applicable `AGENTS.md` pointers, and existing release documentation. Use an existing suitable release knowledge location. If none exists, establish the minimum useful `docs/workflows/release.md` within the authorized documentation scope and link it from the project knowledge entry. Return proposed writeback if that scope is unavailable.

Separate three kinds of material:

| Material | Contents and authority |
|---|---|
| Reusable release knowledge | Build/package entry, runtime/orchestration, service scope, actual scripts/workflows/manifests, sequencing, migration entry, verification, and recovery method. Link executable configuration instead of copying its values. |
| Environment differences | Actual target locator, service/environment mapping, configuration and credential acquisition references, current access conditions, and relevant environment-specific sequence differences. |
| This release's task record | Current/candidate versions, adopted knowledge version, full change span, actual data state and migration work, executor/run, results, evidence, remaining actions, and acceptance. |

Credentials remain in their designated secret source. Record how an authorized executor obtains them, never the secret value. Keep per-release logs and version observations in the task rather than converting them into timeless knowledge.

## Discover the actual release mechanism

Determine build/package and runtime/orchestration independently. A Dockerfile establishes a possible packaging path; it does not establish whether the target runs through Compose, Kubernetes, a platform service, or another mechanism. Trace the actual project workflow to the target and its version-observation entry.

For each requested environment/service, locate:

- Candidate identity: accepted source, build inputs, artifact digest/version, and evidence linkage.
- Release entry: actual command or workflow, supported parameters, responsible executor, and run-observation method.
- Target identity: environment, account/context/cluster/namespace/host or equivalent locator, services, and current-version observation method.
- Configuration authority: manifests, configuration sources, secret references, and access prerequisites.
- Migration ownership: pipeline, explicit job, application startup, or another actual entry, with its concurrency/retry behavior.
- Checks: artifact retrieval, running version, service status, required business paths, and data-preservation/result checks.
- Recovery: applicable application/data compatibility, usable restore or forward-fix method, and actual recovery verification.

Only investigate the breadth needed by the task. Unknown targets or missing execution entries become specific dependencies with evidence and the minimum action needed to resolve them.

## Refresh on each release

Re-read the durable entry in a new session and verify the portion relevant to the requested target. Inspect current scripts, workflow/manifests, access conditions, actual deployed identity, and database state. The preceding release record is a clue, not the current baseline. Record the source version or fingerprint used this time.

If multiple plausible environments remain after investigation, prepare the concrete alternatives and effects for the user. Valid prior target selection and authorization remain usable. Ordinary known steps and accepted migration arrangements can proceed from project knowledge without asking the user to restate them.

After success, failure handling, or recovery, write verified reusable discoveries back to their authoritative source within scope and refresh pointers. Keep temporary observations, unresolved hypotheses, and this release's actual run evidence in the task. Preserve superseded knowledge and its replacement relation when necessary to interpret older release records.

## Completion

Knowledge is sufficient when another session can find the requested environment's release entry, parameters, evidence/observation path, migration owner, and recovery conditions without hidden conversation context. This is knowledge readiness; actual publication/deployment still needs the branch-specific checks in [zh-release](../SKILL.md).
