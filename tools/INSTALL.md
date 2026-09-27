# Install and recover the zh skills

Run from the source repository with Python 3.10 or newer. The defaults install
to `/root/.codex/skills` and keep unique backups under
`/root/.codex/skill-backups`, outside skill discovery. The seven source skill
directories must be siblings of `tools/`. Existing `zh` suite directories and
the old `zhiheng` directory are copied in full before any installed directory
changes. Other installed skills are left alone.

```sh
python3 tools/install.py install --dry-run
python3 tools/install.py install
```

The preview makes no filesystem changes. Both commands accept `--source`,
`--target`, and `--backups` for a different layout. Save the `backup_id` printed
by a successful install. The tool also prints the full backup path.

To inspect or reverse an installation, use that exact ID:

```sh
python3 tools/install.py restore BACKUP_ID --dry-run
python3 tools/install.py restore BACKUP_ID
```

Restore first copies every currently installed affected directory into a unique
`restore-archives/` directory inside the backup, then restores the original
directories and removes newly introduced ones. Edits made after installation
therefore remain available in the archive. An already restored backup is a
no-op. Unrelated skills remain untouched.

Each backup's `manifest.json` records the original directory set, install
progress, phase, and restore archives. If installation or restore is interrupted,
read the reported backup ID and run `restore BACKUP_ID`; repeat the same restore
if it is interrupted. A new install for that target is blocked while an
unfinished migration exists. An interrupted backup copy before the manifest is
written does not change installed skills. Do not delete the backup or its
restore archives until recovery is no longer needed.

For a temporary layout, pass the same `--target` and `--backups` to install;
restore reads the target path from the backup manifest and optionally accepts
`--target` to verify it. After a live install, start a new Codex session so the
host rediscovers the new skill set.
