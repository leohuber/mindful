# Design

## Context

See `proposal.md` for the release scope. `scripts/release.sh` is a copied, 232-line zsh script; its current working-tree contents are not yet a Mindful release workflow:

- Preflight requires `luna_app`, `dev/install.sh`, and `luna_app/shared/_release.py`, which do not exist here. It accepts only `X.Y.Z.devN`, while `pyproject.toml` currently says `0.1.0`.
- It switches a Luna data-directory setting, builds a wheel, exports constraints, and packages an installer ZIP. None is the `.ankiaddon` artifact defined by `establish-anki-addon-architecture`.
- It already checks a clean `main`, synchronizes with `origin/main`, rejects duplicate tags, creates an annotated tag, atomically pushes branch and tag, publishes a GitHub Release, and starts the next development version.
- Its failure trap restores expected files in the caller's checkout if HEAD is unchanged. Another process can edit those files after preflight, so this rollback can discard work. The script also has macOS-specific `sed` commands and does not run this project's quality gates.

The add-on foundation is now implemented and archived. `scripts/build_addon.py` writes `dist/mindful.ankiaddon` with an explicit file list; `tests/integration/addon_archive_test.py` verifies its layout and exclusions. `src/mindful/manifest.json` identifies the package as `mindful`. `README.md` documents direct archive installation and local copies under `addons21/mindful`. These are the source of truth; the new installer ZIP wraps the existing archive without another add-on build.

## Goals / Non-Goals

**Goals:**

- Retain the useful versioning and publication behavior while releasing the exact Anki add-on artifact.
- Keep the operator's checkout and other users' changes safe across failures.
- Make each published artifact traceable to a stable commit and recoverable without rewriting history.
- Offer macOS file-copy installation and explicit upgrades while preserving user-owned files and a recoverable old installation.

**Non-Goals:**

- Publish to AnkiWeb automatically or store AnkiWeb credentials.
- Build wheels, package Anki or Qt, install a separate Python environment, or implement a native Linux or Windows shell installer.
- Install into individual profile directories, modify collections, discover arbitrary custom Anki data folders automatically, or migrate numeric AnkiWeb/development-symlink installations.
- Automate GUI-based Anki smoke tests; maintainers follow the foundation's documented real-host procedure.

## Decisions

### Single development-to-stable version flow

Before the first release, set `pyproject.toml` to `0.1.0.dev0` and update `uv.lock` consistently. Release preflight rejects stable versions and accepts only `X.Y.Z.devN`. Preview the stable version, `vX.Y.Z` tag, and a next patch/minor/major `X.Y.Z.dev0` version using `uv`'s version semantics; compute the next version from the stable release, not by guessing string components.

The tagged release commit contains the stable project and lockfile versions. A later commit contains the chosen next development version. Validate that version operations change only the intended metadata and do not silently update unrelated dependencies. This preserves the copied script's existing cycle; accepting already-stable inputs would make the first release a special case and was not selected.

### Preview, validate, and explicitly confirm

Provide a read-only `--dry-run` preview, with a way to select the next bump for non-interactive preview. Show the resolved GitHub repository, branch, stable and next versions, tag, both asset names, and validation failures. Preview must not write project files, create refs, or publish; use remote queries rather than `git fetch` to compare the live branch and tags.

For a real release, require a clean checkout on `main` equal to `origin/main`, tracked and consistent version files, available tools, builder and executable installer source, the correct GitHub repository and authentication, and no existing local or remote tag or GitHub Release for the target version. A missing terminal or declined confirmation aborts before changes. Recheck relevant local and remote state at the publication boundary; do not rely solely on the initial check.

### Isolate release mutations from the caller's checkout

After confirmation, create a uniquely named temporary detached Git worktree at the preflight commit. Make version changes and the release and next-development commits there, never by restoring files in the caller's checkout. The release tag is a shared local Git ref and is created only after the release commit and checks succeed.

```text
clean main + origin --> preview / confirm --> isolated worktree
                              |
                              v
               stable version + release commit
                              |
                     quality gates + build
                              |
                  annotated tag + atomic push
                              |
              GitHub Release + .ankiaddon + ZIP
                              |
                next-dev commit + normal push
                              |
              manual AnkiWeb upload / local sync
```

