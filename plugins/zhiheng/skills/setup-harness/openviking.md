# OpenViking project access

## Bind the ordinary identity

Record the approved service base URL, stable project ID, dedicated account, ordinary user, project resource root and private credential file path in `docs/agents/project-knowledge.md` or its existing equivalent. Read the settings in registered worktrees before proposing a new ID. Match an existing account to the project's recorded binding or the administrator's provisioning record before resuming setup. A resource root scopes searches inside an account. Assign a separate account to every distinct project.

Reuse the project's private key file. For a new client file, use a path such as `~/.config/openviking/projects/<project-id>.key` outside Git with mode `0600`. Verify the identity returned by the service's authenticated `/health`. The helper uses Python 3.9+ on macOS or Linux. Run the helper from this skill's directory and substitute the agreed values.

```sh
python3 -B scripts/project_access.py verify --url "$ov_base" --account "$ov_account" \
  --user "$ov_user" --key-file "$ov_private_key_file"
```

When migrating a key available only through a legacy environment variable, save that same ordinary key to the private file and verify it there before switching the MCP configuration. Check the returned account, user and `user` role before using project data. If the service or credential is unavailable, record the check as pending and finish the other approved repository edits. Resume from the same binding.

## Create or resume an account

Use the administrator's existing provisioning channel if available. For the documented OpenViking 0.5.5 `api_key` deployment, the bundled helper runs **on the authorized service host**. Its config supplies the local listener and root key. The following command creates or resumes a dedicated account and `role=user` membership and saves only the ordinary key to the private destination. Select an operator-controlled directory outside the repository. For a remote host, run the helper over the approved SSH channel (it also accepts `python3 -` with the script on stdin).

```sh
python3 scripts/project_access.py provision --config /etc/openviking/ov.conf \
  --account "$ov_account" --user "$ov_user" --key-file "$ov_private_key_file"
```

- A verified existing key is reused. An account already created before an interruption is reused and a missing ordinary user is registered.
- If registration succeeded but the key is absent, retrieve the existing credential from its private store. Only when the owner authorizes invalidating the old key, rerun `provision` with `--rotate-lost-key`. A mismatched identity or elevated role needs the correct binding. A timeout calls for a fresh state check at the same account and user.
- Transfer the ordinary key using the project's approved secret store or an authenticated SSH transfer into a private temporary file on the client. Verify it there, then install it as `0600` outside Git. Keep the server's admin configuration on the service host. Reuse the same project credential for its registered worktrees.

## Configure the project client

For a trusted Codex project with a local Streamable HTTP connection, configure `http_headers_helper` to read the private file at startup. Use a project-relative copy of `project_access.py` that supports `mcp-headers`. Reuse the project's existing helper or use `.agents/skills/setup-harness/scripts/project_access.py` for a project-local skill install. If the skill is available only through the marketplace, include a copy of `scripts/project_access.py` at `.codex/openviking-project-access.py` in the setup preview and use that path in the command.

Fill in the service URL, the project-relative helper path and the actual private key path. Merge the table into the project's `.codex/config.toml`, preserving unrelated settings. When migrating, remove the old `bearer_token_env_var` from this table after the same credential verifies from the private file. Check the effective settings for an inherited bearer token or `Authorization` header.

```toml
[mcp_servers.openviking]
url = "<service-base-url>/mcp"
http_headers_helper = 'exec python3 -B "$(git rev-parse --show-toplevel)/<project-relative-helper>" mcp-headers --key-file "$HOME/.config/openviking/projects/<project-id>.key"'
enabled_tools = ["find", "read"]
```

In a fresh Codex client without a project credential environment variable, check that MCP starts and use it for the knowledge checks below. Record the credential file path and normal Codex startup in the generated project guide. Secret values stay in the private file. If the client lacks local HTTP helper support or project configuration is disabled, report the MCP check as pending and use the native HTTP equivalents below with the same ordinary identity. Configure a different client using its supported credential source.

## Verify the project knowledge binding

On both onboarding and refresh, record the outcome of each check separately:

