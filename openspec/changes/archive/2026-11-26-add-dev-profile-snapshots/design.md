# Design

## Context

See `proposal.md` for motivation. `scripts/dev_install.sh` delegates to `dev_install.py`, which builds the archive, extracts it into an owned temporary base, launches the macOS Anki application with an isolated single-instance key, waits, and conditionally removes that base. Existing tests mock process launch; `scripts/release.sh` verifies installation but does not run a GUI smoke test.

The current distribution specification explicitly forbids copying collections into development sessions; the delta intentionally changes that restriction while retaining production isolation and disposable working data.

The installed development `aqt` source shows that missing `prefs21.db` triggers `ProfileManager.setDefaultLang()` before add-ons load, even when `--lang` is supplied. Profile metadata also contains sync credentials and flags. Copying production preferences would avoid setup but import unnecessary account state.

## Goals / Non-Goals

**Goals:**
- Keep production, the reusable snapshot, and session working data as three independent storage boundaries.
- Make capture explicit, repeatable, and fail-closed; make development launch independent of production availability.
- Initialize only temporary development preferences through a narrow compatibility adapter.

**Non-Goals:**
- Implementing the plan during proposal creation, capturing actual user data, or altering add-on runtime code.
- Automated scheduled refresh, merging dev edits into production, persistent dev edits, or simultaneous production and development Anki instances.
- Copying all production profiles, third-party add-ons, production preferences, or backup history.
- Changing `scripts/release.sh`, adding GUI tests to pytest, or guaranteeing offline operation after a user manually signs in or enables sync.

## Decisions

### 1. Separate explicit capture from development launch

Add executable `scripts/dev_snapshot.sh`, following the existing wrapper convention, and `scripts/dev_snapshot.py`. Its interface is:

```sh
./scripts/dev_snapshot.sh --profile "User 1"
./scripts/dev_snapshot.sh --anki-base "/custom/Anki2" --profile "Study"
./scripts/dev_install.sh
./scripts/dev_install.sh --empty
```

Default the production base to `~/Library/Application Support/Anki2`. Require a named, direct-child profile rather than reading or unpickling production preferences to infer one. Reject missing profiles, separators, traversal, symbolic links, and sources outside the selected base. Re-running the capture command explicitly requests replacement; there is no interactive confirmation or implicit refresh.

Use the fixed local store `~/Library/Application Support/Mindful/dev-snapshot`, containing a small versioned manifest, `collection.anki2`, and `collection.media/`. Create private store directories and files so collection content is not made world-readable by a permissive umask. No custom snapshot destination is needed initially; this avoids arbitrary overwrite and cleanup roots.

The development launcher uses a valid existing snapshot by default and otherwise starts empty, reporting the mode. `--empty` bypasses the store entirely, including malformed snapshots. An existing invalid store is an error in default mode, not a reason to silently start empty.

Alternative: automatically clone production during each launch. Rejected because freshness must be developer-controlled and launch must not touch production.

### 2. Capture consistent data without modifying the source

Reuse the existing macOS process check through a small shared development helper, preserving direct script execution. Check Anki is closed before reading the source and immediately before publishing a snapshot; fail closed on indeterminate process state. Tell developers to keep Anki closed throughout capture.

Copy only the selected collection, any SQLite journal/WAL companions needed for recovery, and media into an invocation-owned staging area. Do not open the production database through Anki's collection APIs. Normalize the staged database using SQLite backup from the staged copy into the final staged `collection.anki2`, then run an integrity check. Anki collections use its custom `unicase` collation, so run the check through the existing Anki backend on a further disposable copy; plain Python SQLite cannot validate those indexes. This keeps checkpoint/recovery and Anki initialization writes away from production and the reusable snapshot and avoids silently losing committed WAL data. A journal state SQLite cannot safely recover in staging aborts capture.

Treat an absent media directory as empty, but fail on unreadable files or unsupported filesystem entries. Make independent copies, never hard links or symlinks. Exclude source `prefs21.db`, media-sync databases, backups, logs, and add-ons; Anki can rebuild media metadata in the dev copy.

Check source file identities, sizes, and modification times across capture and refuse publication if the source changed. These checks complement the process checks; they are not an OS-enforced lock preventing a user from briefly starting Anki between checks.

Alternative: copying the entire normal Anki base. Rejected because it imports authentication, unrelated add-ons, and unnecessary personal state.

