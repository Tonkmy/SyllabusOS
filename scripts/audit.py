#!/usr/bin/env python3
"""
Run a lightweight consistency audit for the local agent workspace.

Examples:
    uv run python scripts/audit.py
    uv run python scripts/audit.py subjects/CSCI/ARIN5204 Reinforcement Learning
    uv run python scripts/audit.py subjects/HEALTH
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
VALID_MODES = {"collection", "singleton"}


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


def gather_material_files(space_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in (space_dir / "materials").rglob("*"):
        if path.is_file() and path.name != ".gitkeep":
            files.append(path)
    return sorted(files)


def gather_note_files(space_dir: Path) -> list[Path]:
    notes_dir = space_dir / "notes" / "chapters"
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


def normalize_entry(raw_entry: dict, subject_id: str, subject_path: str) -> dict:
    entry_id = raw_entry["id"]
    title = raw_entry.get("title", entry_id)
    folder_name = raw_entry.get("folder_name") or f"{entry_id} {title}"
    return {
        "id": entry_id,
        "title": title,
        "status": raw_entry.get("status", "new"),
        "path": raw_entry.get("path", f"{subject_path}/{folder_name}"),
        "folder_name": folder_name,
    }


def normalize_catalog(catalog: dict) -> dict:
    subjects = []
    for raw_subject in catalog.get("subjects", []):
        subject_id = raw_subject["id"]
        subject_path = raw_subject.get("path", f"subjects/{subject_id}")
        raw_entries = raw_subject.get("entries", raw_subject.get("workspaces", []))
        subjects.append(
            {
                "id": subject_id,
                "name": raw_subject.get("name", subject_id),
                "kind": raw_subject.get("kind", "course"),
                "mode": raw_subject.get("mode", "collection"),
                "path": subject_path,
                "status": raw_subject.get("status", "new"),
                "entries": [normalize_entry(entry, subject_id, subject_path) for entry in raw_entries],
            }
        )
    return {
        "version": catalog.get("version", 3),
        "updated_at": catalog.get("updated_at"),
        "subjects": subjects,
    }


def validate_space_files(space_dir: Path, report: Report) -> None:
    for required in [
        space_dir / "CLAUDE.md",
        space_dir / "PROFILE.md",
        space_dir / "workspace.json",
        space_dir / "indexes" / "INDEX.md",
        space_dir / "memory" / "MEMORY.md",
        space_dir / "skills" / "README.md",
    ]:
        if not required.exists():
            report.error(f"Missing required space file: {required}")


def audit_root(root: Path, report: Report) -> None:
    catalog_path = root / "registry" / "catalog.json"
    index_path = root / "registry" / "INDEX.md"
    templates_index_path = root / "templates" / "INDEX.md"
    raw_catalog = load_json(catalog_path, report)
    index_text = read_text(index_path, report)
    templates_index_text = read_text(templates_index_path, report)
    kind_ids = gather_kind_ids(root)
    if not raw_catalog:
        return

    catalog = normalize_catalog(raw_catalog)
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
        if subject["kind"] not in kind_ids:
            report.warn(f"Subject kind missing from templates: {subject['kind']}")
        elif subject["kind"] not in templates_index_text:
            report.warn(f"Kind index may be missing kind ID {subject['kind']}")
        if subject["mode"] not in VALID_MODES:
            report.error(f"Invalid subject mode in catalog: {subject['id']} -> {subject['mode']}")

        subject_json_path = subject_path / "subject.json"
        subject_index_path = subject_path / "INDEX.md"
        subject_json = load_json(subject_json_path, report)
        subject_index_text = read_text(subject_index_path, report)
        if subject_json:
            if subject_json.get("id") != subject["id"]:
                report.warn(f"subject.json ID mismatch for {subject['path']}")
            if subject_json.get("path") != subject["path"]:
                report.warn(f"subject.json path mismatch for {subject['path']}")
            if subject_json.get("kind") != subject["kind"]:
                report.warn(f"subject.json kind mismatch for {subject['path']}")
            if subject_json.get("mode") != subject["mode"]:
                report.warn(f"subject.json mode mismatch for {subject['path']}")

        if subject["mode"] == "singleton":
            validate_space_files(subject_path, report)
            workspace_json = load_json(subject_path / "workspace.json", report)
            if workspace_json:
                if workspace_json.get("workspace_id") != subject["id"]:
                    report.warn(f"workspace.json ID mismatch in singleton subject {subject['path']}")
                if workspace_json.get("path") != subject["path"]:
                    report.warn(f"workspace.json path mismatch in singleton subject {subject['path']}")
                if workspace_json.get("kind") != subject["kind"]:
                    report.warn(f"workspace.json kind mismatch in singleton subject {subject['path']}")
            continue

        for entry in subject.get("entries", []):
            entry_path = root / entry["path"]
            if not entry_path.is_dir():
                report.error(f"Child space path missing: {entry['path']}")
                continue
            if entry["id"] not in index_text:
                report.warn(f"Registry index may be missing child ID {entry['id']}")
            if entry["id"] not in subject_index_text:
                report.warn(f"Subject index may be missing child ID {entry['id']} in {subject['path']}")

            validate_space_files(entry_path, report)
            workspace_json = load_json(entry_path / "workspace.json", report)
            if workspace_json:
                if workspace_json.get("workspace_id") != entry["id"]:
                    report.warn(f"workspace.json ID mismatch in {entry['path']}")
                if workspace_json.get("path") != entry["path"]:
                    report.warn(f"workspace.json path mismatch in {entry['path']}")
                if workspace_json.get("kind") != subject["kind"]:
                    report.warn(f"workspace.json kind mismatch in {entry['path']}")


def audit_workspace(space_dir: Path, report: Report) -> None:
    validate_space_files(space_dir, report)

    workspace_json = load_json(space_dir / "workspace.json", report)
    index_text = read_text(space_dir / "indexes" / "INDEX.md", report)
    memory_text = read_text(space_dir / "memory" / "MEMORY.md", report)
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

    inbox_dir = space_dir / "materials" / "inbox"
    inbox_files = [path for path in inbox_dir.rglob("*") if path.is_file() and path.name != ".gitkeep"]
    if inbox_files:
        report.warn(f"{len(inbox_files)} file(s) still in materials/inbox/")

    for material_file in gather_material_files(space_dir):
        rel_path = material_file.relative_to(space_dir).as_posix()
        if rel_path not in indexed_source_paths:
            report.warn(f"Material not listed in Source Inventory: {rel_path}")

    for note_file in gather_note_files(space_dir):
        rel_path = note_file.relative_to(space_dir).as_posix()
        if rel_path not in indexed_note_paths and note_file.name not in index_text:
            report.warn(f"Note not listed in Note Inventory: {rel_path}")
        note_text = note_file.read_text(encoding="utf-8")
        if not SOURCE_ID_RE.search(note_text):
            report.warn(f"Note does not reference a source ID: {rel_path}")

        export_path = space_dir / "notes" / "exports" / f"{note_file.stem}.pdf"
        if not export_path.exists():
            report.warn(f"Missing PDF export for note: {rel_path}")
        elif export_path.stat().st_mtime < note_file.stat().st_mtime:
            report.warn(f"PDF export older than note: {export_path.relative_to(space_dir).as_posix()}")

    for row in source_rows:
        if len(row) >= 5:
            source_path = space_dir / normalize_cell(row[4])
            if not source_path.exists():
                report.warn(f"Indexed source path missing on disk: {normalize_cell(row[4])}")

    for row in note_rows:
        if len(row) >= 5:
            note_path = space_dir / normalize_cell(row[3])
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
        help="repository root or a single active space directory (default: current directory)",
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
        report.error("Audit target must be the repository root or a single active space directory.")

    print_report(report)
    sys.exit(report.exit_code())


if __name__ == "__main__":
    main()
