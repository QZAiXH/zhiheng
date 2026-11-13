"""Exercise one explicit stage in a project with isolated Codex state."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
RUN_ID = os.environ.get("ZH_EVAL_RUN_ID")
if not RUN_ID or "/" in RUN_ID or RUN_ID.startswith("."):
    raise SystemExit("Set ZH_EVAL_RUN_ID to a new simple run name")
OUTPUT = ROOT / "docs/evidence/i07/controlled-stage" / RUN_ID
OUTPUT.mkdir(parents=True, exist_ok=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


with tempfile.TemporaryDirectory(prefix="zh-i07-stage-") as temporary:
    base = Path(temporary).resolve()
    home, codex_home, project = (base / name for name in ("home", "codex-home", "project"))
    home.mkdir()
    codex_home.mkdir()
    project.mkdir()
    (codex_home / "auth.json").symlink_to(Path.home() / ".codex/auth.json")
    for name in ("zh", "zh-spec"):
        shutil.copytree(ROOT / "skills" / name, project / ".agents/skills" / name)

    inputs = {
        "decisions.md": (
            "# Accepted decisions\n"
            "Implement `add(a, b)` for any two integers, including negative values. "
            "The result is their arithmetic sum. Existing `calc.py` is the current implementation, "
            "but this assignment ends at an executable specification. "
            "Acceptance examples: `add(2, 3) == 5`, `add(2, -3) == -1`, "
            "and `add(-2, -3) == -5`. Standard Python; no persistence or migration.\n"
        ),
        "calc.py": "def add(a: int, b: int) -> int:\n    return a - b\n",
    }
    for name, text in inputs.items():
        (project / name).write_text(text, encoding="utf-8")
    sources = {p.relative_to(project).as_posix(): sha(p)
               for p in (project / ".agents/skills").rglob("*") if p.is_file()}
    prompt = (
        "$zh-spec Turn the accepted decisions in decisions.md into an executable "
        "specification in spec.md. Inspect calc.py for the current behavior and "
        "identify the implementation gap. Deliver only this specification stage; "
        "do not edit calc.py or decisions.md. Respond with the spec location and readiness.\n"
    )
    (OUTPUT / "request.txt").write_text(prompt)
    (OUTPUT / "inputs.json").write_text(json.dumps({
        "project_files": inputs, "installed_skill_files_sha256": sources,
    }, indent=2, ensure_ascii=False) + "\n")

    policy = base / "boundary.sb"
    policy.write_text(
        '(version 1)\n(allow default)\n'
        '(deny file-read* (subpath "/Users/bys/.codex/memories") '
        '(subpath "/Users/bys/.agents/skills") '
        '(subpath "/Users/bys/Documents/my/test/zhiheng") '
        f'(subpath "{ROOT}"))\n'
        '(deny file-write*)\n'
        f'(allow file-write* (subpath "{base}"))\n'
        '(allow file-write-data (literal "/dev/null") (literal "/dev/tty"))\n'
    )
    probes = []
    for label, path, operation, allowed in (
        ("denied-memory", Path("/Users/bys/.codex/memories/MEMORY.md"), "read", False),
        ("denied-old-target", Path("/Users/bys/Documents/my/test/zhiheng/.git/HEAD"), "read", False),
        ("denied-staging", ROOT / "README.md", "read", False),
        ("allowed-input", project / "decisions.md", "read", True),
        ("denied-staging-write", ROOT / "docs/evidence/i07/controlled-stage/denied-probe", "write", False),
        ("allowed-project-write", project / "boundary-probe", "write", True),
    ):
        code = ("from pathlib import Path; import sys; "
                "Path(sys.argv[1]).read_bytes()" if operation == "read" else
                "from pathlib import Path; import sys; Path(sys.argv[1]).write_text('probe')")
        argv = ["/usr/bin/sandbox-exec", "-f", str(policy), "python3", "-c", code, str(path)]
        probe = subprocess.run(argv, capture_output=True, text=True)
        probes.append({"label": label, "argv": argv, "path_exists_before": path.is_file()
                       if operation == "read" else None, "exit": probe.returncode,
                       "stdout": probe.stdout, "stderr": probe.stderr, "expected_allowed": allowed})
        if operation == "write" and allowed and path.exists():
            path.unlink()
        if (probe.returncode == 0) != allowed:
            raise RuntimeError(f"Boundary probe mismatch: {label}")
    (OUTPUT / "boundary.json").write_text(json.dumps(probes, indent=2) + "\n")
    env = os.environ.copy()
    env.update({"HOME": str(home), "CODEX_HOME": str(codex_home)})
    command = [
        "/usr/bin/sandbox-exec", "-f", str(policy), shutil.which("codex"),
        "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
        "--skip-git-repo-check", "--sandbox", "danger-full-access", "--json",
        "-m", "gpt-6.1-sol", "-c", 'model_reasoning_effort="high"',
        "-c", 'model_provider="openai"', "-c", 'approval_policy="never"',
        "-c", 'features.skip_host_skill_discovery=true', "-c", 'web_search="disabled"',
        "-c", 'allow_login_shell=false', "-C", str(project), "-",
    ]
    for feature in ("plugins", "remote_plugin", "plugin_discovery_prefetch", "plugin_sharing",
                    "recommended_plugins", "apps", "hooks", "memories", "shell_snapshot",
                    "skill_mcp_dependency_install", "multi_agent", "daemon_auto_start",
                    "system_proxy_fallback"):
        command[command.index("-C"):command.index("-C")] = ["--disable", feature]
    (OUTPUT / "launch.json").write_text(json.dumps({
        "argv": command, "cwd": str(project),
        "environment_overrides": {"HOME": str(home), "CODEX_HOME": str(codex_home)},
        "policy_sha256": hashlib.sha256(policy.read_bytes()).hexdigest(),
        "runner_sha256": sha(Path(__file__)),
        "outer_boundary": "macOS sandbox-exec limits reads and writes; CLI sandbox uses danger-full-access inside it",
        "requested_model": "gpt-6.1-sol", "requested_reasoning": "high",
        "actual_server_model": "not exposed by CLI event stream",
    }, indent=2) + "\n")
    try:
        result = subprocess.run(command, input=prompt, env=env, capture_output=True,
                                text=True, timeout=300)
    except subprocess.TimeoutExpired as exc:
        (OUTPUT / "events.jsonl").write_bytes(exc.stdout or b"")
        (OUTPUT / "stderr.log").write_bytes(exc.stderr or b"")
        (OUTPUT / "result.json").write_text('{"exit":"timeout"}\n')
        raise SystemExit(1)
    (OUTPUT / "events.jsonl").write_text(result.stdout)
    (OUTPUT / "stderr.log").write_text(result.stderr)
    spec = project / "spec.md"
    if spec.is_file():
        shutil.copy2(spec, OUTPUT / "spec.md")
    preserved = {name: sha(project / name) == hashlib.sha256(text.encode()).hexdigest()
                 for name, text in inputs.items()}
    actual = {p.relative_to(project).as_posix() for p in project.rglob("*") if p.is_file()
              and ".agents" not in p.parts}
    events = [json.loads(line) for line in result.stdout.splitlines()]
    commands = [event["item"].get("command", "") for event in events
                if event.get("item", {}).get("type") == "command_execution"]
    report = {
        "exit": result.returncode, "spec_created": spec.is_file(),
        "spec_sha256": sha(spec) if spec.is_file() else None,
        "preserved_inputs": preserved, "project_files": sorted(actual),
        "read_zh_spec": any("zh-spec/SKILL.md" in cmd for cmd in commands),
        "commands": commands,
    }
    (OUTPUT / "result.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: report[key] for key in
                      ("exit", "spec_created", "preserved_inputs", "project_files", "read_zh_spec")}))
    raise SystemExit(0 if result.returncode == 0 and spec.is_file()
                     and all(preserved.values()) and actual == set(inputs) | {"spec.md"} else 1)
