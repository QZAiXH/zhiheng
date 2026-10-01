import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2] / "skills/harness-init/assets/project"
sys.path.insert(0, str(PROJECT))
from harness.tasks import TaskParseError, load_tasks, parse_task

TEMPLATE = """# Log in with a valid password

## Task ID
{tid}

## Description
Authenticate and preserve the user's session.

## Demo path
Submit a valid password, then show the signed-in screen.

## Acceptance Criteria
- [ ] [AC-success] A correct password creates a session.
  The cookie must use the existing security settings.
- [x] [AC-errors] Invalid credentials expose no account details.

## Blocked by
{dependencies}

## Priority
high

## SPEC Reference
specs/login.md §2
"""


class LocalTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "work/feature").mkdir(parents=True)
        self.write("01-login.md", "task-login", "None")

    def write(self, file, tid, dependencies, content=None):
        path = self.root / "work/feature" / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content or TEMPLATE.format(tid=tid, dependencies=dependencies), encoding="utf-8")
        return path

    def load(self, **kwargs):
        return load_tasks(self.root, ["work/feature"], **kwargs)

    def test_preserves_requirements_and_checked_boxes_do_not_authorize_progress(self):
        task = self.load()[0]
        self.assertEqual(task["id"], "task-login")
        self.assertEqual(task["acceptance_ids"], ["AC-success", "AC-errors"])
        self.assertIn("security settings", task["acceptance_criteria"][0]["text"])
        self.assertIn("[x]", task["content"])
        self.assertNotIn("status", task)
        self.assertEqual(task["source_sha256"], hashlib.sha256((self.root / task["source_file"]).read_bytes()).hexdigest())

    def test_two_explicit_directories_and_dependencies(self):
        other = self.root / "other"
        other.mkdir()
        (other / "api.md").write_text(TEMPLATE.format(tid="task-api", dependencies="task-login"))
        tasks = load_tasks(self.root, ["work/feature", "other"])
        self.assertEqual([t["id"] for t in tasks], ["task-api", "task-login"])
        self.assertEqual(tasks[0]["dependencies"], ["task-login"])

    def test_unselected_documentation_is_not_scanned(self):
        (self.root / "README.md").write_text("ordinary documentation")
        self.assertEqual(len(self.load()), 1)

    def test_rename_keeps_id_and_reports_but_refreshes_source_path(self):
        before = self.load()[0]
        (self.root / before["source_file"]).rename(self.root / "work/feature/renamed.md")
        after = self.load()[0]
        self.assertEqual(before["id"], after["id"])
        self.assertEqual(before["reports"], after["reports"])
        self.assertEqual(before["source_sha256"], after["source_sha256"])
        self.assertNotEqual(before["source_file"], after["source_file"])

    def test_report_mapping_by_stable_id(self):
        reports = {"note": "docs/login.html", "walkthrough": "tasks/login.md", "delivery": "docs/login-delivery.md"}
        self.assertEqual(self.load(report_mapping={"task-login": reports})[0]["reports"], reports)

    def test_missing_dependency_never_silently_dropped(self):
        self.write("01-login.md", "task-login", "task-outside-configured-scope")
        with self.assertRaisesRegex(TaskParseError, "missing dependency"):
            self.load()

    def test_cycles_and_self_dependencies(self):
        self.write("01-login.md", "task-login", "task-login")
        with self.assertRaisesRegex(TaskParseError, "cycle"):
            self.load()
        self.write("01-login.md", "task-login", "task-api")
        self.write("02-api.md", "task-api", "task-login")
        with self.assertRaisesRegex(TaskParseError, "cycle"):
            self.load()

    def test_duplicate_task_ids(self):
        self.write("02-duplicate.md", "task-login", "None")
        with self.assertRaisesRegex(TaskParseError, "duplicate Task ID"):
            self.load()

    def test_numeric_ids_and_legacy_number_dependencies_block(self):
        for tid, dependencies in (("01", "None"), ("task-login", "#02"),
                                  ("task-login", "None, task-api"), ("task-login", "task-api and task-db"),
                                  ("task-login", "task-api, task-api")):
            with self.subTest(tid=tid, dependencies=dependencies):
                self.write("01-login.md", tid, dependencies)
                with self.assertRaises(TaskParseError):
                    self.load()

    def test_missing_empty_and_duplicate_sections_block(self):
        base = TEMPLATE.format(tid="task-login", dependencies="None")
        for text in (base.replace("## Task ID", "## Old name"), base.replace("None", ""),
                     base + "\n## Blocked by\nNone\n"):
            self.write("01-login.md", "", "", content=text)
            with self.assertRaises(TaskParseError):
                self.load()

    def test_missing_duplicate_and_malformed_acceptance_ids_block(self):
        base = TEMPLATE.format(tid="task-login", dependencies="None")
        for text in (base.replace("[AC-success] ", ""), base.replace("AC-errors", "AC-success"),
                     base.replace("[AC-success]", "[AC-success/]")):
            self.write("01-login.md", "", "", content=text)
            with self.assertRaises(TaskParseError):
                self.load()

    def test_malformed_markdown_in_selected_directory_blocks(self):
        (self.root / "work/feature/README.md").write_text("not a task")
        with self.assertRaises(TaskParseError):
            self.load()

    def test_symlink_files_and_directories_block(self):
        target = self.root / "external.md"
        target.write_text(TEMPLATE.format(tid="task-other", dependencies="None"))
        (self.root / "work/feature/link.md").symlink_to(target)
        with self.assertRaises(TaskParseError):
            self.load()
        (self.root / "work/feature/link.md").unlink()
        (self.root / "work/feature/linkdir").symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(TaskParseError):
            self.load()

    def test_unsafe_missing_empty_overlapping_task_directories(self):
        for directories in ([], ["../other"], ["missing"], ["work", "work/feature"], ["work/feature", "work/feature"]):
            with self.subTest(directories=directories):
                with self.assertRaises(TaskParseError):
                    load_tasks(self.root, directories)

    def test_report_collisions_and_escape_block(self):
        self.write("02-api.md", "task-api", "None")
        reports = {"note": "docs/shared.html", "walkthrough": "tasks/shared.md", "delivery": "docs/shared-delivery.md"}
        with self.assertRaises(TaskParseError):
            self.load(report_mapping={"task-login": reports, "task-api": reports})
        reports["note"] = "../escape.html"
        with self.assertRaises(TaskParseError):
            self.load(report_mapping={"task-login": reports})

    def test_code_fences_do_not_create_task_sections(self):
        base = TEMPLATE.format(tid="task-login", dependencies="None")
        base = base.replace("## Demo path", "```markdown\n## Blocked by\n# Example, not title\n```\n\n## Demo path")
        self.write("01-login.md", "", "", content=base)
        self.assertIn("## Blocked by", self.load()[0]["description"])

    def test_source_file_limit_and_utf8_errors(self):
        file = self.root / "work/feature/01-login.md"
        for data in (b"", b"\xff", b"x" * (1024 * 1024 + 1)):
            file.write_bytes(data)
            with self.assertRaises(TaskParseError):
                self.load()

    def test_load_is_read_only(self):
        before = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.load()
        after = {str(p): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
