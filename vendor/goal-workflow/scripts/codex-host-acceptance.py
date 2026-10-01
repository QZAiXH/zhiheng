#!/usr/bin/env python3
"""Opt-in Codex host probe; isolated repo, normal sandbox, no auth/config edits.

Default only prepares artifacts. --run-models requires an explicit model and
call budget, uses the caller's authenticated Codex, incurs normal model usage,
and creates one resumable test session. A call means one Codex invocation, not
one underlying API request or a monetary cap. It does
not certify full Harness, GitHub, Serena, cancellation or semantic review quality.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--output", help="new, nonexistent artifact directory; otherwise a temp directory is preserved")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--run-models", action="store_true")
    parser.add_argument("--model", help="explicit model for every model step, including review and resume")
    parser.add_argument("--max-model-calls", type=int,
                        help="explicit maximum Codex model invocations (1..4); no retries")
    args = parser.parse_args()
    if os.name != "posix":
        parser.error("this process-group runner supports Linux/macOS; use WSL on Windows")
    if args.timeout < 10 or args.timeout > 1800:
        parser.error("timeout must be 10..1800 seconds per model step")
    if args.model is not None and (not args.model.strip() or args.model != args.model.strip()
                                   or any(c.isspace() for c in args.model)):
        parser.error("model must be a nonempty model identifier without whitespace")
    if args.max_model_calls is not None and not 1 <= args.max_model_calls <= 4:
        parser.error("max-model-calls must be 1..4")
    if args.run_models and (args.model is None or args.max_model_calls is None):
        parser.error("--run-models requires explicit --model and --max-model-calls")
    root = Path(args.output).absolute() if args.output else Path(tempfile.mkdtemp(prefix="codex-host-acceptance-"))
    if args.output:
        root.mkdir(parents=True, exist_ok=False)
    repo = root / "repo"
    repo.mkdir()
    summary = {"artifact_directory": str(root), "status": "prepared", "steps": [],
               "limits": {"model_step_seconds": args.timeout,
                          "max_model_calls": args.max_model_calls if args.run_models else 0,
                          "script_retries": 0},
               "model_calls_started": 0,
               "model_policy": {"model": args.model, "review_model": args.model,
                                "reasoning_effort": "low", "service_tier": "default",
                                "budget_unit": "Codex invocation; not API requests or currency"},
               "scope": "isolated host discovery/implementation/review/resume/handoff; not full Harness acceptance"}

    def save():
        (root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")

    def command(name, argv, timeout=30, expected=0, model_call=False):
        if model_call:
            if summary["model_calls_started"] >= args.max_model_calls:
                raise RuntimeError(name + ": model invocation budget exhausted; no further call started")
            # Charge before spawn, including failures and uncertain starts.
            summary["model_calls_started"] += 1
        start = time.monotonic()
        record = {"name": name, "argv": argv, "cwd": str(repo), "timeout_seconds": timeout}
        if model_call:
            record.update(model_call_number=summary["model_calls_started"],
                          model_policy=dict(summary["model_policy"]))
        summary["steps"].append(record)
        save()
        try:
            process = subprocess.Popen(argv, cwd=repo, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, start_new_session=True)
            try:
                out, err = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                record["timed_out"] = True
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    out, err = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    out, err = process.communicate(timeout=5)
            record["exit_code"] = process.returncode
        except (OSError, subprocess.TimeoutExpired) as exc:
            record["error"] = str(exc)
            save()
            raise RuntimeError(name + ": command could not complete") from exc
        (root / (name + ".stdout")).write_text(out)
        (root / (name + ".stderr")).write_text(err)
        record["elapsed_seconds"] = time.monotonic() - start
        record["stdout"] = name + ".stdout"
        record["stderr"] = name + ".stderr"
        save()
        if record.get("timed_out") or process.returncode != expected:
            raise RuntimeError(name + ": inspect preserved output; not passed")
        return out

    try:
        command("git-init", ["git", "init", "-b", "main"])
        (repo / "calculator.py").write_text("def add(a, b):\n    return a - b\n")
        (repo / "test_calculator.py").write_text(
            "import unittest\nfrom calculator import add\n\n"
            "class Addition(unittest.TestCase):\n"
            "    def test_positive(self):\n        self.assertEqual(add(2, 3), 5)\n"
            "    def test_negative(self):\n        self.assertEqual(add(-2, -3), -5)\n")
        (repo / ".gitignore").write_text("__pycache__/\n")
        skill = repo / ".agents/skills/harness-host-probe"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: harness-host-probe\ndescription: Use only for the isolated Harness host acceptance fixture.\n---\n"
            "For this probe, fix calculator.py to meet the requested acceptance criteria. Preserve tests. "
            "Run the exact configured Python test command. Do not commit, push, install software, change "
            "credentials or configuration, or work outside this fixture. Your final response must contain "
            "HOST_SKILL_LOADED, both acceptance IDs and the real test outcome.\n")
        command("git-add", ["git", "add", "."])
        command("git-baseline", ["git", "-c", "user.name=Harness fixture", "-c",
                                 "user.email=harness-fixture@example.invalid", "commit", "-m", "host probe baseline"])
        command("baseline-tests", [sys.executable, "-B", "-m", "unittest", "-v"], expected=1)
        summary["baseline"] = command("baseline-sha", ["git", "rev-parse", "HEAD"]).strip()
        if not args.run_models:
            save()
            print("Prepared only; no Codex/model invocation. Artifacts: " + str(root))
            return 0
        codex = shutil.which(args.codex) or str(Path(args.codex).absolute())
        summary["codex_version"] = command("codex-version", [codex, "--version"]).strip()
        for name, action in (("codex-help", []), ("codex-review-help", ["review"]),
                             ("codex-resume-help", ["resume"])):
            help_text = command(name, [codex, "exec", *action, "--help"])
            if "--model" not in help_text or "--config" not in help_text:
                raise RuntimeError(name + ": explicit model/config options unsupported; no model call started")

        def model_argv(sandbox, *action):
            # --model and -c are supported by exec, review and resume. Explicit
            # review_model also overrides an inherited review-only model.
            # Official config schema: https://learn.chatgpt.com/docs/config-schema.json
            return [codex, "exec", "--sandbox", sandbox, "--json", "-C", str(repo), *action,
                    "--model", args.model, "-c", "review_model=" + json.dumps(args.model),
                    "-c", 'model_reasoning_effort="low"', "-c", 'service_tier="default"']
        implementation = root / "implementation.txt"
        prompt = ("Use $harness-host-probe for this isolated fixture. Fix addition in calculator.py. "
                  "AC-POS: add(2,3) is 5. AC-NEG: add(-2,-3) is -5. Do not change tests. "
                  "Run " + sys.executable + " -B -m unittest -v. Do not commit or use network. "
                  "Do not access other projects or alter user configuration/authentication.")
        trace = command("implement", model_argv("workspace-write") +
                        ["--output-last-message", str(implementation), prompt], args.timeout, model_call=True)
        events = []
        for line in trace.splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        thread_ids = {event.get("thread_id") for event in events
                      if event.get("type") == "thread.started" and event.get("thread_id")}
        if len(thread_ids) != 1:
            raise RuntimeError("could not identify exactly one created session; no --last fallback is allowed")
        session = next(iter(thread_ids))
        summary["created_session_id"] = session
        if "HOST_SKILL_LOADED" not in implementation.read_text():
            raise RuntimeError("skill loading marker absent; inspect trace rather than assume discovery")
        command("verified-tests", [sys.executable, "-B", "-m", "unittest", "-v"])
        changed = command("changed-files", ["git", "diff", "--name-only"]).splitlines()
        untracked = command("untracked-files", ["git", "ls-files", "--others", "--exclude-standard"]).splitlines()
        if changed != ["calculator.py"] or untracked:
            raise RuntimeError("fixture changed outside calculator.py; inspect artifacts")
        command("independent-review", model_argv("read-only", "review") +
                ["--uncommitted", "--ephemeral"], args.timeout, model_call=True)
        resumed = root / "resume.txt"
        command("exact-session-resume", model_argv("read-only", "resume", session) +
                ["--output-last-message", str(resumed),
                 "Do not run tools or modify files. Recall the two acceptance IDs from this session and their outcome."],
                args.timeout, model_call=True)
        if not all(x in resumed.read_text() for x in ("AC-POS", "AC-NEG")):
            raise RuntimeError("exact-session resume did not recover both acceptance IDs")
        (repo / "handoff.md").write_text(
            "# Host fixture handoff\nAC-POS: add(2,3)=5. AC-NEG: add(-2,-3)=-5.\n"
            "Only calculator.py may change; tests and user configuration must be preserved.\n"
            "Implementation has run; verify actual code and rerun tests before reporting.\n"
            "No commit/push/delivery was requested. Independent review output still requires human inspection.\n"
            "Next: state any unresolved issue; do not ship.\n")
        handoff = root / "fresh-handoff.txt"
        command("fresh-context-handoff", model_argv("read-only") +
                ["--ephemeral", "--output-last-message", str(handoff),
                "Read handoff.md and relevant fixture code. Do not modify files. Recover acceptance conditions, "
                "constraints, current state and next action, and check them. No previous chat is required."],
                args.timeout, model_call=True)
        if not all(x in handoff.read_text() for x in ("AC-POS", "AC-NEG")):
            raise RuntimeError("fresh-context handoff did not preserve both acceptance IDs")
        summary["status"] = "host_steps_executed_review_requires_inspection"
        summary["not_certified"] = ["semantic review quality", "full Harness workflow", "GitHub",
            "Serena onboarding", "cancellation/descendant shutdown", "P5 representative tasks"]
        save()
        print("Host steps executed; inspect independent-review outputs. Artifacts: " + str(root))
        return 0
    except Exception as exc:
        summary["status"] = "blocked"
        summary["reason"] = str(exc)
        save()
        print("Blocked: " + str(exc) + "\nArtifacts preserved: " + str(root), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
