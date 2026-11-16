# Adapting to Host Capabilities

Prefer the current host's skill discovery and invocation entry points when loading skills from this package. When file reading is available, load resources through package-relative paths. Stage skills and shared references are different layers: reading shared material does not also invoke the coordination skill.

## Context isolation contract

This is this package's authoritative context boundary. Executing a full task through `zh` uses an outer coordinator agent/session and a real independent inner execution agent/session, including brief or low-impact implementation. Read-only consultation or assessment, an explicitly single-loop fixed procedure outside full-task coordination, and a separately invoked stage skill keep their own scope; they do not automatically start `zh` or recursive delegation.

The outer coordinator owns planning, dependencies, dispatch, acceptance, and persistent state integration. Only it writes authoritative overall progress and promotes accepted knowledge. Workers act and self-check within assigned writes, then return outputs, evidence, and proposed discoveries; their completion declarations are returns. Related execution stages may remain in one bounded worker assignment. The coordinator checks current requirements and actual artifacts before accepting; it does not implement and accept the same slice in its own context.

Before dispatch, verify the actual host creation interface and its context inheritance behavior. Give the worker only a versioned task contract and relevant source/material entry points. Disable parent-history inheritance with the supported control or use a verified fresh-session mechanism; do not forward the full parent conversation. Inline skill calls, role switches, and history-preserving forks do not provide this boundary. The same model may run independent contexts. Shared workspaces are valid with bounded writes; separate checkouts isolate files, not model history.

Pin task/slice and dispatch identity, requirement revision, source versions or fingerprints, objective and completion criteria, dependencies, workspace and permitted writes, expected artifacts and return path, checks, and failure/retry destination. A brief task can carry this in a compact versioned dispatch instead of a full task tree. Keep concurrent writes disjoint or use isolated checkouts. Pass artifacts, checks, and bounded source pointers across the boundary, retrieving detailed logs only for a scoped verification need.

Independent review uses a clean context separate from implementation, with original effective requirements, standards and actual artifacts, and report-only writes. With `zh-review`, keep Standards and Spec contexts separate as its stage instructions require. Exclude implementation history, intended conclusions, and the producer's verdict; pass prior findings only for a requested recheck. Self-checks retain that label.

Record actual coordinator/worker/reviewer agent and session IDs, parent relationships, actual model/reasoning settings when exposed, host interface/version, parent-context inheritance setting or fresh-session mechanism, and host evidence paths. Mark unexposed settings unknown; an ID or a working directory alone proves no isolation. Each return records the actual adopted versions, output paths and fingerprints, commands/methods, results and raw evidence, unresolved conditions, proposed knowledge, material disposition and next action. Use the [dispatch/return template](../assets/templates/dispatch.md) when creating a record. The coordinator verifies the return and alone registers overall acceptance and checkpoint updates.

If tools, permissions, or runtime conditions cannot provide or verify the boundary, record the attempted mechanism, missing capability, preserved artifacts/checkpoint, recovery condition and next action. Keep affected isolation/review/acceptance requirements unmet. Same-context serial work or role switching cannot substitute. Continue authorized preparation and unaffected work; reuse existing authorization rather than adding confirmation steps.

Dispatch at bounded assignment boundaries. Workers use tools and stage methods inside that assignment without starting another full-task coordinator or dispatching every microstep. Return a split or review need to the outer coordinator for further assignment; this bounds delegation depth.

## Runtime coordination

Use the actual interfaces provided by the current tools for notification, waiting, cancellation, shell termination, and status queries, and verify their effects separately. Before every next affected action, verify that the executor has actually adopted the current requirement and source versions, even when notification receipt was acknowledged. Recheck the basis before accepting a return. On pause, stop further dispatches and inspect in-flight external effects. For each host experiment, record the interface, time, isolation scope, and observed results.
