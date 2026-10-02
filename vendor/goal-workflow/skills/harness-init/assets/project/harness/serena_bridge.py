"""Thin native Serena 1.7.0 API bridge, executed by Serena's own Python.

CLI 1.7.0 has no register-only or rendered-onboarding command. These operations
call the pinned package APIs used by upstream CLI/OnboardingTool; they do not
create another knowledge store or claim semantic onboarding has happened.
"""
import argparse
import hashlib
import sys
import importlib.metadata
import json
import platform


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("register", "onboarding", "update", "rename-plan", "rename"))
    parser.add_argument("project")
    args = parser.parse_args()
    if importlib.metadata.version("serena-agent") != "1.7.0":
        raise SystemExit("serena-agent==1.7.0 is required")
    from serena.config.serena_config import SerenaConfig
    config = SerenaConfig.from_config_file()
    project = config.get_registered_project(args.project, autoregister=args.action == "register")
    if project is None:
        raise SystemExit("Project must have an existing native project.yml and be registered")
    if args.action == "register":
        print(json.dumps({"registered": True, "project_root": str(project.project_root),
                          "host_activated": False, "onboarding_completed": False}))
        return
    from serena.prompt_factory import SerenaPromptFactory
    manager = project.get_project_instance(config).memory_manager
    if args.action in ("update", "rename-plan", "rename"):
        payload = json.load(sys.stdin)
        listed = manager.list_memories()
        names = listed.get_full_list()
        protected = set(listed.read_only_memories)
        contents = {name: manager.load_memory(name) for name in names}
        digest = lambda text: hashlib.sha256(text.encode("utf-8")).hexdigest()
        if args.action == "update":
            name = payload["name"]
            if name.startswith("global/") or name not in contents or name in protected:
                raise SystemExit("Native edit refused: missing/global/read-only memory")
            if digest(contents[name]) != payload["expected_sha256"]:
                raise SystemExit("Native edit preimage changed")
            output = manager.save_memory(name, payload["content"], is_tool_context=True)
            print(json.dumps({"updated": True, "memory": name, "native_output": output}))
            return
        old, new = payload["old_name"], payload["new_name"]
        if old.startswith("global/") or new.startswith("global/") or old not in contents or new in contents:
            raise SystemExit("Native rename refused: missing source, global scope or occupied destination")
        if digest(contents[old]) != payload["expected_sha256"]:
            raise SystemExit("Native rename source preimage changed")
        changes = {old: None}
        for name, content in contents.items():
            updated, count = manager.rename_references_to_memory(content, old, new)
            if name == old or count:
                if name.startswith("global/") or name in protected:
                    raise SystemExit("Native rename would alter global/read-only memory")
                changes[new if name == old else name] = updated
        snapshot = hashlib.sha256(json.dumps(contents, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if args.action == "rename-plan":
            print(json.dumps({"changes": changes, "snapshot_sha256": snapshot}))
            return
        if snapshot != payload["snapshot_sha256"]:
            raise SystemExit("Native memory graph changed after rename plan")
        output, count = manager.rename_memory_and_propagate_references(old, new, is_tool_context=True)
        print(json.dumps({"renamed": True, "old_name": old, "new_name": new,
                          "updated_references": count, "native_output": output}))
        return
    maintenance = manager.ensure_memory_maintenance_memory()
    prompt = SerenaPromptFactory().create_onboarding_prompt(
        system=platform.system(), memory_maintenance_name=maintenance)
    print(json.dumps({"instructions": prompt, "maintenance_memory": maintenance,
                      "onboarding_completed": False, "host_activated": False}))


if __name__ == "__main__":
    main()
