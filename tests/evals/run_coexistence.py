"""Evaluate discovery with zhiheng and overlapping installed skill descriptions."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = Path("/Users/bys/.codex/plugins/cache/mattpocock/mattpocock-skills/1.3.2/skills")
OTHERS = {
    "code-review": UPSTREAM / "engineering/code-review/SKILL.md",
    "tdd": UPSTREAM / "engineering/tdd/SKILL.md",
    "research": UPSTREAM / "engineering/research/SKILL.md",
    "diagnosing-bugs": UPSTREAM / "engineering/diagnosing-bugs/SKILL.md",
    "harness-engineering": ROOT.parent / ".agents/skills/harness-engineering/SKILL.md",
}
CASES = {
    "adopted-review": (
        "This project has adopted the zhiheng workflow. Review the current change against "
        "its accepted spec and coding standards, and report both axes.", "zh-review"),
    "adopted-whole": (
        "This project has adopted zhiheng. Implement this accepted feature, get an independent "
        "review, verify completion criteria, and hand off the local result.", "zh"),
    "explicit-upstream": (
        "Use the installed code-review skill to review the changes since main.", "code-review"),
    "neighbor": ("Translate this single sentence into English.", None),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def frontmatter(data):
    text = data.decode("utf-8")
    if not text.startswith("---\n") or "---\n" not in text[4:]:
        raise ValueError("Missing skill frontmatter")
    return "---\n" + text.split("---\n", 2)[1] + "---\n"


def run_case(case_id, request, expected, destination):
    destination.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="zh-coexistence-") as temp:
        base = Path(temp).resolve()
        home, codex_home, project = (base / name for name in ("home", "codex-home", "project"))
        for path in (home, codex_home, project / ".agents/skills"):
            path.mkdir(parents=True)
        (codex_home / "auth.json").symlink_to(Path.home() / ".codex/auth.json")
        candidates = []
        sources = {p.parent.name: p for p in (ROOT / "skills").glob("*/SKILL.md")}
        sources.update(OTHERS)
        for name, source in sorted(sources.items()):
            data = source.read_bytes()
            head = frontmatter(data)
            target = project / ".agents/skills" / name / "SKILL.md"
            target.parent.mkdir()
            target.write_text(head + "\n# Discovery fixture\n")
            candidates.append({"name": name, "source": str(source),
                               "sha256": sha(data), "frontmatter": head})
        (destination / "candidates.json").write_text(json.dumps(candidates, indent=2) + "\n")
        policy = base / "boundary.sb"
        forbidden = [str(ROOT), str(ROOT.parent / "zhiheng-new"),
                     "/Users/bys/.codex/memories", "/Users/bys/.agents/skills",
                     str(UPSTREAM)]
        policy.write_text(
            "(version 1)\n(allow default)\n(deny file-read* "
            + " ".join(f'(subpath \"{path}\")' for path in forbidden)
            + ")\n(deny file-write*)\n"
            + f'(allow file-write* (subpath \"{base}\"))\n'
            + '(allow file-write-data (literal "/dev/null") (literal "/dev/tty"))\n'
        )
        probes = []
        for path in (ROOT / "README.md", UPSTREAM / "engineering/code-review/SKILL.md",
                     project / ".agents/skills/zh-review/SKILL.md"):
            check = subprocess.run(
                ["/usr/bin/sandbox-exec", "-f", str(policy), "python3", "-c",
                 "from pathlib import Path; import sys; Path(sys.argv[1]).read_bytes()",
                 str(path)], capture_output=True, text=True)
            probes.append({"path": str(path), "exists": path.is_file(), "exit": check.returncode,
                           "stdout": check.stdout, "stderr": check.stderr})
        (destination / "boundary.json").write_text(json.dumps(probes, indent=2) + "\n")
        if not (all(p["exists"] for p in probes) and
                all(p["exit"] != 0 and "PermissionError" in p["stderr"] for p in probes[:2]) and
                probes[2]["exit"] == 0):
            raise RuntimeError("Read boundary probe failed")
        prompt = (
            "Select the single most relevant available skill for the request, or null if no skill "
            "applies. Use only available skill names and descriptions. Do not read skill bodies or "
            "files and do not run commands. Respond only as JSON: "
            '{"skill": "name-or-null", "reason": "one short sentence"}.\n\n'
            "Request: " + request + "\n"
        )
        (destination / "request.txt").write_text(prompt)
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
        command += ["-C", str(project), "-"]
        env = os.environ.copy()
        env.update(HOME=str(home), CODEX_HOME=str(codex_home))
        (destination / "launch.json").write_text(json.dumps({
            "argv": command, "cwd": str(project),
            "environment_overrides": {"HOME": str(home), "CODEX_HOME": str(codex_home)},
            "policy_sha256": sha(policy.read_bytes()),
            "runner_sha256": sha(Path(__file__).read_bytes()),
            "requested_model": "gpt-6.1-sol", "requested_reasoning": "high",
            "actual_server_model": "not exposed",
        }, indent=2) + "\n")
        try:
            result = subprocess.run(command, input=prompt, env=env, capture_output=True,
                                    text=True, timeout=180)
        except subprocess.TimeoutExpired as exc:
            (destination / "events.jsonl").write_bytes(exc.stdout or b"")
            (destination / "stderr.log").write_bytes(exc.stderr or b"")
            (destination / "result.json").write_text(json.dumps({
                "exit": "timeout", "expected": expected, "matched": False}) + "\n")
            return False
        (destination / "events.jsonl").write_text(result.stdout)
        (destination / "stderr.log").write_text(result.stderr)
        events = [json.loads(line) for line in result.stdout.splitlines()]
        messages = [e["item"]["text"] for e in events if e.get("type") == "item.completed"
                    and e.get("item", {}).get("type") == "agent_message"]
        try:
            selected = json.loads(messages[-1])["skill"] if messages else "no-response"
        except (ValueError, KeyError):
            selected = "unparsed"
        tools = [e for e in events if e.get("item", {}).get("type") in
                 {"command_execution", "web_search", "collab_tool_call"}]
        matched = result.returncode == 0 and selected == expected and not tools
        (destination / "result.json").write_text(json.dumps({
            "exit": result.returncode, "expected": expected, "selected": selected,
            "tool_events": len(tools), "matched": matched, "final": messages[-1] if messages else None,
        }, indent=2) + "\n")
        return matched


if __name__ == "__main__":
    output = ROOT / "docs/evidence/i07/coexistence/R01-20261113"
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(Path(__file__), output / "runner.py")
    results = {name: run_case(name, *case, output / name) for name, case in CASES.items()}
    (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results))
    raise SystemExit(0 if all(results.values()) else 1)
