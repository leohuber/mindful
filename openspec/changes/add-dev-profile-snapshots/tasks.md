# Tasks

## 1. Explicit snapshot capture and safe storage

- [x] 1.1 Add `scripts/dev_snapshot.sh` and `scripts/dev_snapshot.py` with required `--profile`, optional `--anki-base`, the documented default source and snapshot store, and a shared fail-closed macOS Anki process check. Verify executable wrapper/help behavior and unit cases for missing/custom sources, invalid profile names, running Anki, and unavailable process listings.
- [x] 1.2 Implement independently copied collection/media capture into private owned staging, including SQLite companion handling, staged normalization and integrity validation, and source/process rechecks. Verify focused unit cases using synthetic SQLite/media data, committed WAL data, absent media, unreadable/invalid collections, source changes, excluded preferences/add-ons/backups, and unchanged production bytes.
- [x] 1.3 Add snapshot format validation, safe-path and ownership checks, operation locking, staged replacement, rollback/recovery reporting, and bounded cleanup. Verify unit cases for explicit successful refresh, symlinks/special files, overlapping operations, unrelated existing directories, failed copy/publication/rollback, interrupted recovery state, and restrictive permissions.
- [x] 1.4 Document capture and explicit refresh commands, profile selection, local store location, Anki-closed requirements, disk/privacy considerations, and targeted failure recovery in `README.md`. Verify examples match CLI help and clearly distinguish production from snapshot data.

## 2. Dialog-free disposable development sessions

- [x] 2.1 Add a narrow development preference initializer using the existing profile-manager API behind a mockable boundary; persist English, `Mindful Dev`, completed first-run state, cleared sync authentication, disabled automatic collection/media sync, and disabled update checks. Verify unit cases with a profile-manager double, including database closure and abort-on-initialization failure, without importing Anki in unit tests.
- [x] 2.2 Adapt `scripts/dev_install.py` to select the saved snapshot by default, start empty when none exists, support `--empty` without accessing the store, and populate only the owned temporary development profile. Verify unit cases for snapshot and empty modes, invalid snapshot rejection, no production access, mode reporting, and edits that leave snapshot bytes unchanged.
- [x] 2.3 Launch with explicit profile/language arguments while retaining current archive validation, isolated single-instance key, process rechecks, process-group exit verification, and owned-base cleanup/failure retention. Update `tests/dev_install_test.py` to verify these lifecycle behaviors remain intact in both data modes and that preparation failures prevent launch.
- [x] 2.4 Update the development-session documentation with default snapshot selection, deterministic `--empty` mode, automatic-sync defaults and remaining network risks, and the distinction between discarded session data and retained snapshots. Verify the instructions match launcher help and do not imply changes to `scripts/release.sh`.

## 3. End-to-end acceptance

- [x] 3.1 With a disposable synthetic Anki source profile on macOS, exercise capture, default snapshot startup, and `--empty` startup against the installed supported Anki app. Verify neither language dialog nor profile picker appears, copied notes/media are usable, automatic sync is disabled, an explicit refresh is needed to change the snapshot, and session edits leave source/snapshot unchanged. Use no personal production data; if GUI validation is unavailable, report the blocker rather than mark this task complete.
- [x] 3.2 Run the `mindful_check_code_quality` skill after implementation; verify the full pytest suite, Ruff lint/format, Pyrefly, and import-linter checks pass. Confirm the final diff changes only the planned development scripts, their unit tests, documentation, and change artifacts, with no captured collections or media.
