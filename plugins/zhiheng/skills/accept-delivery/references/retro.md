# Maintainer-requested retrospective

Start when the maintainer requests `retro`. Reopen the original ticket, the specified session or run, the pinned diff, tests and original reports. Read related Episodes in this project when recurrence matters. Use the project's `retro` skill if available, or directly trace the difference between expected work and what happened. Record each proposed change with its evidence, effect, scope and an observable check. Keep undecided proposals on the original ticket.

## Apply adopted project rules

1. Look for the repository's existing engineering standards, contribution guide and mechanical checks. For an adopted judgment about code, add the clause to its engineering standards or create a minimal `CODING_STANDARDS.md`. For an adopted collaboration step, update the contribution guide or create a minimal `CONTRIBUTING.md`. Put mechanically decidable requirements in tests, lint or CI and run the affected check. Use the project's existing equivalent paths and tooling when present.
2. Obtain the actual Git commit containing the adopted text or check under the project's delivery conventions. Verify the clause at that commit with `git show <commit>:<path>`. Until that revision exists, leave the Git change pending on the original ticket.
3. Publish reusable committed clauses under the project's `knowledge/`. Include the applicable code or workflow, versions, Git path and section, containing commit and originating ticket. Use the [write and recovery procedure](../../plan-feature/references/project-knowledge.md#checkpoint-write-and-recover) for each URI. Link verified URIs and their Git sources on the original ticket.
4. Hand off the adopted rule, its target version and check to the next affected ticket. Delivery uses the contribution guide from its target revision. `Standards` cites applicable Git clauses at the reviewed revision. When a knowledge URI is outdated, report the URI and current source to `Act` for correction.

## Improve a skill's method

For an adopted change to a skill, create a separate maintenance ticket linking the originating issue, evidence and effective skill version. State a concrete behavior to improve and a case that would expose a regression. Compare the effective old version and the candidate in fresh sessions with the same task, model, project knowledge, tools and checks. Run the affected regressions and preserve outputs, skill versions and adoption evidence with a rollback reference. Use the project's maintenance and acceptance flow to decide adoption.
