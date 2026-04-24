# Architecture

## Design Principle

This template optimizes agent performance by externalizing state into small files.
The main improvement is not a larger prompt or a more complicated framework. It is a stricter retrieval order.
The rules stay intentionally light because the workspace is designed for strong local LLMs.
Kinds let the registrar reuse or create leaf workspace shapes without adding more agent layers.

## Retrieval Order

### Root
1. `registry/catalog.json`
2. `registry/INDEX.md`
3. if workspace shape matters: `templates/INDEX.md`
4. only then the folder tree

### Subject Container
1. `subject.json`
2. `INDEX.md`
3. only then the workspace list under `workspaces/`

### Workspace
1. `workspace.json`
2. `PROFILE.md` if present
3. `indexes/INDEX.md`
4. `memory/MEMORY.md`
5. relevant `skills/*.md` only when the task needs them
6. the smallest relevant set of files in `notes/chapters/`
7. raw files in `materials/` only when necessary

## Why This Works

- `catalog.json` is the global directory of record.
- `templates/INDEX.md` is the kind directory of record.
- `INDEX.md` files are human-readable summaries that reduce tree-scanning.
- `MEMORY.md` stays short because it stores only stable cache, not transcripts.
- `notes/chapters/` becomes the default retrieval layer for teaching and Q&A.

## File Roles

### `registry/catalog.json`
Machine-readable registry of subjects and workspaces.

### `templates/INDEX.md`
Human-readable list of available kinds.

### `subject.json`
Machine-readable summary for one subject.

### `kind.json`
Machine-readable summary for one kind template.

### `workspace.json`
Machine-readable summary for one workspace.

### `PROFILE.md`
Workspace-local customization for tone, goals, special rules, and custom features.

### `indexes/INDEX.md`
Canonical workspace map plus source and note inventory for a workspace.

### `memory/MEMORY.md`
Short reusable cache for future sessions.

### `skills/`
Small optional task modules that keep `CLAUDE.md` short and let one workspace add specialized behavior without changing the repo-wide core.

## Intended Agent Behavior

- Root registrar creates structure, updates subject indexes and kind indexes, and routes work.
- Subject folders are passive namespaces, not independent agents.
- Leaf workspace agents ingest materials, update indexes, write notes, and answer questions according to their kind.
- Local customization lives in `PROFILE.md` and `skills/`, not in the registrar.

## Why There Is No Heavy Agent Framework

For a repo-first workflow, hidden runtime graphs are fragile unless they write state back to disk. This template starts from the opposite assumption:

- disk files are the source of truth
- prompts are thin control layers
- scripts automate repeatable filesystem work

This repository is a local agent workspace, not an online product runtime.
If you later want LangGraph, PydanticAI, or another runtime, plug it into this structure instead of replacing the structure.
