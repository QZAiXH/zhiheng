"""Observe a natural review request with overlapping complete skills installed."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = Path("/Users/bys/.codex/plugins/cache/mattpocock/mattpocock-skills/1.3.2/skills")
RUN = ROOT / "docs/evidence/i07/coexistence/R01-20261113/natural-review"
RUN.mkdir(parents=True, exist_ok=False)
shutil.copy2(Path(__file__), RUN / "runner.py")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


with tempfile.TemporaryDirectory(prefix="zh-coexistence-natural-") as temp:
    base = Path(temp).resolve()
    home, codex_home, project = (base / name for name in ("home", "codex-home", "project"))
    for path in (home, codex_home, project / ".agents/skills"):
        path.mkdir(parents=True)
    (codex_home / "auth.json").symlink_to(Path.home() / ".codex/auth.json")
    sources = {p.name: p for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()}
    sources.update({
        "code-review": UPSTREAM / "engineering/code-review",
        "tdd": UPSTREAM / "engineering/tdd",
        "research": UPSTREAM / "engineering/research",
        "diagnosing-bugs": UPSTREAM / "engineering/diagnosing-bugs",
        "harness-engineering": ROOT.parent / ".agents/skills/harness-engineering",
    })
    for name, source in sorted(sources.items()):
        shutil.copytree(source, project / ".agents/skills" / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    inputs = {
        "AGENTS.md": "This project adopts the zhiheng workflow. Review against the accepted local specification and standards. Report precise findings with evidence. Do not edit on a review-only request.\n",
        "spec.md": "# Addition\n`add(a, b)` returns the sum of integers including negative inputs. New behavior needs a regression test.\n",
        "calc.py": "def add(a: int, b: int) -> int:\n    return a - b\n",
    }
    for name, text in inputs.items():
        (project / name).write_text(text)
    prompt = "Review calc.py against spec.md and the local project standards. Report findings only; do not edit.\n"
    (RUN / "request.txt").write_text(prompt)
    installed = {p.relative_to(project).as_posix(): sha(p)
                 for p in (project / ".agents/skills").rglob("*") if p.is_file()}
    (RUN / "inputs.json").write_text(json.dumps({
        "files": inputs, "installed_skill_files_sha256": installed,
        "skill_sources": {k: str(v) for k, v in sources.items()},
    }, indent=2, ensure_ascii=False) + "\n")
    policy = base / "boundary.sb"
    policy.write_text(
        "(version 1)\n(allow default)\n"
        '(deny file-read* (subpath "/Users/bys/.codex/memories") '
        '(subpath "/Users/bys/.agents/skills") '
        f'(subpath "{ROOT}") (subpath "{UPSTREAM}"))\n'
        "(deny file-write*)\n"
        f'(allow file-write* (subpath "{home}") (subpath "{codex_home}"))\n'
        '(allow file-write-data (literal "/dev/null") (literal "/dev/tty"))\n'
    )
    probes = []
    for path, allowed in ((ROOT / "README.md", False),
                          (UPSTREAM / "engineering/code-review/SKILL.md", False),
                          (project / ".agents/skills/zh-review/SKILL.md", True)):
        check = subprocess.run(
            ["/usr/bin/sandbox-exec", "-f", str(policy), "python3", "-c",
             "from pathlib import Path; import sys; Path(sys.argv[1]).read_bytes()", str(path)],
            capture_output=True, text=True)
        probes.append({"path": str(path), "exists": path.is_file(), "exit": check.returncode,
                       "stdout": check.stdout, "stderr": check.stderr, "expected_allowed": allowed})
    (RUN / "boundary.json").write_text(json.dumps(probes, indent=2) + "\n")
    if not all(p["exists"] and ((p["exit"] == 0) == p["expected_allowed"])
               for p in probes):
        raise RuntimeError("Boundary probe failed")
    command = [
        "/usr/bin/sandbox-exec", "-f", str(policy), shutil.which("codex"),
        "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
        "--skip-git-repo-check", "--sandbox", "danger-full-access", "--json",
        "-m", "gpt-6.1-sol", "-c", 'model_reasoning_effort="high"',
        "-c", 'model_provider="openai"', "-c", 'approval_policy="never"',
        "-c", 'features.skip_host_skill_discovery=true', "-c", 'web_search="disabled"',
        "-c", 'allow_login_shell=false',
    ]
    for feature in ("plugins", "remote_plugin", "plugin_discovery_prefetch", "plugin_sharing",
                    "recommended_plugins", "apps", "hooks", "memories", "shell_snapshot",
                    "skill_mcp_dependency_install", "multi_agent", "daemon_auto_start",
                    "system_proxy_fallback"):
        command += ["--disable", feature]
    command += ["-C", str(project), "-"]
    env = os.environ.copy()
    env.update(HOME=str(home), CODEX_HOME=str(codex_home))
    (RUN / "launch.json").write_text(json.dumps({
        "argv": command, "cwd": str(project),
        "environment_overrides": {"HOME": str(home), "CODEX_HOME": str(codex_home)},
        "policy_sha256": sha(policy), "runner_sha256": sha(RUN / "runner.py"),
        "requested_model": "gpt-6.1-sol", "requested_reasoning": "high",
        "actual_server_model": "not exposed",
    }, indent=2) + "\n")
    try:
        result = subprocess.run(command, input=prompt, env=env, capture_output=True,
                                text=True, timeout=240)
    except subprocess.TimeoutExpired as exc:
        (RUN / "events.jsonl").write_bytes(exc.stdout or b"")
        (RUN / "stderr.log").write_bytes(exc.stderr or b"")
        (RUN / "result.json").write_text('{"exit":"timeout"}\n')
        raise SystemExit(1)
    (RUN / "events.jsonl").write_text(result.stdout)
    (RUN / "stderr.log").write_text(result.stderr)
    events = [json.loads(line) for line in result.stdout.splitlines()]
    completed = [e["item"] for e in events if e.get("type") == "item.completed"]
    skill = project / ".agents/skills/zh-review/SKILL.md"
    loaded = any(i.get("type") == "command_execution" and i.get("exit_code") == 0
                 and "zh-review/SKILL.md" in i.get("command", "")
                 and skill.read_text() in i.get("aggregated_output", "") for i in completed)
    reads = [i.get("command") for i in completed
             if i.get("type") == "command_execution" and "/SKILL.md" in i.get("command", "")]
    final = [i["text"] for i in completed if i.get("type") == "agent_message"]
    preserved = all(sha(project / name) == hashlib.sha256(text.encode()).hexdigest()
                    for name, text in inputs.items())
    output = {"exit": result.returncode, "loaded_zh_review": loaded,
              "skill_read_commands": reads, "inputs_preserved": preserved,
              "final": final[-1] if final else None}
    (RUN / "result.json").write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: output[k] for k in ("exit", "loaded_zh_review", "inputs_preserved")}))
    raise SystemExit(0 if result.returncode == 0 and loaded and preserved else 1)
