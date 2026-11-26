# Design

## Context

See `proposal.md` for the motivation and the release spec delta for the behavioral contract. The existing zsh script requires a clean `main` matching origin, prepares release commits in a detached worktree, publishes the stable commit and annotated tag atomically, verifies the GitHub assets, and pushes a development commit. It currently leaves the caller's checkout at its original commit and retains the temporary worktree and assets after failures. The README documents both the version policy and manual recovery.

## Goals / Non-Goals

**Goals:**

- Determine the release version from the remote release history without relying on possibly stale local tags.
- Preserve the existing publication gates and recovery information while making successful checkout synchronization automatic.
- Allow intentional cleanup of retained release areas without deleting active work or silently discarding recovery data.

**Non-Goals:**

- Change the add-on or installer packaging, automate AnkiWeb publication, or rewrite existing release tags.
- Automatically repair divergent branches or infer how to recover a partially published release.

## Decisions

### Base versions on origin's stable tags

Query origin without changing local refs and select the numerically highest tag exactly matching `vX.Y.Z`; ignore non-stable and nonmatching tags. Treat a failed query or absence of a matching tag as a preflight error rather than guessing a first version. Calculate patch, minor, and major from the tag's numeric components, resetting lower components as appropriate; compute the next development version as the selected stable version's patch successor plus `.dev0`. The development version remains required input, but its numeric components do not set a floor; `0.6.0.dev0` can therefore release as `0.5.1` after `v0.5.0`.

The script prompts for the release bump, or accepts `--bump`; reject the old `--next-bump` with migration guidance because it has different semantics. A dry run without a bump shows all three candidates and their corresponding next-development versions. Check conflicts for the selected target and repeat the origin baseline and target-tag checks immediately before publication; stop if another release changed the baseline. This narrows but cannot eliminate concurrent remote changes, so retain the atomic push and failure recovery.

Alternative: use the current development version as the baseline. That preserves the premature version decision and cannot produce the requested patch in the transition case. Using local tags alone risks choosing a stale baseline.

### Synchronize after publication, not during preparation

Keep the isolated worktree and existing validation, atomic push, release verification, and development push. Once the development commit is pushed, inspect the original checkout again: it must still be on `main`, at the original commit, and clean. Verify origin still points to the exact pushed commit, fetch the branch, and fast-forward only to that commit. Recheck the local HEAD and live origin branch after the update.

If checks, fetch, fast-forward, or verification fail, do not force or reset anything. Report that the release was published but checkout synchronization is incomplete, retain useful recovery state, and provide inspection and safe manual fast-forward guidance. This warning must not describe a successfully published release as unpublished. A remote move after the final check remains possible; synchronization is verified at the time of the check.

Alternative: mutate the caller's checkout throughout the release. That would make validation and failure recovery interfere with local work and weaken the existing isolation.

### Cleanup requires explicit, per-area consent and safe identification

Discover candidate worktrees from Git's worktree registry for this repository, not by recursively scanning or deleting temp directories. Display each candidate's resolved worktree and release-area paths and warn that retained assets and unpushed commits can be lost. Require a separate explicit confirmation for each cleanup; declining or running a dry run makes no cleanup changes. Verify path ownership, canonical paths, directory identity, Git registration, and activity again immediately before removal; never follow symlinks, remove the caller's checkout, or delete an unverified directory.

Introduce a repository-scoped release/cleanup lock and an ownership/activity marker for new release areas, so cooperating runs cannot delete each other's active areas. Release the lock on exit without erasing retained recovery data. Older areas lack these markers: inspect and report them but leave them intact whenever inactivity and ownership cannot be established safely; explain the manual recovery and cleanup path. Do not treat a directory name or a confirmation alone as proof that an area is safe to remove. Delete only the individually confirmed and verified Git worktree and its exact owned release area.

Alternative: automatically remove every `mindful-release.*` directory. That risks destroying another user's files, active work, or the only retained copies of release assets.

## Risks / Trade-offs

- **A remote tag changes between preflight and push** -> Recheck the baseline just before the existing atomic push; report uncertain outcomes instead of retrying blindly.
- **The caller or remote changes concurrently** -> Revalidate before and after the fast-forward, preserve changes, and distinguish publication from local synchronization.
- **A legacy retained area cannot be proven inactive** -> Keep it and provide manual inspection guidance rather than guessing; cleanup is intentionally conservative.
- **A confirmed cleanup destroys recovery evidence** -> Show the exact area and warning before each confirmation, and never prompt during dry run.

## Migration Plan

Update the release script, its focused tests, and the README version policy, release commands, synchronization, and recovery guidance together. Existing releases and tags remain unchanged; the first release after `v0.5.0` can be `v0.5.1` even if the current version is `0.6.0.dev0`. Maintainers replace `--next-bump` with `--bump`. If the new workflow fails after publication, follow the retained-state recovery instructions rather than reverting published tags or force-pushing.
