---
applyTo: "**/*.py"
---

## Architecture and Anki integration

* Keep `core` and `application` independent of Anki and Qt. Dependencies point inward; `ui` and `integration` are independent peers composed by `bootstrap`.
* Use relative imports within the add-on so numeric AnkiWeb directory names work.
* Initialize only in a running Anki host; do not access a collection before a profile opens or add placeholder hooks.
* Use supported Anki hooks and operations for future integrations. Keep UI work on the main thread, and use undo-aware operations for collection changes.

## After Code Changes

After code changes and before finishing up work, run the following commands to verify that the code is correct and consistent with the repository's standards:

* Run relevant tests with the project's uv-managed environment. At the end run full testsuite to ensure all tests pass. If there are violations, fix them and rerun until no errors remain.
* Run `uv run ruff check src/mindful tests scripts` and `uv run ruff format --check src/mindful tests scripts` to check lint and formatting. If there are violations, fix them and rerun until no errors remain.
* Run `uv run pyrefly check` to check for type violations. If there are violations, fix them and rerun until no errors remain.
* Run `uv run lint-imports` to check import boundaries. If there are violations, fix them and rerun until no errors remain.

Use the skill `mindful_check_code_quality` to run all of the above in one command and get a summary report.
