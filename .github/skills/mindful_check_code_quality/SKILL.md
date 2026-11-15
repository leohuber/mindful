---
name: mindful_check_code_quality
description: Run the full code quality gate for this project - all tests (pytest), Ruff lint and format check, Pyrefly type checking, and import-linter architecture contracts.
allowed-tools: Bash(uv:*)
---

Run the project's quality gate and report the results.

Run all commands from the repository root. Run **every** step even if an earlier one fails, so the user gets the complete picture in one pass.

## Steps

1. **Tests**
   ```bash
   uv run pytest tests
   ```
2. **Ruff lint**
   ```bash
   uv run ruff check src/mindful tests scripts
   ```
3. **Ruff format check**
   ```bash
   uv run ruff format --check src/mindful tests scripts
   ```
4. **Pyrefly type check**
   ```bash
   uv run pyrefly check
   ```
5. **Import Linter** (contracts in `.importlinter`)
   ```bash
   uv run lint-imports
   ```

## Handling failures

- Do **not** auto-fix unless the user asks. If they do:
  - Lint: `uv run ruff check --fix src/mindful tests scripts`
  - Format: `uv run ruff format src/mindful tests scripts`
  - Re-run all steps afterwards.
- Never silence findings with `# noqa`, `# type: ignore`, `# pyrefly: ignore`, or by editing Ruff/Pyrefly/import-linter config just to make a check pass, unless the user explicitly approves.
- Import Linter failures indicate an architecture violation (layering in `mindful`); fix by restructuring the dependency, not by adding ignores.

## Report

End with a short summary table, one row per step:

| Step | Result | Details |
|------|--------|---------|
| Tests | ✅ / ❌ | passed/failed counts |
| Ruff lint | ✅ / ❌ | number of violations |
| Ruff format | ✅ / ❌ | files needing formatting |
| Pyrefly | ✅ / ❌ | number of errors |
| Import Linter | ✅ / ❌ | broken contracts |

For each failure, list the key file/line and message (concise), and state overall pass/fail.
