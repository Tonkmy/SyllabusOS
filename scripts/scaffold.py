#!/usr/bin/env python3
"""
Create and maintain subject-based scaffolds for the local agent workspace.

Examples:
    uv run python scripts/scaffold.py add-subject CSCI "Computer Science"
    uv run python scripts/scaffold.py add-subject HEALTH "Health" --kind health_coach --mode singleton
    uv run python scripts/scaffold.py add-workspace CSCI RL "Reinforcement Learning"
    uv run python scripts/scaffold.py add-course CSCI ARIN5204 "Reinforcement Learning"
    uv run python scripts/scaffold.py add-kind health_coach --name "Health Coach" --description "Health coaching subject/workspace"
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
VALID_MODES = {"collection", "singleton"}


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


def sanitize_mode(value: str) -> str:
    clean = value.strip().lower()
    if clean not in VALID_MODES:
        raise ValueError("mode must be 'collection' or 'singleton'")
    return clean


def title_from_kind_id(kind_id: str) -> str:
    return kind_id.replace("_", " ").replace("-", " ").title()


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
        if template_path.name in {"kind.json", ".DS_Store"}:
            continue
        relative_path = template_path.relative_to(template_dir)
        output_path = dest_dir / relative_path
        write_file(output_path, render_template(template_path, replacements))


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


def normalize_entry(raw_entry: dict, subject_id: str, subject_path: str) -> dict:
    entry_id = sanitize_id(raw_entry["id"])
    title = sanitize_title(raw_entry.get("title", entry_id))
    folder_name = raw_entry.get("folder_name") or f"{entry_id} {title}"
    return {
        "id": entry_id,
        "title": title,
        "status": raw_entry.get("status", "new"),
        "path": raw_entry.get("path", f"{subject_path}/{folder_name}"),
        "folder_name": folder_name,
    }


def normalize_subject(raw_subject: dict) -> dict:
    subject_id = sanitize_id(raw_subject["id"])
    subject_name = sanitize_title(raw_subject.get("name", subject_id))
    subject_path = raw_subject.get("path", f"subjects/{subject_id}")

    if "entries" in raw_subject:
        raw_entries = raw_subject.get("entries", [])
        inferred_kind = raw_subject.get("kind", "course")
    else:
        raw_entries = raw_subject.get("workspaces", [])
        kinds = {item.get("kind", "course") for item in raw_entries}
        inferred_kind = next(iter(kinds)) if len(kinds) == 1 else "course"

    kind_id = sanitize_kind_id(raw_subject.get("kind", inferred_kind))
    mode = sanitize_mode(raw_subject.get("mode", "collection"))

    return {
        "id": subject_id,
        "name": subject_name,
        "kind": kind_id,
        "mode": mode,
        "path": subject_path,
        "status": raw_subject.get("status", "new" if mode == "singleton" else "active"),
        "entries": [normalize_entry(item, subject_id, subject_path) for item in raw_entries],
    }


def normalize_catalog(raw: dict) -> dict:
    catalog = {
        "version": 3,
        "updated_at": raw.get("updated_at"),
        "subjects": [],
    }
    for raw_subject in raw.get("subjects", []):
        catalog["subjects"].append(normalize_subject(raw_subject))
    return catalog


def load_catalog() -> dict:
    if not CATALOG_PATH.exists():
        return {"version": 3, "updated_at": None, "subjects": []}
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return normalize_catalog(raw)


def save_catalog(catalog: dict) -> None:
    catalog["version"] = 3
    catalog["updated_at"] = now_iso()
    CATALOG_PATH.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


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


def iter_active_spaces(catalog: dict) -> list[tuple[dict, dict]]:
    spaces: list[tuple[dict, dict]] = []
    for subject in catalog["subjects"]:
        if subject["mode"] == "singleton":
            spaces.append(
                (
                    subject,
                    {
                        "id": subject["id"],
                        "title": subject["name"],
                        "status": subject.get("status", "new"),
                        "path": subject["path"],
                        "folder_name": Path(subject["path"]).name,
                    },
                )
            )
        else:
            for entry in subject["entries"]:
                spaces.append((subject, entry))
    return spaces


def build_registry_index(catalog: dict) -> str:
    lines = [
        "# Registry Index",
        "",
        "This file is maintained from `registry/catalog.json`.",
        "",
        "## Subjects",
        "",
        "| Subject ID | Name | Kind | Mode | Children | Path |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    if catalog["subjects"]:
        for subject in sorted(catalog["subjects"], key=lambda item: item["id"]):
            child_count = 1 if subject["mode"] == "singleton" else len(subject["entries"])
            lines.append(
                f"| {subject['id']} | {subject['name']} | {subject['kind']} | "
                f"{subject['mode']} | {child_count} | `{subject['path']}` |"
            )
    else:
        lines.append("| *(none yet)* |  |  |  | 0 |  |")

    lines.extend(
        [
            "",
            "## Active Spaces",
            "",
            "| Subject | Space ID | Title | Kind | Status | Path |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )

    spaces = iter_active_spaces(catalog)
    if spaces:
        for subject, entry in sorted(spaces, key=lambda item: (item[0]["id"], item[1]["id"])):
            lines.append(
                f"| {subject['id']} | {entry['id']} | {entry['title']} | "
                f"{subject['kind']} | {entry['status']} | `{entry['path']}` |"
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
        f"- Kind: `{subject['kind']}`",
        f"- Mode: `{subject['mode']}`",
    ]

    if subject["mode"] == "singleton":
        lines.extend(
            [
                f"- Active path: `{subject['path']}`",
                f"- Status: `{subject.get('status', 'new')}`",
                "",
                "## Active Space",
                "",
                "This subject is itself the active space.",
                "",
                "- Open this subject folder directly when you want the agent to work.",
                "- Root files such as `CLAUDE.md`, `PROFILE.md`, `indexes/`, and `notes/` live here.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            f"- Child spaces: {len(subject['entries'])}",
            "",
            "## Child Spaces",
            "",
            "| Space ID | Title | Status | Path |",
            "| --- | --- | --- | --- |",
        ]
    )
    if subject["entries"]:
        for entry in sorted(subject["entries"], key=lambda item: item["id"]):
            lines.append(
                f"| {entry['id']} | {entry['title']} | {entry['status']} | "
                f"`{entry['folder_name']}` |"
            )
    else:
        lines.append("| *(none yet)* |  |  |  |")
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
            "kind": subject["kind"],
            "mode": subject["mode"],
            "path": subject["path"],
            "status": subject.get("status", "new" if subject["mode"] == "singleton" else "active"),
            "entry_count": 1 if subject["mode"] == "singleton" else len(subject["entries"]),
            "entries": subject["entries"],
            "updated_at": catalog["updated_at"],
        }
        write_file(
            subject_dir / "subject.json",
            json.dumps(subject_meta, indent=2, ensure_ascii=False) + "\n",
        )
        write_file(subject_dir / "INDEX.md", build_subject_index(subject))


def ensure_space_dirs(space_dir: Path) -> None:
    for directory in [
        space_dir / "materials" / "inbox",
        space_dir / "materials" / "lectures",
        space_dir / "materials" / "assignments",
        space_dir / "materials" / "references",
        space_dir / "notes" / "chapters",
        space_dir / "notes" / "exports",
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    for keep_path in [
        space_dir / "materials" / "inbox" / ".gitkeep",
        space_dir / "materials" / "lectures" / ".gitkeep",
        space_dir / "materials" / "assignments" / ".gitkeep",
        space_dir / "materials" / "references" / ".gitkeep",
        space_dir / "notes" / "chapters" / ".gitkeep",
        space_dir / "notes" / "exports" / ".gitkeep",
    ]:
        touch_keep(keep_path)


def scaffold_space(
    *,
    subject_id: str,
    subject_name: str,
    kind_id: str,
    space_id: str,
    space_title: str,
    space_path: str,
    space_dir: Path,
) -> None:
    kind = load_kind_metadata(kind_id)
    kind_dir = ROOT / kind["path"]
    ensure_space_dirs(space_dir)

    replacements = {
        "SUBJECT_ID": subject_id,
        "WORKSPACE_ID": space_id,
        "WORKSPACE_TITLE": space_title,
        "WORKSPACE_PATH": space_path,
        "KIND_ID": kind_id,
        "KIND_NAME": kind["name"],
    }
    render_directory(kind_dir, space_dir, replacements)

    workspace_meta = {
        "subject_id": subject_id,
        "workspace_id": space_id,
        "workspace_title": space_title,
        "kind": kind_id,
        "path": space_path,
        "status": "new",
    }
    write_file(
        space_dir / "workspace.json",
        json.dumps(workspace_meta, indent=2, ensure_ascii=False) + "\n",
    )


def add_subject(args: argparse.Namespace) -> None:
    subject_id = sanitize_id(args.subject_id)
    subject_name = sanitize_title(args.subject_name)
    kind_id = sanitize_kind_id(args.kind)
    mode = sanitize_mode(args.mode)

    catalog = load_catalog()
    if find_subject(catalog, subject_id):
        raise SystemExit(f"subject already exists: {subject_id}")

    load_kind_metadata(kind_id)

    subject_path = f"subjects/{subject_id}"
    subject_dir = ROOT / subject_path
    subject_dir.mkdir(parents=True, exist_ok=True)

    subject_record = {
        "id": subject_id,
        "name": subject_name,
        "kind": kind_id,
        "mode": mode,
        "path": subject_path,
        "status": "new" if mode == "singleton" else "active",
        "entries": [],
    }

    if mode == "singleton":
        scaffold_space(
            subject_id=subject_id,
            subject_name=subject_name,
            kind_id=kind_id,
            space_id=subject_id,
            space_title=subject_name,
            space_path=subject_path,
            space_dir=subject_dir,
        )

    catalog["subjects"].append(subject_record)
    save_catalog(catalog)
    rebuild_indexes(catalog)
    print(f"Created subject: {subject_id} -> {subject_path} [{kind_id}, {mode}]")


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

    catalog = load_catalog()
    subject = find_subject(catalog, subject_id)
    if not subject:
        raise SystemExit(f"unknown subject: {subject_id}")
    if subject["mode"] != "collection":
        raise SystemExit(f"subject {subject_id} is a singleton subject; open it directly instead of adding child spaces")
    if any(entry["id"] == workspace_id for entry in subject["entries"]):
        raise SystemExit(f"space already exists in {subject_id}: {workspace_id}")

    subject_kind = subject["kind"]
    requested_kind = sanitize_kind_id(args.kind) if args.kind else subject_kind
    if requested_kind != subject_kind:
        raise SystemExit(
            f"subject {subject_id} uses kind `{subject_kind}`; child spaces under this subject must use the same kind"
        )

    folder_name = f"{workspace_id} {workspace_title}"
    workspace_path = f"{subject['path']}/{folder_name}"
    workspace_dir = ROOT / workspace_path

    scaffold_space(
        subject_id=subject_id,
        subject_name=subject["name"],
        kind_id=subject_kind,
        space_id=workspace_id,
        space_title=workspace_title,
        space_path=workspace_path,
        space_dir=workspace_dir,
    )

    subject["entries"].append(
        {
            "id": workspace_id,
            "title": workspace_title,
            "status": "new",
            "path": workspace_path,
            "folder_name": folder_name,
        }
    )
    save_catalog(catalog)
    rebuild_indexes(catalog)
    print(f"Created child space: {workspace_id} -> {workspace_path} [{subject_kind}]")


def add_course(args: argparse.Namespace) -> None:
    catalog = load_catalog()
    subject_id = sanitize_id(args.subject_id)
    subject = find_subject(catalog, subject_id)
    if not subject:
        raise SystemExit(f"unknown subject: {subject_id}")
    if subject["kind"] != "course" or subject["mode"] != "collection":
        raise SystemExit(f"subject {subject_id} is not a course collection")

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
        if subject["mode"] == "singleton":
            print(f"{subject['id']}  {subject['name']}  [{subject['kind']}, singleton]")
        else:
            print(
                f"{subject['id']}  {subject['name']}  "
                f"[{subject['kind']}, collection] ({len(subject['entries'])} child space(s))"
            )
            for entry in sorted(subject["entries"], key=lambda item: item["id"]):
                print(f"  - {entry['id']}  {entry['title']}  [{entry['status']}]")


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

    add_subject_parser = subparsers.add_parser("add-subject", help="create a subject")
    add_subject_parser.add_argument("subject_id")
    add_subject_parser.add_argument("subject_name")
    add_subject_parser.add_argument("--kind", default="course")
    add_subject_parser.add_argument("--mode", default="collection", choices=sorted(VALID_MODES))
    add_subject_parser.set_defaults(func=add_subject)

    add_workspace_parser = subparsers.add_parser(
        "add-workspace",
        help="create a child space under a collection subject using that subject's kind",
    )
    add_workspace_parser.add_argument("subject_id")
    add_workspace_parser.add_argument("workspace_id")
    add_workspace_parser.add_argument("workspace_title")
    add_workspace_parser.add_argument("--kind")
    add_workspace_parser.set_defaults(func=add_workspace)

    add_course_parser = subparsers.add_parser(
        "add-course",
        help="create a course folder under a subject whose kind is `course` and mode is `collection`",
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
