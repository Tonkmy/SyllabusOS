# {{WORKSPACE_ID}} — {{WORKSPACE_TITLE}}

This folder is the leaf workspace created from the `{{KIND_ID}}` kind template.

## Recommended Workflow

1. Put new files into `materials/inbox/`
2. Open this folder in Codex or Claude
3. Ask the professor agent to run `/init-course` or `/intake`
4. Let the agent update:
   - `indexes/INDEX.md`
   - `memory/MEMORY.md`
   - `notes/chapters/`
5. Ask course questions with `/ask <question>`
6. Export polished notes to PDF with the root script

## Customization Surface

- `CLAUDE.md`
  Stable core behavior for this workspace.
- `PROFILE.md`
  Local preferences, answer style, special goals, and custom feature notes.
- `skills/`
  Small modular instructions for recurring tasks or special capabilities.

Prefer editing `PROFILE.md` and `skills/` before growing `CLAUDE.md`.

## File Roles

- `workspace.json` keeps stable workspace identity and status
- `PROFILE.md` keeps this workspace's local customization
- `indexes/INDEX.md` keeps the workspace map plus source and note navigation
- `memory/MEMORY.md` keeps short cache and backlog only
- `notes/chapters/` is the canonical knowledge layer
- `skills/` keeps task-specific guidance and custom features

## Structure

```text
{{WORKSPACE_ID}} {{WORKSPACE_TITLE}}/
├── CLAUDE.md
├── PROFILE.md
├── README.md
├── workspace.json
├── indexes/
│   └── INDEX.md
├── materials/
│   ├── inbox/
│   ├── lectures/
│   ├── assignments/
│   └── references/
├── memory/
│   └── MEMORY.md
├── notes/
│   ├── chapters/
│   └── exports/
└── skills/
    ├── README.md
    ├── ask.md
    ├── audit.md
    ├── chapter.md
    ├── export.md
    └── intake.md
```
