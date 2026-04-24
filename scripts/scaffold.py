#!/usr/bin/env python3
"""
Create and maintain subject/workspace scaffolds for the local agent workspace.

Examples:
    uv run python scripts/scaffold.py add-subject CSCI "Computer Science"
    uv run python scripts/scaffold.py add-workspace CSCI RL "Reinforcement Learning" --kind course
    uv run python scripts/scaffold.py add-course CSCI ARIN5204 "Reinforcement Learning"
    uv run python scripts/scaffold.py add-kind health_coach --name "Health Coach" --description "Health coaching workspace"
    uv run python scripts/scaffold.py list
    uv run python scripts/scaffold.py list-kinds
    uv run python scripts/scaffold.py rebuild
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "registry"
CATALOG_PATH = REGISTRY_DIR / "catalog.json"
TEMPLATES_DIR = ROOT / "templates"
TEMPLATES_INDEX_PATH = TEMPLATES_DIR / "INDEX.md"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sanitize_id(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "", value.strip())
    if not clean:
        raise ValueError("identifier must contain letters, numbers, '-' or '_'")
    return clean.upper()


def sanitize_kind_id(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "", value.strip())
    if not clean:
        raise ValueError("kind identifier must contain letters, numbers, '-' or '_'")
    return clean.lower()


def sanitize_title(value: str) -> str:
    clean = re.sub(r"\s+", " ", value.strip())
    clean = clean.replace("/", "-")
    if not clean:
        raise ValueError("title cannot be empty")
    return clean


def load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        return {"version": 2, "updated_at": None, "subjects": []}
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def save_catalog(catalog: dict) -> None:
    catalog["version"] = 2
    catalog["updated_at"] = now_iso()
    CATALOG_PATH.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def render_template(template_path: Path, replacements: dict[str, str]) -> str:
    text = template_path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def touch_keep(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)


def render_directory(template_dir: Path, dest_dir: Path, replacements: dict[str, str]) -> None:
    for template_path in template_dir.rglob("*"):
        if not template_path.is_file():
            continue
        if template_path.name == "kind.json":
            continue
        relative_path = template_path.relative_to(template_dir)
        output_path = dest_dir / relative_path
        write_file(output_path, render_template(template_path, replacements))


def title_from_kind_id(kind_id: str) -> str:
    return kind_id.replace("_", " ").replace("-", " ").title()


def load_kind_metadata(kind_id: str) -> dict:
    kind_id = sanitize_kind_id(kind_id)
    kind_dir = TEMPLATES_DIR / kind_id
    if not kind_dir.is_dir():
        raise SystemExit(f"unknown kind: {kind_id}")
    kind_json_path = kind_dir / "kind.json"
    if not kind_json_path.exists():
        raise SystemExit(f"kind metadata missing: {kind_json_path}")
    metadata = json.loads(kind_json_path.read_text(encoding="utf-8"))
    metadata.setdefault("id", kind_id)
    metadata.setdefault("name", title_from_kind_id(kind_id))
    metadata.setdefault("description", "")
    metadata.setdefault("best_for", [])
    metadata.setdefault("copied_from", None)
    metadata["path"] = f"templates/{kind_id}"
    return metadata


def iter_kind_metadata() -> list[dict]:
    kinds: list[dict] = []
    for path in sorted(TEMPLATES_DIR.iterdir()):
        if not path.is_dir():
            continue
        kind_json_path = path / "kind.json"
        if not kind_json_path.exists():
            continue
        kinds.append(load_kind_metadata(path.name))
    return kinds


def find_subject(catalog: dict, subject_id: str) -> dict | None:
    for subject in catalog["subjects"]:
        if subject["id"] == subject_id:
            return subject
    return None


def build_templates_index() -> str:
    kinds = iter_kind_metadata()
    lines = [
        "# Kind Index",
        "",
        "This file is maintained from `templates/*/kind.json`.",
        "",
        "## Available Kinds",
        "",
        "| Kind ID | Name | Description | Copied From | Path |",
        "| --- | --- | --- | --- | --- |",
    ]
    if kinds:
        for kind in kinds:
            lines.append(
                f"| {kind['id']} | {kind['name']} | {kind['description']} | "
                f"{kind.get('copied_from') or ''} | `{kind['path']}` |"
            )
    else:
        lines.append("| *(none yet)* |  |  |  |  |")
    lines.append("")
    return "\n".join(lines)


def build_registry_index(catalog: dict) -> str:
    lines = [
        "# Registry Index",
        "",
        "This file is maintained from `registry/catalog.json`.",
        "",
        "## Subjects",
        "",
        "| Subject ID | Name | Workspaces | Path |",
        "| --- | --- | --- | --- |",
    ]
    if catalog["subjects"]:
        for subject in sorted(catalog["subjects"], key=lambda item: item["id"]):
            lines.append(
                f"| {subject['id']} | {subject['name']} | "
                f"{len(subject['workspaces'])} | `{subject['path']}` |"
            )
    else:
        lines.append("| *(none yet)* |  | 0 |  |")

    lines.extend(
        [
            "",
            "## Workspaces",
            "",
            "| Subject | Workspace ID | Title | Kind | Status | Path |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )

    workspaces = []
    for subject in catalog["subjects"]:
        for workspace in subject["workspaces"]:
            workspaces.append((subject["id"], workspace))
    if workspaces:
        for subject_id, workspace in sorted(workspaces, key=lambda item: (item[0], item[1]["id"])):
            lines.append(
                f"| {subject_id} | {workspace['id']} | {workspace['title']} | "
                f"{workspace['kind']} | {workspace['status']} | `{workspace['path']}` |"
            )
    else:
        lines.append("| *(none yet)* |  |  |  |  |  |")
    lines.append("")
    return "\n".join(lines)


def build_subject_index(subject: dict) -> str:
    lines = [
        f"# Subject Index — {subject['id']}",
        "",
        "This file is maintained from `subject.json`.",
        "",
        "## Summary",
        "",
        f"- Subject ID: `{subject['id']}`",
        f"- Subject name: `{subject['name']}`",
        f"- Workspaces: {len(subject['workspaces'])}",
        "",
        "## Workspaces",
        "",
        "| Workspace ID | Title | Kind | Status | Path |",
        "| --- | --- | --- | --- | --- |",
    ]
    if subject["workspaces"]:
        for workspace in sorted(subject["workspaces"], key=lambda item: item["id"]):
            relative_path = f"workspaces/{workspace['folder_name']}"
            lines.append(
                f"| {workspace['id']} | {workspace['title']} | {workspace['kind']} | "
                f"{workspace['status']} | `{relative_path}` |"
            )
    else:
        lines.append("| *(none yet)* |  |  |  |  |")
    lines.append("")
    return "\n".join(lines)


def rebuild_indexes(catalog: dict) -> None:
    write_file(REGISTRY_DIR / "INDEX.md", build_registry_index(catalog))
    write_file(TEMPLATES_INDEX_PATH, build_templates_index())
    for subject in catalog["subjects"]:
        subject_dir = ROOT / subject["path"]
        subject_meta = {
            "id": subject["id"],
            "name": subject["name"],
            "path": subject["path"],
            "workspace_count": len(subject["workspaces"]),
            "workspaces": subject["workspaces"],
            "updated_at": catalog["updated_at"],
        }
        write_file(
            subject_dir / "subject.json",
            json.dumps(subject_meta, indent=2, ensure_ascii=False) + "\n",
        )
        write_file(subject_dir / "INDEX.md", build_subject_index(subject))


def add_subject(args: argparse.Namespace) -> None:
    subject_id = sanitize_id(args.subject_id)
    subject_name = sanitize_title(args.subject_name)
    catalog = load_catalog()
    if find_subject(catalog, subject_id):
        raise SystemExit(f"subject already exists: {subject_id}")

    subject_path = f"subjects/{subject_id}"
    subject_dir = ROOT / subject_path
    (subject_dir / "workspaces").mkdir(parents=True, exist_ok=True)
    touch_keep(subject_dir / "workspaces" / ".gitkeep")

    catalog["subjects"].append(
        {
            "id": subject_id,
            "name": subject_name,
            "path": subject_path,
            "workspaces": [],
        }
    )
    save_catalog(catalog)
    rebuild_indexes(catalog)
    print(f"Created subject: {subject_id} -> {subject_path}")


def add_kind(args: argparse.Namespace) -> None:
    kind_id = sanitize_kind_id(args.kind_id)
    from_kind = sanitize_kind_id(args.from_kind)
    kind_name = sanitize_title(args.name) if args.name else title_from_kind_id(kind_id)
    kind_description = args.description.strip() if args.description else f"Template cloned from `{from_kind}`."

    source_dir = TEMPLATES_DIR / from_kind
    if not source_dir.is_dir():
        raise SystemExit(f"unknown source kind: {from_kind}")

    target_dir = TEMPLATES_DIR / kind_id
    if target_dir.exists():
        raise SystemExit(f"kind already exists: {kind_id}")

    shutil.copytree(source_dir, target_dir)
    kind_meta = {
        "id": kind_id,
        "name": kind_name,
        "description": kind_description,
        "best_for": [],
        "copied_from": from_kind,
    }
    write_file(target_dir / "kind.json", json.dumps(kind_meta, indent=2, ensure_ascii=False) + "\n")

    catalog = load_catalog()
    rebuild_indexes(catalog)
    print(f"Created kind: {kind_id} -> templates/{kind_id}")


def add_workspace(args: argparse.Namespace) -> None:
    subject_id = sanitize_id(args.subject_id)
    workspace_id = sanitize_id(args.workspace_id)
    workspace_title = sanitize_title(args.workspace_title)
    kind_id = sanitize_kind_id(args.kind)

    catalog = load_catalog()
    subject = find_subject(catalog, subject_id)
    if not subject:
        raise SystemExit(f"unknown subject: {subject_id}")
    if any(workspace["id"] == workspace_id for workspace in subject["workspaces"]):
        raise SystemExit(f"workspace already exists in {subject_id}: {workspace_id}")

    kind = load_kind_metadata(kind_id)
    kind_dir = ROOT / kind["path"]
    folder_name = f"{workspace_id} {workspace_title}"
    workspace_path = f"{subject['path']}/workspaces/{folder_name}"
    workspace_dir = ROOT / workspace_path

    for directory in [
        workspace_dir / "materials" / "inbox",
        workspace_dir / "materials" / "lectures",
        workspace_dir / "materials" / "assignments",
        workspace_dir / "materials" / "references",
        workspace_dir / "notes" / "chapters",
        workspace_dir / "notes" / "exports",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    for keep_path in [
        workspace_dir / "materials" / "inbox" / ".gitkeep",
        workspace_dir / "materials" / "lectures" / ".gitkeep",
        workspace_dir / "materials" / "assignments" / ".gitkeep",
        workspace_dir / "materials" / "references" / ".gitkeep",
        workspace_dir / "notes" / "chapters" / ".gitkeep",
        workspace_dir / "notes" / "exports" / ".gitkeep",
    ]:
        touch_keep(keep_path)

    replacements = {
        "SUBJECT_ID": subject_id,
        "WORKSPACE_ID": workspace_id,
        "WORKSPACE_TITLE": workspace_title,
        "WORKSPACE_PATH": workspace_path,
        "KIND_ID": kind_id,
        "KIND_NAME": kind["name"],
    }
    render_directory(kind_dir, workspace_dir, replacements)

    workspace_meta = {
        "subject_id": subject_id,
        "workspace_id": workspace_id,
        "workspace_title": workspace_title,
        "kind": kind_id,
        "path": workspace_path,
        "status": "new",
    }
    write_file(
        workspace_dir / "workspace.json",
        json.dumps(workspace_meta, indent=2, ensure_ascii=False) + "\n",
    )

    subject["workspaces"].append(
        {
            "id": workspace_id,
            "title": workspace_title,
            "kind": kind_id,
            "status": "new",
            "path": workspace_path,
            "folder_name": folder_name,
        }
    )
    save_catalog(catalog)
    rebuild_indexes(catalog)
    print(f"Created workspace: {workspace_id} -> {workspace_path}")


def add_course(args: argparse.Namespace) -> None:
    add_workspace(
        argparse.Namespace(
            subject_id=args.subject_id,
            workspace_id=args.course_id,
            workspace_title=args.course_title,
            kind="course",
        )
    )


def list_catalog(_: argparse.Namespace) -> None:
    catalog = load_catalog()
    if not catalog["subjects"]:
        print("No subjects registered.")
        return
    for subject in sorted(catalog["subjects"], key=lambda item: item["id"]):
        print(f"{subject['id']}  {subject['name']}  ({len(subject['workspaces'])} workspace(s))")
        for workspace in sorted(subject["workspaces"], key=lambda item: item["id"]):
            print(
                f"  - {workspace['id']}  {workspace['title']}  "
                f"[{workspace['kind']}, {workspace['status']}]"
            )


def list_kinds(_: argparse.Namespace) -> None:
    kinds = iter_kind_metadata()
    if not kinds:
        print("No kinds registered.")
        return
    for kind in kinds:
        print(f"{kind['id']}  {kind['name']}")
        if kind["description"]:
            print(f"  {kind['description']}")


def rebuild(_: argparse.Namespace) -> None:
    catalog = load_catalog()
    save_catalog(catalog)
    rebuild_indexes(catalog)
    print("Rebuilt registry, subject indexes, and kind index.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_subject_parser = subparsers.add_parser("add-subject", help="create a subject container")
    add_subject_parser.add_argument("subject_id")
    add_subject_parser.add_argument("subject_name")
    add_subject_parser.set_defaults(func=add_subject)

    add_workspace_parser = subparsers.add_parser("add-workspace", help="create a workspace")
    add_workspace_parser.add_argument("subject_id")
    add_workspace_parser.add_argument("workspace_id")
    add_workspace_parser.add_argument("workspace_title")
    add_workspace_parser.add_argument("--kind", default="course")
    add_workspace_parser.set_defaults(func=add_workspace)

    add_course_parser = subparsers.add_parser(
        "add-course", help="create an academic workspace using the default `course` kind"
    )
    add_course_parser.add_argument("subject_id")
    add_course_parser.add_argument("course_id")
    add_course_parser.add_argument("course_title")
    add_course_parser.set_defaults(func=add_course)

    add_kind_parser = subparsers.add_parser("add-kind", help="clone a new kind template")
    add_kind_parser.add_argument("kind_id")
    add_kind_parser.add_argument("--name")
    add_kind_parser.add_argument("--description")
    add_kind_parser.add_argument("--from-kind", default="course")
    add_kind_parser.set_defaults(func=add_kind)

    list_parser = subparsers.add_parser("list", help="print the current catalog")
    list_parser.set_defaults(func=list_catalog)

    list_kinds_parser = subparsers.add_parser("list-kinds", help="print available kinds")
    list_kinds_parser.set_defaults(func=list_kinds)

    rebuild_parser = subparsers.add_parser("rebuild", help="rewrite derived index files")
    rebuild_parser.set_defaults(func=rebuild)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
