# Contributing

This repository is a local agent workspace template, not a hosted product runtime.
Keep changes aligned with that scope.

## What Good Changes Look Like

- Keep the `registrar + passive subject + kind-based workspace` model intact.
- Prefer simple file protocols over new runtime layers.
- Keep `CLAUDE.md` files lean; put local behavior into `PROFILE.md` and `skills/`.
- Keep templates generic. Do not commit personal lecture files, exports, or private workspace data.

## Before You Open a Pull Request

Run the basic checks locally:

```bash
python3 -m py_compile scripts/scaffold.py scripts/audit.py scripts/md_to_pdf.py scripts/pdf_to_text.py
python3 scripts/scaffold.py rebuild
python3 scripts/scaffold.py list-kinds
python3 scripts/audit.py .
```

Run a minimal scaffold smoke test in a disposable copy:

```bash
tmpdir="$(mktemp -d)"
cp -R . "$tmpdir/repo"
cd "$tmpdir/repo"
python3 scripts/scaffold.py add-subject CSCI "Computer Science"
python3 scripts/scaffold.py add-course CSCI RL "Reinforcement Learning"
python3 scripts/audit.py "subjects/CSCI/workspaces/RL Reinforcement Learning"
```

## Pull Request Expectations

- Explain the user-facing problem you are solving.
- Note any template, script, or documentation changes.
- Update docs when behavior, file layout, or command flow changes.
- Avoid unrelated cleanup in the same pull request.

## Template and Kind Changes

If you change `templates/<kind>/`, also check whether you need to update:

- `templates/<kind>/kind.json`
- `README.md`
- `docs/architecture.md`
- `docs/PROJECT_OVERVIEW.md`

Then run:

```bash
python3 scripts/scaffold.py rebuild
```

## Communication

- Use the issue templates when possible.
- Keep bug reports concrete and reproducible.
- For new kinds, explain the intended workspace shape and why existing kinds do not fit.
