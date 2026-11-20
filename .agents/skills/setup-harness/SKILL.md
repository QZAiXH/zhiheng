---
name: setup-harness
description: "Configure or refresh a repository for dual-loop development with its tracker, checks, project knowledge and model routing. Answer explanations of existing setup directly."
---

# Set up the development harness

Start at the target repository. Set up an effective project entry that lets a new session locate the original ticket from a development request and resume from that ticket and its target revision.

## 1. Inspect the project

- Inspect the Git root, remotes, registered worktrees, effective instructions and existing `docs/agents/`. Locate the actual `AGENTS.md` or `CLAUDE.md` used by the intended client. Follow imports, symlinks and scoped overrides. Two names may resolve to one file. If both are independent and their intended scope is unclear, ask which client or entry to configure. If neither exists, ask which to create.
- Read the current tracker guide, `.scratch/` conventions, domain glossary or map (including legacy `CONTEXT*.md`), relevant ADRs and engineering standards such as `CODING_STANDARDS.md`, `CONTRIBUTING.md` or their project equivalents. Follow actual domain boundaries in multi-package repositories. Look for test and lint commands in scripts, manifests, build files and CI. Record their working directories and prerequisites.
- Inspect the existing OpenViking binding in the project, including its registered worktrees and project MCP configuration. Identify the stable project ID, account, ordinary user, resource root, endpoint and credential **reference**. Read only the non-secret fields. Two repositories with similar names may belong to different accounts.
- For a project with a knowledge binding, run the [project knowledge checks](openviking.md#verify-the-project-knowledge-binding). For empty results or broken references in an established project, pin the scenario and target release or Git revision from the delivery ticket or confirmed setup scope. Use that scope for read-only recovery and preview even without a delivery ticket.
- Open any existing `docs/agents/model-routing.md` through the effective project entry and recover the approved examples and model pairs.

## 2. Resolve choices and preview

Use prior decisions. On a rerun, verify the existing setup in place, including the routing from chat and the OpenViking credential source. If it already covers the same choices, paths, checks and verified knowledge, finish with zero edits. For an undecided tracker, propose the matching GitHub or GitLab remote, or local Markdown for a local-only repository. Have the user select the actual issue repository, which may differ from the code repository. Give the smallest remaining choices together when practicable.

Default to one glossary. Use an existing map or confirm a multi-context layout only where inspection shows distinct domains. Keep active legacy paths. Include triage only when the **project uses it**. If adopted, confirm the five role mappings against the existing labels. Installation alone does not select triage.

For OpenViking, agree on the project binding. Check an existing ordinary credential first. New accounts require administrative authorization for that project. A repository edit and a server-side change are separate effects. Follow [OpenViking setup and recovery](openviking.md) for new client configuration and migration from an environment variable.

Agree on the [project model routing table](model-routing.md) in this session on first setup. For an assigned setup update, work within the confirmed scope and hand choices that need approval back to the caller. Preview the difficulty examples, three default pairs, any role exceptions, and the complete resolved table with the rest of the setup. On refresh, retain confirmed values and resolve only gaps unless the user requests a change.

Use the language explicitly requested for the project's guidance, otherwise use the language of the user's onboarding request. Apply it to both the entry and the generated guides. Preserve CLI commands, filenames, URIs, configured labels and the local `Status:` and `## Comments` protocol.

Show the actual instruction filename and the proposed block, the contents or diffs for the selected guides and any project MCP settings. Include recovered rule references with their applicable versions and cite the Git and ticket evidence for replacements or retirements. Identify any remote changes being proposed, including account creation, confirmed rule URIs or missing labels. Obtain approval for the preview before editing. Honor an already approved draft.

## 3. Apply the approved setup

Adapt **one** tracker template into `docs/agents/issue-tracker.md`: [GitHub](issue-tracker-github.md), [GitLab](issue-tracker-gitlab.md) or [local Markdown](issue-tracker-local.md). Render the selected host and repository in every remote command. Keep code remotes as found. Write [domain.md](domain.md) to `docs/agents/domain.md` using the actual paths. When triage is adopted, adapt [triage-labels.md](triage-labels.md) and create only approved, missing labels in the selected tracker. Reuse equivalent existing guides when they already serve these roles.

In the effective instructions, maintain a single block between `<!-- harness-memory:begin -->` and `<!-- harness-memory:end -->`. Include the following in project language, replacing descriptions with the project's facts:

- **Planning** opens the selected ticket and parent spec for the goal, target version, slice and acceptance examples. Link the tracker guide and the domain guide.
- **Delivery** reads the applicable Git standards at the target revision. Name their actual paths and the commands to run, with working directory. Point to the bound OpenViking root and project knowledge guide for scoped `find` and original `read`.
- **Handoff** returns the delivered revision or diff, commands and observed results, rule URIs and Git sources, open criteria and any review evidence to the **same ticket**. Name the actual comment or file destination. Outer Check matches this evidence to the delivered version. Outer Act records acceptance, rework or pending verification and updates the ticket status.
- **Routing** sends explicit chat requests to develop or fix behavior, requests to finish a ticket, development-only requests and new acceptance-report requests to `$double-loop` once the confirmed [model routing table](model-routing.md) is installed. Link the actual model routing file and tracker guide from this instruction file. Point chat development requests to the tracker guide for intake and resume all stages from the original ticket. Honor explicit skill invocation. Keep discussion in the conversation, stop development-only requests at the development handoff, and stop report-only requests after the report. Answer explanations and summaries directly.

Render [ticket intake and write recovery](../plan-feature/references/ticket-and-spec.md#resolve-the-original-ticket) in the tracker guide itself. Use the project's actual tracker operations, ticket paths and domain guide link. The effective entry and its generated guides must support intake and recovery even when the setup skill and its references are unavailable.

If an entry already has an `Agent skills` section, integrate matching pointers once and retain its other instructions. Update only the managed block, relevant guide passages and the selected MCP table. Preserve manual notes, symlink targets, other tools and other people's edits. Compare current contents before writing. Identical choices and repository facts should yield a byte-identical rerun. If an existing marker is unmatched or the ownership of a passage is unclear, preview a targeted repair before editing it.

Bind OpenViking as described in the [setup reference](openviking.md). Render the daily-use procedure, including the binding checks, rule recovery and pre-write checkpoint, in the project's language in its guide. A fresh session needs the procedure even when it cannot load this skill. Apply approved reference repairs and run the binding checks against the resulting entry and guide. Confirm each approved server write with an exact readback before presenting its URI as verified. Surface missing test commands, authority or connection as a specific pending item. Continue the approved local setup. Add standards and project knowledge as actual tickets establish a need.

Save the confirmed examples and resolved table to `docs/agents/model-routing.md`. Enable the routing pointer when it opens the complete table. Incomplete choices leave routing setup pending while independently approved setup can proceed.

## 4. Check the handoff

From the effective entry, follow a chat development request without a ticket number to the configured tracker and its original ticket, when one exists. Follow only the generated project links to verify search and reuse, authorized creation, uncertain writes, read-only drafts and the requested stopping point. If the project has no tickets yet, verify the configured tracker location and leave the first handoff for the first ticket. Check a repository-defined test command from its stated working directory. Report which checks actually ran. For a fresh-session trial, give the reader only the ticket identifier and target revision in the configured project. A successful reader can identify the criteria, run the check and cite the applicable clause and its Git revision.

Open the rendered knowledge guide from the effective entry. Report service connectivity, original rule readability and current entry references separately. Verify any repaired links and exact readbacks. From only the generated entry and guides, check both ticket-based recovery and standalone refresh from a confirmed scenario and target. Reopen the approved write checkpoint at its actual tracker or decision record. Record any unresolved reference or criterion and its resume action.

Open the model routing file from the effective entry. Verify all difficulty examples and exact pairs against the approved preview, including role exceptions. Reuse the same setup without changing bytes. For a ticket-only trial, check that a fresh session reaches the table and dispatches the relevant stage with its recorded pair.

The [upstream source record](upstream/ORIGIN.md) identifies the pinned Matt Pocock skill, its original files and license.
