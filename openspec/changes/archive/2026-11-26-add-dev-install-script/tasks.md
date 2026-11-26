# Tasks

## 1. Isolated development command

- [x] 1.1 Add a macOS development command that runs the existing builder, creates a private temporary base, and installs the resulting archive safely; add unit tests verifying archive contents, sequencing, and that an existing normal base remains unchanged.
- [x] 1.2 Launch Anki with the temporary `--base`, reject running or indeterminate Anki state, and report missing executables and failed steps; add unit tests for arguments, process checks, and failure short-circuiting.
- [x] 1.3 Implement session-aware cleanup and retention on interruption or uncertain exit; add unit tests for successful cleanup, safe retention, and paths outside the owned temporary directory remaining untouched.
- [x] 1.4 Document the command, macOS and build prerequisites, Anki-closed requirement, empty disposable profile, cleanup behavior, and sync warning in the README; verify the documented invocation and flags match the implementation.

## 2. End-to-end verification

- [x] 2.1 With Anki closed, perform a manual macOS smoke check: build and launch against a temporary base, confirm Mindful loads and the normal installation is unchanged, and verify cleanup occurs only after the actual Anki session exits; investigate launcher handoff and fail safely if its lifetime is uncertain.
- [x] 2.2 Run the full project quality gate: `uv run pytest`, `uv run ruff check src/mindful tests scripts`, `uv run ruff format --check src/mindful tests scripts`, `uv run pyrefly check`, and `uv run lint-imports`.
