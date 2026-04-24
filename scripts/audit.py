#!/usr/bin/env python3
"""
Run a lightweight consistency audit for the local agent workspace.

Examples:
    uv run python scripts/audit.py
    uv run python scripts/audit.py subjects/CSCI/workspaces/RL Reinforcement Learning
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT_MARKERS = ("registry/catalog.json", "scripts/scaffold.py")
SOURCE_ID_RE = re.compile(r"\bS\d{3}\b")


@dataclass
class Report:
    target: Path
    infos: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def info(self, message: str) -> None:
        self.infos.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def exit_code(self) -> int:
        return 1 if self.errors else 0


def find_root(start: Path) -> Path:
    start = start.resolve()
    for candidate in [start, *start.parents]:
        if all((candidate / marker).exists() for marker in ROOT_MARKERS):
            return candidate
    raise SystemExit("Could not locate repository root from the provided path.")


def load_json(path: Path, report: Report) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.error(f"Missing JSON file: {path}")
    except json.JSONDecodeError as exc:
        report.error(f"Invalid JSON in {path}: {exc}")
    return None


def read_text(path: Path, report: Report) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        report.error(f"Missing text file: {path}")
    return ""


def is_workspace_dir(path: Path) -> bool:
    return (path / "workspace.json").exists() and (path / "indexes" / "INDEX.md").exists()


def parse_table_rows(index_text: str, heading: str) -> list[list[str]]:
    marker = f"## {heading}"
    if marker not in index_text:
        return []
    section = index_text.split(marker, 1)[1]
    next_header = section.find("\n## ")
    if next_header != -1:
        section = section[:next_header]
    rows: list[list[str]] = []
    header_skipped = False
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if not header_skipped:
            header_skipped = True
            continue
        if "---" in stripped or "*(none yet)*" in stripped:
            continue
        parts = [cell.strip() for cell in stripped.strip("|").split("|")]
        if parts:
            rows.append(parts)
    return rows


def normalize_cell(cell: str) -> str:
    return cell.replace("`", "").strip()


def gather_material_files(workspace_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in (workspace_dir / "materials").rglob("*"):
        if path.is_file() and path.name != ".gitkeep":
            files.append(path)
    return sorted(files)


def gather_note_files(workspace_dir: Path) -> list[Path]:
    notes_dir = workspace_dir / "notes" / "chapters"
    return sorted(
        path for path in notes_dir.glob("*.md") if path.is_file() and path.name != ".gitkeep"
    )


def gather_kind_ids(root: Path) -> set[str]:
    kind_ids: set[str] = set()
    templates_dir = root / "templates"
    if not templates_dir.is_dir():
        return kind_ids
    for path in templates_dir.iterdir():
        if path.is_dir() and (path / "kind.json").exists():
            kind_ids.add(path.name)
    return kind_ids


def audit_root(root: Path, report: Report) -> None:
    catalog_path = root / "registry" / "catalog.json"
    index_path = root / "registry" / "INDEX.md"
    templates_index_path = root / "templates" / "INDEX.md"
    catalog = load_json(catalog_path, report)
    index_text = read_text(index_path, report)
    templates_index_text = read_text(templates_index_path, report)
    kind_ids = gather_kind_ids(root)
    if not catalog:
        return

    subjects = catalog.get("subjects", [])
    if not subjects:
        report.info("No subjects registered.")
        return

    for subject in subjects:
        subject_path = root / subject["path"]
        if not subject_path.is_dir():
            report.error(f"Subject path missing: {subject['path']}")
            continue
        if subject["id"] not in index_text:
            report.warn(f"Registry index may be missing subject ID {subject['id']}")

        subject_json_path = subject_path / "subject.json"
        subject_index_path = subject_path / "INDEX.md"
        subject_json = load_json(subject_json_path, report)
        subject_index_text = read_text(subject_index_path, report)
        if subject_json:
            if subject_json.get("id") != subject["id"]:
                report.warn(f"subject.json ID mismatch for {subject['path']}")
            if subject_json.get("path") != subject["path"]:
                report.warn(f"subject.json path mismatch for {subject['path']}")

        for workspace in subject.get("workspaces", []):
            workspace_path = root / workspace["path"]
            if not workspace_path.is_dir():
                report.error(f"Workspace path missing: {workspace['path']}")
                continue
            if workspace["id"] not in index_text:
                report.warn(f"Registry index may be missing workspace ID {workspace['id']}")
            if workspace["id"] not in subject_index_text:
                report.warn(f"Subject index may be missing workspace ID {workspace['id']} in {subject['path']}")

            for required in [
                workspace_path / "CLAUDE.md",
                workspace_path / "PROFILE.md",
                workspace_path / "workspace.json",
                workspace_path / "indexes" / "INDEX.md",
                workspace_path / "memory" / "MEMORY.md",
                workspace_path / "skills" / "README.md",
            ]:
                if not required.exists():
                    report.error(f"Missing required workspace file: {required}")

            workspace_json = load_json(workspace_path / "workspace.json", report)
            if workspace_json:
                if workspace_json.get("workspace_id") != workspace["id"]:
                    report.warn(f"workspace.json ID mismatch in {workspace['path']}")
                if workspace_json.get("path") != workspace["path"]:
                    report.warn(f"workspace.json path mismatch in {workspace['path']}")
                if workspace_json.get("kind") != workspace["kind"]:
                    report.warn(f"workspace.json kind mismatch in {workspace['path']}")

            if workspace["kind"] not in kind_ids:
                report.warn(f"Workspace kind missing from templates: {workspace['kind']}")
            elif workspace["kind"] not in templates_index_text:
                report.warn(f"Kind index may be missing kind ID {workspace['kind']}")


def audit_workspace(workspace_dir: Path, report: Report) -> None:
    for required in [
        workspace_dir / "CLAUDE.md",
        workspace_dir / "PROFILE.md",
        workspace_dir / "workspace.json",
        workspace_dir / "indexes" / "INDEX.md",
        workspace_dir / "memory" / "MEMORY.md",
        workspace_dir / "skills" / "README.md",
    ]:
        if not required.exists():
            report.error(f"Missing required workspace file: {required}")

    workspace_json = load_json(workspace_dir / "workspace.json", report)
    index_text = read_text(workspace_dir / "indexes" / "INDEX.md", report)
    memory_text = read_text(workspace_dir / "memory" / "MEMORY.md", report)
    if not workspace_json:
        return

    allowed_workspace_keys = {
        "subject_id",
        "workspace_id",
        "workspace_title",
        "kind",
        "path",
        "status",
    }
    extra_keys = sorted(set(workspace_json) - allowed_workspace_keys)
    if extra_keys:
        report.warn(f"workspace.json has non-minimal keys: {', '.join(extra_keys)}")

    source_rows = parse_table_rows(index_text, "Source Inventory")
    note_rows = parse_table_rows(index_text, "Note Inventory")
    indexed_source_paths = {normalize_cell(row[4]) for row in source_rows if len(row) >= 5}
    indexed_note_paths = {normalize_cell(row[3]) for row in note_rows if len(row) >= 4}

    inbox_files = [
        path for path in (workspace_dir / "materials" / "inbox").rglob("*")
        if path.is_file() and path.name != ".gitkeep"
    ]
    if inbox_files:
        report.warn(f"{len(inbox_files)} file(s) still in materials/inbox/")

    for material_file in gather_material_files(workspace_dir):
        rel_path = material_file.relative_to(workspace_dir).as_posix()
        if rel_path not in indexed_source_paths:
            report.warn(f"Material not listed in Source Inventory: {rel_path}")

    for note_file in gather_note_files(workspace_dir):
        rel_path = note_file.relative_to(workspace_dir).as_posix()
        if rel_path not in indexed_note_paths and note_file.name not in index_text:
            report.warn(f"Note not listed in Note Inventory: {rel_path}")
        note_text = note_file.read_text(encoding="utf-8")
        if not SOURCE_ID_RE.search(note_text):
            report.warn(f"Note does not reference a source ID: {rel_path}")

        export_path = workspace_dir / "notes" / "exports" / f"{note_file.stem}.pdf"
        if not export_path.exists():
            report.warn(f"Missing PDF export for note: {rel_path}")
        elif export_path.stat().st_mtime < note_file.stat().st_mtime:
            report.warn(f"PDF export older than note: {export_path.relative_to(workspace_dir).as_posix()}")

    for row in source_rows:
        if len(row) >= 5:
            source_path = workspace_dir / normalize_cell(row[4])
            if not source_path.exists():
                report.warn(f"Indexed source path missing on disk: {normalize_cell(row[4])}")

    for row in note_rows:
        if len(row) >= 5:
            note_path = workspace_dir / normalize_cell(row[3])
            source_ids = normalize_cell(row[4])
            if not note_path.exists():
                report.warn(f"Indexed note path missing on disk: {normalize_cell(row[3])}")
            if not source_ids:
                report.warn(f"Note inventory row has empty source IDs: {normalize_cell(row[3])}")

    if len(memory_text.splitlines()) > 120 or len(memory_text) > 4000:
        report.warn("memory/MEMORY.md is getting long; keep it as short cache, not knowledge store.")


def print_report(report: Report) -> None:
    print(f"Audit target: {report.target}")
    for message in report.infos:
        print(f"INFO: {message}")
    for message in report.warnings:
        print(f"WARN: {message}")
    for message in report.errors:
        print(f"ERROR: {message}")
    print(
        f"Summary: {len(report.errors)} error(s), "
        f"{len(report.warnings)} warning(s), {len(report.infos)} info message(s)."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="repository root or a single workspace directory (default: current directory)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target = Path(args.path).expanduser().resolve()
    if not target.exists():
        raise SystemExit(f"Path does not exist: {target}")

    root = find_root(target)
    report = Report(target=target)

    if is_workspace_dir(target):
        audit_workspace(target, report)
    elif target == root:
        audit_root(root, report)
    else:
        report.error("Audit target must be the repository root or a workspace directory.")

    print_report(report)
    sys.exit(report.exit_code())


if __name__ == "__main__":
    main()