1. **Service connectivity.** Use the ordinary credential and authenticated `/health` to verify the configured endpoint, account, user and ordinary role. If identity or connectivity cannot be verified, record the observed result and mark dependent service reads pending.
2. **Original rule readability.** Read known rule URIs directly. For a known scenario without a URI, use project-scoped `find` and then `read` the exact originals. Record the URIs and applicable target versions that were actually verified. An empty result, an authenticated native missing-resource response and an unavailable service are distinct outcomes. If no original exists yet in a new project, record that there is nothing to read. The project can start and add confirmed rules as tickets establish a need.
3. **Effective entry references.** From the active project instructions, open the actual knowledge guide and check that it points to the approved binding. Follow the live Git paths and rule URIs it presents, verify that each opens and applies to its stated target revision, and record broken or stale references. For an established project with missing, stale or empty knowledge, also examine relevant earlier versions of the project entry and guide, including deleted or renamed paths, and use the [rule reference recovery procedure](../plan-feature/references/project-knowledge.md#recover-a-missing-or-stale-rule-reference).

For standalone onboarding or refresh, use the confirmed setup scenario and target release or Git revision to read history and confirmed decisions. Include the confirmed scope, proposed reference repairs and their sources in the setup preview. After applying the approved changes, reopen the effective entry and verify the repaired targets. When the target, service, approval or durable checkpoint is missing, record the affected reference, write or criterion and its recovery condition. Continue the approved setup and independent checks.

## Put daily use in the project guide

Render these instructions with the project's real values so a fresh session can operate without the setup package.

- Include the [binding checks](#verify-the-project-knowledge-binding) as a procedure in the guide, with the actual project-relative helper path, endpoint, identity and private key file for the authenticated check.
- From the ticket or the confirmed standalone setup or refresh scope, pin the scenario and target release or Git revision. Call MCP `find` with `target_uri` set to the project root and `level: [2]`. Call `read` on the original URI before applying a rule. If the ticket supplies a URI, go directly to `read`. Native HTTP equivalents use `POST /api/v1/search/find` and `GET /api/v1/content/read?uri=<encoded-uri>` with `Authorization: Bearer <project-key>`.
- Check the conclusion and scope against the actual target Git revision (`git show <target>:<path>`). A verified clause cites the Git path, section and commit containing it. Resolve obsolete or contradictory records against the accepted source at the target revision. Refer a genuinely undecided case to the outer loop and keep the affected criterion pending.
- Apply the decision owner's explicit version range. When no version was specified, the decision applies from the next regular delivery as scheduled at confirmation, including one already underway, until superseded or withdrawn. Record that target in the original knowledge body. Use its iteration or delivery ticket if it has no version number. For example, `v1.8` in development uses the new rule when it is the next regular delivery. A `v1.7` hotfix uses its previous rule until an explicit backport approval covers `v1.7` and the scenario. Read both the new decision and the approval in that case. If the delivery target cannot be established, keep the affected criterion open.
- For a confirmed clause needed by a later ticket, write the conclusion, applicable versions and scenario, and Git path, section and revision to a stable URI under `<root>/knowledge/`. A materially changed rule gets a versioned URI with the scope and supersession link so maintenance branches can still find their rule. Keep unconfirmed observations and one-off test evidence on the ticket. Add clauses as needed during development.
- When authorized, store full source-backed Markdown research under `<root>/research/` and verified task Episodes under `<root>/episodes/`. Find earlier cases by scenario in that project's `episodes/`, then open the original and follow its evidence. The original ticket carries the verified URI.

Render the [rule reference recovery steps](../plan-feature/references/project-knowledge.md#recover-a-missing-or-stale-rule-reference) in the guide itself. Include how to find earlier versions of the effective entry, read deleted or renamed paths from Git, and follow their leads to confirmed decisions in the configured tracker. Cover standalone read-only recovery and preview by confirmed scenario and target. Select the effective rule, repair approved links, retain retired history, and hold only the references or criteria that depend on missing evidence.

Render the [shared write and recovery procedure](../plan-feature/references/project-knowledge.md#checkpoint-write-and-recover) as executable instructions in this order so it works from the project guide alone.

1. Before writing, checkpoint the exact URI, target version or revision, confirmation source and complete approved UTF-8 body on the original ticket. For standalone setup or refresh, reuse a confirmed decision record with the full checkpoint or save it durably using the linked project tracker guide. Secure approval and an authorized result destination linked to that checkpoint before writing. If either is missing, leave that write pending and continue other checks. Preserve an approved source file byte for byte as a linked attachment. Reopen the checkpoint and its body. Use one submission owner per URI.
2. For a new URI or a resumed write, read the exact URI. If the body matches byte for byte, skip the knowledge write and proceed to step 4. If authenticated native `404` confirms this resource is missing, proceed to step 3. A separately authorized correction can proceed after verifying the current text and reconciling its scope. For all other mismatches or errors, keep the checkpoint pending and record the observed error and next action.
3. For the write authorized in step 2, load `content` directly from the approved UTF-8 bytes, preserving line endings and the final newline. Compare the outgoing bytes with the approved original and any recorded digest. Make one `POST /api/v1/content/write` with `uri`, `content`, `mode: "replace"`, `processing_mode: "vectors_only"` and `wait: true` with the ordinary key. Read the **same URI** and compare its full UTF-8 body byte for byte with the approved original. On a match, proceed to step 4.
4. After either exact match, reopen the durable result destination and check for a verification receipt for this checkpoint and URI. If present, preserve it without another entry. If absent, record the verified URI and exact readback once, then reopen the destination and confirm the saved receipt. Follow the verified source URI from that record. Record observed indexing separately and check discovery when the handoff depends on `find`. If the receipt lookup or its write outcome is uncertain, leave it pending and reconcile it on resumption.
5. If readback cannot confirm the original, keep the full checkpoint and record the observed error, pending synchronization and next action. On resumption start with step 2.
