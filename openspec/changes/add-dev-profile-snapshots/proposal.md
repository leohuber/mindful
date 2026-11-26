# Proposal

## Why

Every development launch currently starts with an empty Anki base, repeats the language-selection dialog, and lacks realistic notes and media. Developers need to choose when to capture production data and then test repeatedly on disposable copies without changing production or refreshing the snapshot implicitly.

## What Changes

- Add a separate macOS `scripts/dev_snapshot.sh` command, backed by Python, to create or explicitly refresh a local snapshot of one named production profile's collection and media while Anki is closed.
- Keep the reusable snapshot outside the repository and distribution artifacts; do not copy production preferences, sync credentials, installed add-ons, or backups.
- Adapt `scripts/dev_install.sh` and its Python launcher to copy the saved snapshot into each fresh temporary development base when available. Preserve empty-data development before the first snapshot and expose `--empty` for deterministic automation.
- Initialize fresh development preferences with English and a dedicated profile before launching Anki, avoiding the first-run language dialog in both modes.
- Preserve the existing process checks, packaged-build installation, disposable-session cleanup, and failure retention. Disable automatic collection and media sync in the fresh development preferences.
- Document snapshot creation, explicit refresh, source selection, default data mode, and privacy and data-loss implications.

## Capabilities

### New Capabilities

None. Snapshot management belongs to the existing local development and distribution workflow.

### Modified Capabilities

- `anki-addon-distribution`: Extend disposable development installation to allow saved collection snapshots, add safe explicit snapshot capture and unattended profile initialization, and update development workflow instructions.

## Impact

- Add snapshot command entry points under `scripts/` and focused unit tests under `tests/`; adapt `scripts/dev_install.py` and share narrowly scoped development helpers where needed.
- Update the development section of `README.md`. No add-on runtime behavior or public release publication behavior changes.
- Use the existing uv-managed Python environment and standard-library filesystem and SQLite tools; no new dependencies are planned.
- Production collection content remains local and must not enter source control, test fixtures, logs, or published assets. This proposal does not capture any actual production data.
- This intentionally replaces the current specification's unconditional empty-base behavior with snapshot-aware startup; an explicit empty mode preserves that workflow.
