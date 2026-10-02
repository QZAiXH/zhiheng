"""JSON Schema + deterministic consistency gates, with no verification claims.

The installed project uses jsonschema==4.26.0 from its locked tool environment.
The sibling harness_check.py remains a portable, stdlib-only CLI.
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator

try:
    from .harness_check import Validator as ConsistencyValidator, fingerprint, check_fingerprint, scaffold, NOTICE
except ImportError:  # Direct script import, including the initializer's fallback.
    from harness_check import Validator as ConsistencyValidator, fingerprint, check_fingerprint, scaffold, NOTICE

SCHEMA_DIRECTORY = Path(__file__).resolve().parent.parent / "schemas"
if not SCHEMA_DIRECTORY.is_dir():
    SCHEMA_DIRECTORY = Path(__file__).resolve().parent / "schemas"


def schema_errors(value, kind):
    """Validate one input/result object; no network resolvers or dynamic schemas."""
    if kind not in ("input", "result"):
        raise ValueError("kind must be input or result")
    path = SCHEMA_DIRECTORY / ("task-" + kind + ".schema.json")
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    failures = sorted(validator.iter_errors(value), key=lambda item: str(list(item.absolute_path)))
    return [{"path": kind + ("." + ".".join(str(x) for x in item.absolute_path)
                            if item.absolute_path else ""),
             "message": item.message, "source": "jsonschema"} for item in failures]


class Validator(ConsistencyValidator):
    """Same API as the portable helper, plus actual input/result JSON Schemas."""
    def evidence(self):
        super().evidence()
        if isinstance(self.bundle, dict):
            for kind in ("input", "result"):
                self.errors.extend(schema_errors(self.bundle.get(kind), kind))
        return not self.errors


def evaluate_bundle(bundle, command="preflight"):
    if command not in ("preflight", "evidence"):
        raise ValueError("command must be preflight or evidence")
    validator = Validator(bundle)
    okay = validator.preflight() if command == "preflight" else validator.evidence()
    decision = ("configuration_consistent" if command == "preflight" else
                "eligible_for_independent_verification") if okay else "blocked"
    return {"version": 1, "command": command, "ok": okay, "decision": decision,
            "errors": validator.errors, "notice": NOTICE}
