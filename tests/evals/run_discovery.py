"""Run description-only skill discovery cases with isolated Codex state."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((Path(__file__).with_name("discovery.json")).read_text())["cases"]


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(path)
    head = text.split("---\n", 2)[1]
    return "---\n" + head + "---\n"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run_case(case, output):
    destination = output / case["id"]
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(Path(__file__), destination / "runner.py")
    with tempfile.TemporaryDirectory(prefix="zh-discovery-controlled-") as temporary:
        base = Path(temporary).resolve()
        home, codex_home, workspace = (base / name for name in ("home", "codex-home", "project"))
        for path in (home, codex_home, workspace / ".agents/skills"):
            path.mkdir(parents=True)
        (codex_home / "auth.json").symlink_to(Path.home() / ".codex/auth.json")

        candidates = []
        for source in sorted((ROOT / "skills").glob("*/SKILL.md")):
            head = frontmatter(source)
            name = source.parent.name
            target = workspace / ".agents/skills" / name / "SKILL.md"
            target.parent.mkdir()
            target.write_text(head + "\n# Discovery fixture\n", encoding="utf-8")
            candidates.append({"name": name, "frontmatter": head, "source_sha256": digest(source.read_bytes())})
        (destination / "candidates.json").write_text(json.dumps(candidates, indent=2) + "\n")

        policy = base / "boundary.sb"
        forbidden = [
            "/Users/bys/.codex/memories",
            "/Users/bys/.agents/skills",
            "/Users/bys/Documents/my/test/zhiheng",
            str(ROOT),
        ]
        policy.write_text(
            "(version 1)\n(allow default)\n(deny file-read* "
            + " ".join(f'(subpath "{path}")' for path in forbidden)
            + ")\n(deny file-write*)\n"
            + f'(allow file-write* (subpath "{base}"))\n'
            + '(allow file-write-data (literal "/dev/null") (literal "/dev/tty"))\n',
            encoding="utf-8",
        )
        probes = []
        for path in ("/Users/bys/.codex/memories/MEMORY.md",
                     "/Users/bys/.agents/skills/astryx/SKILL.md",
                     "/Users/bys/Documents/my/test/zhiheng/.git/HEAD",
                     str(ROOT / "README.md")):
            probe = subprocess.run(
                ["/usr/bin/sandbox-exec", "-f", str(policy), "python3", "-c",
                 "from pathlib import Path; import sys; Path(sys.argv[1]).read_bytes()", path],
                capture_output=True, text=True,
            )
            probes.append({"path": path, "argv": ["read_bytes", path],
                           "exists_outside_boundary": Path(path).is_file(),
                           "exit": probe.returncode, "stdout": probe.stdout, "stderr": probe.stderr,
                           "denied": probe.returncode != 0 and "PermissionError" in probe.stderr})
        allowed = workspace / ".agents/skills/zh-review/SKILL.md"
        positive = subprocess.run(
            ["/usr/bin/sandbox-exec", "-f", str(policy), "python3", "-c",
             "from pathlib import Path; import sys; print(len(Path(sys.argv[1]).read_bytes()))",
             str(allowed)], capture_output=True, text=True,
        )
        probes.append({"path": str(allowed), "argv": ["read_bytes", str(allowed)],
                       "exit": positive.returncode, "stdout": positive.stdout,
                       "stderr": positive.stderr, "allowed": positive.returncode == 0})
        for label, path, expected_allowed in (
            ("denied-staging-write", output.resolve() / "denied-probe", False),
            ("allowed-project-write", workspace / "boundary-probe", True),
        ):
            argv = ["/usr/bin/sandbox-exec", "-f", str(policy), "python3", "-c",
                    "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('probe')",
                    str(path)]
            check = subprocess.run(argv, capture_output=True, text=True)
            probes.append({"label": label, "argv": argv, "exit": check.returncode,
                           "stdout": check.stdout, "stderr": check.stderr,
                           "expected_allowed": expected_allowed})
            if expected_allowed and path.exists():
                path.unlink()
        (destination / "boundary.json").write_text(json.dumps(probes, indent=2) + "\n")
        if not all(item["denied"] and item["exists_outside_boundary"] for item in probes[:4]) or (
                not probes[4]["allowed"] or probes[5]["exit"] == 0 or
                "PermissionError" not in probes[5]["stderr"] or probes[6]["exit"] != 0):
            raise RuntimeError("Isolation boundary probe failed")

        prompt = (
            "For the request below, select the single most relevant available zh skill, "
            "or null if no skill applies. Use only the available skill names and descriptions. "
            "Do not read skill bodies or files and do not run commands. "
            'Respond only as JSON: {"skill": "name-or-null", "reason": "one short sentence"}.\n\n'
            "Request: " + case["request"] + "\n"
        )
        (destination / "request.txt").write_text(prompt, encoding="utf-8")
        command = [
            "/usr/bin/sandbox-exec", "-f", str(policy), shutil.which("codex"),
            "exec", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
            "--sandbox", "read-only", "--json", "-m", "gpt-6.1-sol",
            "-c", 'model_reasoning_effort="high"', "-c", 'model_provider="openai"',
            "-c", 'features.skip_host_skill_discovery=true', "-c", 'web_search="disabled"',
        ]
        for feature in ("plugins", "remote_plugin", "plugin_discovery_prefetch",
                        "plugin_sharing", "recommended_plugins", "apps", "hooks",
                        "memories", "shell_snapshot", "skill_mcp_dependency_install",
                        "multi_agent", "daemon_auto_start", "system_proxy_fallback"):
            command += ["--disable", feature]
        command += ["-C", str(workspace), "-"]
        env = os.environ.copy()
        env.update({"HOME": str(home), "CODEX_HOME": str(codex_home)})
        (destination / "launch.json").write_text(json.dumps({
            "argv": command, "cwd": str(workspace),
            "environment_overrides": {"HOME": str(home), "CODEX_HOME": str(codex_home)},
            "policy_sha256": digest(policy.read_bytes()),
            "runner_sha256": digest((destination / "runner.py").read_bytes()),
            "fixture": "17 exact skill frontmatters plus inert body; no other project files",
            "requested_model": "gpt-6.1-sol", "requested_reasoning": "high",
            "actual_server_model": "not exposed by CLI event stream",
        }, indent=2) + "\n")
        try:
            result = subprocess.run(command, input=prompt, env=env, capture_output=True,
                                    text=True, timeout=180)
        except subprocess.TimeoutExpired as exc:
            (destination / "events.jsonl").write_bytes(exc.stdout or b"")
            (destination / "stderr.log").write_bytes(exc.stderr or b"")
            (destination / "result.json").write_text(json.dumps({"exit": "timeout", "expected": case["expected"]}) + "\n")
            return False
        (destination / "events.jsonl").write_text(result.stdout)
        (destination / "stderr.log").write_text(result.stderr)
        events = [json.loads(line) for line in result.stdout.splitlines()]
        messages = [event["item"]["text"] for event in events
                    if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message"]
        selected = None
        if messages:
            try:
                selected = json.loads(messages[-1])["skill"]
            except (json.JSONDecodeError, KeyError):
                selected = "unparsed"
        tool_events = [event for event in events if event.get("item", {}).get("type") in
                       {"command_execution", "web_search", "collab_tool_call"}]
        matched = result.returncode == 0 and selected == case["expected"] and not tool_events
        (destination / "result.json").write_text(json.dumps({
            "exit": result.returncode, "expected": case["expected"], "selected": selected,
            "tool_events": len(tool_events), "matched": matched, "final": messages[-1] if messages else None,
        }, indent=2, ensure_ascii=False) + "\n")
        return matched


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "docs/evidence/i07/controlled")
    parser.add_argument("--ids", nargs="*")
    args = parser.parse_args()
    cases = [case for case in CASES if not args.ids or case["id"] in args.ids]
    results = {case["id"]: run_case(case, args.output) for case in cases}
    print(json.dumps(results, ensure_ascii=False))
    raise SystemExit(0 if all(results.values()) else 1)
