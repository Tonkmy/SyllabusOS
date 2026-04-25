# Subjects

Each subject has a fixed `kind` and a fixed `mode`.

## Collection Subject

Use this when the subject is a container for multiple child spaces.

Example:

```text
subjects/
  CSCI/
    subject.json
    INDEX.md
    ARIN5204 Reinforcement Learning/
    COMP7404 Machine Learning in Trading and Finance/
```

This is the normal shape for `kind=course`.

## Singleton Subject

Use this when the subject root is itself the active space.

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

This is the normal shape for personal assistants such as health coaching or interview prep.

Use the root registrar to create subjects and kinds.
Then move directly into the active subject folder or child folder for actual work.
