# Architecture

## Design Principle

This template optimizes agent performance by externalizing state into small files.
The main improvement is not a larger prompt or a more complicated framework. It is a stricter retrieval order plus a clearer subject model.
The rules stay intentionally light because the workspace is designed for strong local LLMs.

## Subject Model

Each subject has a fixed `kind` and a fixed `mode`.

### `collection`

The subject is a container.
Its child spaces live directly under the subject root.

Example:

```text
subjects/
  CSCI/
    subject.json
    INDEX.md
    ARIN5204 Reinforcement Learning/
    COMP7404 Machine Learning in Trading and Finance/
```

This is the normal shape for academic subjects whose `kind` is `course`.

### `singleton`

The subject root is itself the active space.

Example:

```text
subjects/
  HEALTH/
    subject.json
    CLAUDE.md
    PROFILE.md
    indexes/
    memory/
    notes/
    skills/
```

This is the normal shape for spaces such as health coaching, interview prep, or other personal assistants.

## Retrieval Order

### Root
1. `registry/catalog.json`
2. `registry/INDEX.md`
3. if subject shape matters: `templates/INDEX.md`
4. only then the folder tree

### Collection Subject
1. `subject.json`
2. `INDEX.md`
3. only then the child folders under that subject

### Singleton Subject Or Child Space
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
- `subject.json` tells the registrar whether a subject is a collection or a singleton.
- `INDEX.md` files are human-readable summaries that reduce tree-scanning.
- `MEMORY.md` stays short because it stores only stable cache, not transcripts.
- `notes/chapters/` becomes the default retrieval layer for teaching and Q&A.

## File Roles

### `registry/catalog.json`
Machine-readable registry of subjects and their child spaces.

### `templates/INDEX.md`
Human-readable list of available kinds.

### `subject.json`
Machine-readable summary for one subject, including its `kind` and `mode`.

### `kind.json`
Machine-readable summary for one kind template.

### `workspace.json`
Machine-readable summary for one active space.
This appears inside child spaces and inside singleton subjects.

### `PROFILE.md`
Space-local customization for tone, goals, special rules, and custom features.

### `indexes/INDEX.md`
Canonical space map plus source and note inventory for an active space.

### `memory/MEMORY.md`
Short reusable cache for future sessions.

### `skills/`
Small optional task modules that keep `CLAUDE.md` short and let one space add specialized behavior without changing the repo-wide core.

## Intended Agent Behavior

- Root registrar creates subjects, creates new kinds when needed, and routes work.
- `collection` subjects are containers and navigation layers.
- `singleton` subjects are themselves the active space.
- Child spaces under a collection subject inherit that subject's kind.
- Local customization lives in `PROFILE.md` and `skills/`, not in the registrar.

## Why There Is No Heavy Agent Framework

For a repo-first workflow, hidden runtime graphs are fragile unless they write state back to disk. This template starts from the opposite assumption:

- disk files are the source of truth
- prompts are thin control layers
- scripts automate repeatable filesystem work

This repository is a local agent workspace, not an online product runtime.
If you later want LangGraph, PydanticAI, or another runtime, plug it into this structure instead of replacing the structure.
