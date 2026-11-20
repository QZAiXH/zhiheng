# Configure project delivery

The effective project entry links to the generated tracker guide, normally `docs/agents/issue-tracker.md`. Keep exactly one standalone delivery line in that guide. Its spelling stays fixed across languages.

- `<!-- harness-delivery: local -->` selects local delivery. Record the branch, commit and verification on the original ticket after acceptance.
- `<!-- harness-delivery: github-pr -->` selects GitHub PR delivery. Open or reuse the PR in the code repository, link the original ticket, and check acceptance and applicable CI/CD on the current PR head before closure. When no remote checks apply, record how that was established and the agreed local verification. Leave the PR for the user to merge.

Downstream readers open the guide directly and use its delivery value. A missing or ambiguous line leaves the delivery choice pending. An intake opt-in controls whether a PR or MR can supply a request. The delivery value controls how accepted changes are handed off. Honor a request to stop after development or to produce only an acceptance report.

## Preview and apply

Use [delivery_config.py](scripts/delivery_config.py) with Python 3.9+ and the path of the effective guide. `read GUIDE` prints the value or `missing`. Duplicate or malformed lines need a targeted repair in the preview. For an existing guide with a missing value, propose adding the single delivery line. For an unchanged setup, report the current values and leave the files untouched.

Keep scratch files outside the target working tree. For a new guide, prepare a localized draft from the selected template. For an existing guide, start the draft and a separate baseline copy from the original bytes. With a tracker switch, edit the relevant passages of the draft in place. Update the tracker identity, commands, current ticket paths and links where applicable. Carry over hand-written notes and preserve historical ticket references. Preserve the confirmed intake opt-in for the same request surface. Resolve its applicability with the user if the surface changes and the existing opt-in is affected.

Set `skill_dir` to the setup skill directory, `draft` and `candidate` to separate scratch paths, `tracker` to `github`, `gitlab` or `local`, and `mode` to the resolved delivery value. Use the output as the final candidate.

```sh
python3 -B "$skill_dir/scripts/delivery_config.py" prepare "$draft" "$tracker" "$mode" > "$candidate"
```

Compare the original bytes and the final candidate with `diff -u "$baseline" "$candidate"`. Use `/dev/null` as the baseline for a new guide. A result of 0 means equal bytes, 1 means a diff, and any other result means an error. Show the actual diff, including any tracker updates, for confirmation. Keep the baseline and candidate used for that preview.

After confirmation, set `guide` to the previewed destination and apply the approved candidate against the saved baseline.

```sh
python3 -B "$skill_dir/scripts/delivery_config.py" apply "$guide" "$candidate" --baseline "$baseline"
```

For a new guide, omit `--baseline`. Resolve any guide symlink to its actual target before preparing the preview. The command preserves an existing symlink and the approved bytes. If the guide already equals the candidate, it leaves the file untouched. If the baseline changed, reread the guide and preview the revised diff before applying it. Reopen the guide after applying and verify both the tracker target and delivery value.
