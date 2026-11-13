---
name: zh-init
description: Onboard an existing project for a concrete development task, or establish a runnable new project from an agreed stack and suitable scaffold. Use for project discovery, minimal knowledge entrypoints, or greenfield setup; stop at the commissioned setup boundary.
---

# Project Onboarding and Creation

Make the project ready for the current task. An existing project needs enough verified context to proceed; a new project needs a runnable foundation. Standalone invocation ends at the requested onboarding or creation result. Build a first feature only when it is included in the assignment.

## Establish the assignment

Read the requested project location, goal, allowed writes, existing decisions, and delivery target. Determine whether this is an existing project, an empty project, or an interrupted setup. Inspect actual files before choosing a branch. Preserve unrelated user work.

When maintaining persistent task records or returning a delegated result, read [task-protocol](../zh/references/task-protocol.md). Read [knowledge](../zh/references/knowledge.md) when locating, creating, or updating project entrypoints. Access these resources directly; this does not start the `zh` coordinator.

## Existing project

1. Follow applicable project instructions and existing knowledge navigation. Locate the affected modules, domain terminology, accepted decisions, framework-native structure, dependency configuration, and actual run and check entrypoints.
2. Investigate only what the task needs. Distinguish verified implementation facts, accepted target behavior, and unknown history. Resolve gaps affecting business meaning, permissions, data ownership, or correctness before the affected implementation.
3. Identify data impact proactively. Inspect relevant models, persistence paths, database type, migration tool and history, and retention requirements. Read [data-change](../zh/references/data-change.md) for this investigation, including a supported conclusion when no migration is needed.
4. If the task concerns release or environment preparation, locate existing build, runtime, deployment, migration, verification, and recovery documentation. Verify the relevant configuration and environment differences; add a minimal release knowledge pointer when the existing navigation is insufficient.
5. In the authorized documentation scope, repair only the entrypoints needed for this task. Reuse existing authoritative documents rather than reproducing their contents. Use `AGENTS.md` and `docs/README.md` for navigation when no suitable convention exists; create further documents only when their content is needed.

## New project

1. Establish the intended first runnable outcome, deployment constraints, and any already accepted stack. If the main stack or an important module boundary remains undecided, prepare a concrete recommendation and tradeoffs for the user before committing to that choice. Reuse valid prior approval.
2. Prefer a suitable maintained scaffold or template. Check its current maintenance, license, compatibility, and relevant security constraints against authoritative sources. Choose one stack for this project rather than building a template library.
3. Generate the smallest useful foundation in the assigned location. Follow the framework's native source, test, and build layout; use the project's package and configuration conventions. Record the scaffold origin and adopted version. Inspect generated files and remove only scaffolding that is unnecessary for the agreed outcome.
4. Establish the minimal project knowledge entrypoints and actual development and verification instructions. Link configuration as the authority for commands and dependencies. Install or load generic skills through the project's chosen mechanism; add `.agents/skills/README.md` only when a skills navigation entry is needed.
5. Start the project and run its relevant baseline checks. If a first feature is commissioned, carry its accepted requirements into `zh-spec` / `zh-plan` and implement through `zh-implement`; a new page or major interaction requires an accepted interactive prototype before business UI implementation.

## Check and return

Read [verification](../zh/references/verification.md) when recording runnable results and evidence. Return the verified run and check entrypoints, knowledge locations, data impact findings, actual changes, remaining conditions, and the next executable step. A setup report must distinguish a command that was found from one that actually succeeded.

Onboarding is complete when the current task has reachable constraints, implementation and check entrypoints, and explicit consequential gaps. New-project creation additionally requires the agreed foundation to run and pass its required checks; a commissioned first feature must meet its own acceptance conditions.

For missing tools or environment prerequisites, investigate and repair within existing authorization or use an equivalent path that preserves the original conditions. Continue unaffected work. When a required result remains unavailable, return its evidence and specific unblock condition. Read [change-recovery](../zh/references/change-recovery.md) when setup is interrupted or its requirements change, and [host](../zh/references/host.md) only when loading or delegating through host-specific capabilities.

This entry is independently authored from the project's accepted onboarding and greenfield requirements.