Push the release commit to `origin/main` and its annotated tag in one non-force atomic push; if the remote rejects it, do not fall back to separate pushes. Publish the release against the verified tag. Push the subsequent development commit without force, stopping if the remote has moved.

The original checkout stays on its original commit. After a successful release, print instructions for the maintainer to inspect their checkout and fast-forward it explicitly. Never silently move that checkout or delete tags, commits, or remote releases. Remove only verified, script-owned temporary files/worktrees on success; if safety is uncertain or the release fails, retain the work area and report its path.

Using the original checkout and automatically restoring files is simpler, but cannot distinguish the script's edits from concurrent edits reliably. An isolated worktree also leaves the release commit available for inspection when publication fails.

### Reuse the builder and package two verified assets

Run `uv run python scripts/build_addon.py` from the stable release worktree and copy its `dist/mindful.ankiaddon` output to the owned release area as `mindful-X.Y.Z.ankiaddon`. Verify the archive layout, required manifest and entry point, absence of caches, user files, and bundled Anki/Qt, and consistency between the stable source version, tag, and release title. The current manifest does not encode a version; do not claim it provides version verification. Run the existing full project quality gates before the branch/tag push.

Create the following wrapper from files in the same stable commit, preserving the installer's executable bit:

```text
mindful-X.Y.Z.zip
  mindful-X.Y.Z/
    install.sh
    mindful-X.Y.Z.ankiaddon
```

Unpack the ZIP into an isolated verification area, verify the exact layout and executable script, and compare the nested archive byte for byte with the standalone asset. The wrapper contains no wheel, constraints file, runtime environment, or duplicate unpacked source tree. This retains one source of truth and avoids drifting installer payloads. Exercise the extracted installer with disposable directories before publication; never use the maintainer's Anki folder.

