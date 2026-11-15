# Tasks

## 1. Foundation and version baseline

- [x] 1.1 Verify the existing `scripts/build_addon.py` interface and archived distribution contract with `uv run python scripts/build_addon.py` and `uv run pytest tests/integration/addon_archive_test.py`; stop if the foundation no longer meets that contract.
- [x] 1.2 Change the project version to `0.1.0.dev0`, update `uv.lock` without unrelated dependency changes, and verify `uv version --short` and `uv lock --check`.
- [x] 1.3 Document the development-to-stable-to-next-development version policy and first-release prerequisite in `README.md`; verify the documented version commands match the project configuration.

## 2. Safe preflight and preview

- [x] 2.1 Replace Luna-specific root, tracked-file, tool, remote, authentication, and version checks with Mindful checks, including the builder and executable installer source; use isolated repository tests for missing prerequisites, dirty state, wrong branch, divergent remote, and existing tags.
- [x] 2.2 Add a read-only `--dry-run` and next-bump selection that display the target repository, versions, tag, branch, and both asset names; test that preview creates no project changes, refs, pushes, or publications.
- [x] 2.3 Require explicit confirmation for a real release and reject missing or declined input; test that cancellation leaves project and remote state unchanged.

## 3. macOS installer

- [x] 3.1 Add executable `scripts/install.sh` with macOS system Bash compatibility, `--help`, default Anki `addons21` detection, and `--addons-dir` override; verify default/custom destinations, spaces, invocation from another working directory, missing or unwritable directories, and unsupported-platform guidance in isolated pytest integration tests.
- [x] 3.2 Validate the sibling archive, entry names and types, entry point, manifest identity, destination paths, and Anki process state before installation changes; test missing/corrupt/traversal/duplicate/symlink archives, reserved user-data entries, unsafe destination links, running Anki, and failed process inspection without real-user filesystem writes.
- [x] 3.3 Stage and install into `addons21/mindful` without dependencies or downloads; test successful fresh installation, existing-target refusal without `--upgrade`, rejection of development symlinks or conflicting Mindful copies, and preservation of other add-ons and profile data.
- [x] 3.4 Implement explicit `--upgrade` with a fresh code tree, unchanged `meta.json`, `config.json`, and `user_files/`, and a verified complete backup outside `addons21`; test stale-module removal, preserved file contents, retained backup identity, and rejection of symlinked preserved data.
- [x] 3.5 Track backup/staging/replacement state and provide safe restoration or manual recovery on failure; inject failures before and during replacement and concurrent target changes, asserting no unsafe overwrite or backup deletion and accurate recovery paths.
- [x] 3.6 Document ZIP extraction, macOS requirements, Anki-closed/restart guidance, default and custom paths, shared-profile scope, explicit upgrades, backup restoration, and standalone installation for other platforms in `README.md`; exercise the documented installer commands with disposable directories.

## 4. Isolated release preparation

- [x] 4.1 Prepare the stable release commit in a uniquely owned detached worktree without restoring or overwriting the caller's checkout; test that concurrent caller changes survive both success and failure.
- [x] 4.2 Run the project's quality gates and `uv run python scripts/build_addon.py` against the stable commit; test that a failing check or build prevents tag publication and GitHub release creation.
- [x] 4.3 Verify the built archive and name it `mindful-X.Y.Z.ankiaddon`; test that its entry point, manifest identity, exclusions, and stable source version/tag relationship match the existing distribution contract without requiring an absent manifest version field.
- [x] 4.4 Build `mindful-X.Y.Z.zip` with one versioned directory containing executable `install.sh` and the verified versioned `.ankiaddon`; test exact ZIP layout, executable permissions after extraction, and byte identity with the standalone asset.
- [x] 4.5 Exercise the extracted installer in isolated disposable add-on directories before publication on macOS; test that invalid bundles or installer verification failures prevent the branch/tag push, and ensure Linux release-operator tests distinguish simulated installer checks from real macOS verification.

## 5. Publication and recovery

- [x] 5.1 Create the annotated tag and push the stable commit and tag atomically without force, then create the GitHub Release with generated notes, installation guidance, and both verified assets; test success, asset identities, and rejected atomic pushes using a local bare remote and simulated `gh`.
- [x] 5.2 Create and push the selected next patch, minor, or major development commit with consistent project and lockfile versions only after both assets are confirmed published; test each bump, partial-upload blocking, and the post-publication push-failure path.
- [x] 5.3 Retain both assets and release state on failure and provide state-aware recovery instructions without rewriting history or blindly retrying uncertain publication; test failures before and after the remote push, single-asset uploads, existing mismatched assets, and simulated lost GitHub responses.
- [x] 5.4 Report both asset locations, distinguish the standalone archive for manual AnkiWeb upload, and provide the safe local fast-forward handoff; document normal and recovery workflows in `README.md` and verify the stated commands and URLs match the script.

## 6. End-to-end verification

- [x] 6.1 Run the complete project quality gates and an end-to-end dual-asset release test using an isolated local bare remote and simulated GitHub client; verify no test contacts GitHub or the real origin.
- [x] 6.2 Check `zsh -n scripts/release.sh` and `/bin/bash -n scripts/install.sh`, exercise release tests on available macOS/Linux environments, and run the extracted installer with actual macOS system tools; report unavailable platforms rather than claiming simulated tests verify them.
- [x] 6.3 Follow the documented disposable Anki data-folder smoke test for ZIP installation and explicit upgrade, checking enablement, preserved user files, and unchanged collection data; never use or sync real profiles, and report unavailable real-host verification explicitly.