### 3. Publish complete snapshots and preserve recovery

Serialize refresh and snapshot-to-session copying with an advisory lock in the private store parent. A second operation fails clearly rather than consuming a mixed snapshot; release the lock after the session copy, not after Anki exits.

Construct and validate the replacement in a sibling owned staging directory. Identify existing stores by a format marker and reject unrelated directories or symlinked storage components. Only after validation, move an existing snapshot to an owned recovery name and publish the staged replacement. Roll back the old snapshot on ordinary publication errors; if rollback fails, retain and report its recovery path. Do not silently treat an interrupted replacement with recovery state as an absent snapshot.

Cleanup is restricted to identity-checked directories created or positively identified as owned snapshot generations. Never recursively delete an arbitrary supplied source or broadly remove the store parent. Interrupted staging or recovery state must have explicit diagnostic guidance.

Alternative: delete the old snapshot before copying. Rejected because disk-full, interruption, or validation errors would destroy the last usable snapshot.

### 4. Build fresh Anki preferences before GUI launch

Add a narrow development-only initializer using the existing uv-managed `aqt.profiles.ProfileManager` API. In the owned temporary base, call metadata setup, persist English via `setLang("en_US")`, create and load the dedicated `Mindful Dev` profile, mark first-run setup complete, clear sync authentication, disable `autoSync` and `syncMedia`, disable automatic update checks, and save and close the preferences database. Do not invoke the language dialog or load production preferences.

Pass `--profile "Mindful Dev"` and `--lang en` alongside the existing `--base`. These options select the initialized profile and language; the preferences file, not the language flag alone, prevents the first-run dialog.

Copy snapshot data into the dedicated profile before launch; in empty mode leave collection creation to Anki. Initialization failures prevent GUI launch and use existing failure-retention reporting. Preserve archive validation, the single-instance key, the pre-launch process recheck, process-group verification, and owned-base cleanup.

Alternative: hard-code Anki's pickled preferences schema or patch language selection after launch. Rejected because the existing profile API supplies defaults and because add-ons load too late to prevent the dialog. Keep API usage behind one adapter to contain version drift.

### 5. Verify behavior without making unit tests depend on Anki

Extend `tests/dev_install_test.py` and add snapshot/helper test modules following the project's naming conventions. Use temporary synthetic SQLite databases, tiny media files, and mocks for processes and the profile API boundary; do not read real production data or require a GUI or Anki API in unit tests.

Cover explicit refresh, missing and custom sources, WAL-backed input, rejected unsafe paths, capture races, failed publication and recovery, snapshot-vs-empty selection, independent dev writes, and retained-base behavior. Use profile-manager doubles to verify language/profile persistence, disabled automatic sync, absent imported authentication, and abort-on-initialization failure.

Document a separate macOS manual smoke check with synthetic data to verify actual application startup bypasses language selection and opens the copied collection with media. Unit assertions about flags alone cannot establish that the real dialog is absent. This check is an implementation acceptance step, not a new automated integration suite.

## Risks / Trade-offs

- Anki profile APIs and preferences may drift between the uv package and installed app -> Isolate initialization, fail before launch on adapter errors, and smoke-check the supported installed application.
- Large media folders consume disk and copy time -> Report capture and session-copy phases, fail cleanly on insufficient space, and retain the prior snapshot.
- Production may change during capture despite initial checks -> Recheck process state and source metadata and document the limitation rather than claim a source-wide atomic filesystem snapshot.
- Copies contain private notes and media even without account credentials -> Private permissions, external storage, no note content in logs, and explicit local-data handling instructions.
- Collection content can contain external resource URLs -> Disabled sync is not a network sandbox; retain a warning against enabling sync or signing into production accounts.
- Replacement interrupted between renames -> Preserve identified recovery state, block ambiguous automatic consumption, and document targeted recovery instead of deleting unknown paths.

## Migration Plan

No existing snapshot data requires migration. Existing users without a snapshot keep empty-data development, now without first-run language interaction. Snapshot users opt in by explicitly running capture once; later captures replace only the local store. Document the changed default after opt-in and `--empty` for automation.

Rollback restores the prior launcher and removes the new entry points; it must not delete production, retained sessions, or snapshot data automatically. The reusable snapshot is developer-owned local data, independent of published add-on releases.