The GitHub Release uploads both verified assets and combines generated notes with concise installation guidance. Report both asset URLs and the [AnkiWeb upload page](https://ankiweb.net/shared/addons). Only the standalone `.ankiaddon` is uploaded manually to AnkiWeb; the ZIP is a macOS convenience bundle, not an Anki install-from-file archive.

### macOS installer with default detection and override

Add executable `scripts/install.sh`, compatible with macOS's system Bash. Use system archive tools and `plutil` for JSON manifest validation rather than introducing a Python or package-manager requirement. Resolve the bundle relative to the script, not the caller's working directory, and require exactly one correctly named sibling `.ankiaddon`. All consumer operations are local; the script does not fetch dependencies or launch Anki.

Default to `$HOME/Library/Application Support/Anki2/addons21`, with `--addons-dir PATH` accepting an absolute existing writable add-on directory for an Anki `-b` custom data folder. Document `--help` and `--upgrade`. Fail with actionable guidance if the default is absent instead of guessing another folder or creating a fake Anki profile. Install into its `mindful` child, matching the package manifest and existing local-development documentation. Add-ons are shared by profiles within an Anki data folder, not installed into a profile's collection directory.

Require Anki to be closed and stop if the process check detects a running Anki instance or cannot reliably inspect process state. Recheck immediately before replacement and document that the user must not reopen Anki during installation; process checks cannot lock out a concurrent launch. Unsupported systems receive direct `.ankiaddon` installation guidance without filesystem changes.

Before extraction, validate archive integrity, entry names, entry types, expected manifest identity, and required root files. Reject absolute or traversal paths, duplicate/ambiguous entries, symbolic links, and reserved user-data entries. Reject symlinked destination components, existing target links, and links within user data to be preserved; do not follow them. Quote paths and test spaces in both bundle and destination names. Check canonical paths before writes or cleanup. Numeric AnkiWeb package directories or other conflicting Mindful copies require manual resolution rather than installing a second active copy or guessing which one to replace.

Opening the archive in Anki would be simpler, but the requested installer copies files. Automatically guessing arbitrary custom data paths or editing collection databases would increase risk without meeting a necessary requirement.

### Explicit upgrade with retained backup

A new install stages the validated archive outside `addons21` on the destination filesystem, exclusively creates `addons21/mindful`, and copies the staged files into it. An existing ordinary `mindful` directory is never overwritten without `--upgrade`; an existing development symlink or ambiguous target is rejected even with that flag.

For an upgrade, prepare a fresh staged tree rather than copying code over old files, which would retain removed modules. Copy the existing `meta.json`, `config.json`, and `user_files/` into that tree unchanged when present. These paths are installer-preserved user state, not files supplied by the release archive. Keep the new packaged manifest and code; do not retain other obsolete files in the active installation.

Before replacement, retain a complete uniquely named backup beneath the selected Anki data folder's `mindful-backups/` directory, outside `addons21` so Anki cannot load the backup as another add-on. Verify the backup and recheck the target has not changed. Use a script-owned staging/rollback area on the same filesystem and tracked replacement phases; directory replacement is not a globally atomic transaction. If replacement fails, restore the prior directory only when doing so cannot overwrite concurrent changes. Otherwise retain both states and report exact manual recovery paths.

Retain and report the complete backup even after success; explain restoration with Anki closed. Cleanup removes only verified, owned staging paths, never backups, other add-ons, or profile data. Do not use privileged installation or broad recursive deletion. The archive path and destination are untrusted inputs despite the usual GitHub-download workflow.

### Recover from partial or uncertain publication

Record and report the last confirmed state and retain both assets and the temporary worktree on failure. Before suggesting a retry after a network error, instruct the maintainer to inspect the remote branch, tag target, GitHub Release, and both existing asset identities. A release with only one uploaded asset is incomplete, even if the GitHub Release exists. After inspection, upload only a confirmed missing asset; if the remote state or an existing asset differs, stop for manual resolution rather than overwriting or recreating it. Advance to the next development version only after both uploads are confirmed. If publication succeeded but the development push failed, preserve the release and provide the steps to finish the next-development commit.

### Test without real publication

Use temporary Git repositories with a local bare remote and a simulated `gh` client. Cover successful version transitions, dual-asset identity and ZIP layout, preflight rejection, dry-run and cancellation, quality/build/installer-verification failures, atomic push failure, partial asset upload, uncertain publication, and recovery after publication. Assert that tests never invoke the real GitHub API or push to the real origin.

Extend the existing pytest integration suite with shell-installation tests using temporary HOME, disposable add-on directories, and simulated process state. Cover default detection, explicit overrides, paths with spaces, invocation from another working directory, unsupported platforms, running Anki, missing destinations, corrupt/traversal/symlink archives, implicit-overwrite refusal, explicit upgrade preservation and stale-code removal, backup retention, and failures in staging or replacement. Do not install into a real user profile, launch a user's Anki, or claim real-host verification from simulated process checks.

Validate the release operator script on macOS and Linux with zsh and documented dependencies. Exercise the actual extracted installer with macOS system tools and perform the documented real-host smoke test only against disposable Anki data. Linux and Windows consumers retain direct `.ankiaddon` installation; shell-installer support is macOS only.

## Risks / Trade-offs

- **A GitHub request can succeed even when its response is lost, or upload only one asset.** Inspect remote state and both asset identities before any retry; retain the worktree and both assets.
- **Concurrent activity can invalidate preflight or alter the caller's checkout.** Isolate mutations, recheck refs before pushing, use non-force pushes, and avoid automatic checkout restoration.
- **Anki may launch or files may change during installation.** Require Anki closed, recheck process and target state before replacement, preserve a verified backup, and stop for manual recovery if concurrent changes make restoration unsafe.
- **Default-path detection cannot find all Anki data folders.** Require `--addons-dir` for custom locations and refuse missing or symlinked destinations instead of guessing.
- **Backups consume disk space and contain user-owned files.** Retain them locally outside `addons21`, report their paths, and leave deliberate removal to the user.
- **The caller's local branch is stale after a successful isolated release.** Print an explicit, safe fast-forward handoff rather than modifying a potentially changed checkout.

## Migration Plan

Verify the existing builder and distribution contract, then switch the current development version to `0.1.0.dev0`. Add and test the macOS installer, adapt the release script using local test remotes, and document operator and consumer workflows. Existing published history is unchanged; before a real release, a maintainer reviews the dry run and confirms. If an attempted release stops, use the retained state and recovery guidance rather than rewriting the branch or deleting a published tag. Installer upgrades require an explicit flag and retain a backup; restoration is performed with Anki closed and without modifying other add-ons or collections.
