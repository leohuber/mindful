# Tasks

## 1. Release-time version selection

- [x] 1.1 Query origin's stable version tags and calculate numeric patch, minor, and major candidates and their next patch development versions; verify transitions including `v0.5.0` with `0.6.0.dev0`, multi-digit components, nonmatching tags, missing tags, and remote query failure.
- [x] 1.2 Replace `--next-bump` with `--bump`, prompt for the release type when needed, and preview all candidates when no bump is supplied in a dry run; verify argument errors, confirmation, selected previews, and that dry runs leave files and refs unchanged.
- [x] 1.3 Recheck the origin baseline and target tag immediately before the atomic push; verify a changed baseline or occupied target stops publication while existing quality and asset checks remain gates.
- [x] 1.4 Update the README version policy and release commands for `--bump`, the automatic next development version, and the initial transition; verify the examples match the implemented preview behavior.

## 2. Checkout synchronization

- [x] 2.1 After the next-development push, safely fast-forward the original checkout and verify local HEAD and live origin both match the pushed commit; exercise the successful flow using disposable Git repositories and a simulated publication.
- [x] 2.2 Preserve checkout and history when the caller's branch, HEAD, or working tree changes, origin moves, or fetch or fast-forward fails; verify publication is reported separately from incomplete sync and actionable recovery guidance is shown.
- [x] 2.3 Update the README's synchronization and interrupted-release recovery guidance; verify it distinguishes a published release from a checkout that still needs attention.

## 3. Retained worktree cleanup

- [x] 3.1 Add repository-scoped coordination and release-area ownership/activity identification; verify concurrent cooperating release or cleanup runs cannot remove an active release area and failures retain recovery data.
- [x] 3.2 Discover registered retained worktrees, display the exact candidate paths and data-loss warning, and require per-area confirmation; verify decline, dry run, active or unidentifiable legacy areas, unsafe paths, and changed directory identity leave data intact.
- [x] 3.3 Remove only a confirmed, verified inactive Git worktree and its exact owned area; verify cleanup does not affect the caller's checkout, other worktrees, unrelated directories, or symlink targets.
- [x] 3.4 Document cleanup, warnings, and manual inspection of legacy retained areas; verify the guidance preserves recovery data until the maintainer decides it is no longer needed.

## 4. Integration verification

- [x] 4.1 Run the project's relevant release tests and quality checks, and exercise a simulated complete release to verify versions, both publication assets, remote refs, local synchronization, and recovery behavior without publishing a real release.
