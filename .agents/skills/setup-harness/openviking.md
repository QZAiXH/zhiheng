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

In a fresh Codex client without a project credential environment variable, check that MCP starts and call `find` and `read` against the bound project. If there is no record to read, report the successful connection and the missing readback separately. Record the credential file path and normal Codex startup in the generated project guide. Secret values stay in the private file. If the client lacks local HTTP helper support or project configuration is disabled, report the MCP check as pending and use the native HTTP equivalents below with the same ordinary identity. Configure a different client using its supported credential source.

## Put daily use in the project guide

Render these instructions with the project's real values so a fresh session can operate without the setup package.

- From the ticket's question and target version, call MCP `find` with `target_uri` set to the project root and `level: [2]`. Call `read` on the original URI before applying a rule. If the ticket supplies a URI, go directly to `read`. Native HTTP equivalents use `POST /api/v1/search/find` and `GET /api/v1/content/read?uri=<encoded-uri>` with `Authorization: Bearer <project-key>`.
- Check the conclusion and scope against the actual target Git revision (`git show <target>:<path>`). A verified clause cites the Git path, section and commit containing it. Resolve obsolete or contradictory records against the accepted source at the target revision. Refer a genuinely undecided case to the outer loop and keep the affected criterion pending.
- Apply the decision owner's explicit version range. When no version was specified, the decision applies from the next regular delivery as scheduled at confirmation, including one already underway, until superseded or withdrawn. Record that target in the original knowledge body. Use its iteration or delivery ticket if it has no version number. For example, `v1.8` in development uses the new rule when it is the next regular delivery. A `v1.7` hotfix uses its previous rule until an explicit backport approval covers `v1.7` and the scenario. Read both the new decision and the approval in that case. If the delivery target cannot be established, keep the affected criterion open.
- For a confirmed clause needed by a later ticket, write the conclusion, applicable versions and scenario, and Git path, section and revision to a stable URI under `<root>/knowledge/`. A materially changed rule gets a versioned URI with the scope and supersession link so maintenance branches can still find their rule. Keep unconfirmed observations and one-off test evidence on the ticket. Add clauses as needed during development.
- When authorized, store full source-backed Markdown research under `<root>/research/` and verified task Episodes under `<root>/episodes/`. Find earlier cases by scenario in that project's `episodes/`, then open the original and follow its evidence. The original ticket carries the verified URI.

Render the [shared write and recovery procedure](../plan-feature/references/project-knowledge.md#checkpoint-write-and-recover) as executable instructions in this order so it works from the project guide alone.

1. Before writing, checkpoint the exact URI, target version or revision, confirmation source and complete approved UTF-8 body on the original ticket. When the approved source is a file, preserve it byte for byte as a durable attachment linked from the ticket. Reopen the checkpoint and its body. Use one submission owner per URI.
2. For a new URI or a resumed write, read the exact URI. If the body matches byte for byte, finish with zero writes. If authenticated native `404` confirms this resource is missing, proceed to step 3. A separately authorized correction can proceed after verifying the current text and reconciling its scope. For all other mismatches or errors, keep the checkpoint pending and record the observed error and next action.
3. For the write authorized in step 2, load `content` directly from the approved UTF-8 bytes, preserving line endings and the final newline. Compare the outgoing bytes with the approved original and any recorded digest. Make one `POST /api/v1/content/write` with `uri`, `content`, `mode: "replace"`, `processing_mode: "vectors_only"` and `wait: true` with the ordinary key. Read the **same URI**, compare the full body, and record the verified URI and indexing result separately.
4. If readback cannot confirm the original, keep the full checkpoint and record the observed error, pending synchronization and next action. On resumption start with step 2.
