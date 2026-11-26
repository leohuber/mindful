# Spec Delta

## MODIFIED Requirements

### Requirement: Releases start from a development version

The release workflow SHALL accept only a project version of the form `X.Y.Z.devN` and determine the stable release version by applying the maintainer's patch, minor, or major selection to the highest stable `vX.Y.Z` tag on origin.

#### Scenario: Preview a development version
- **GIVEN** the latest stable tag on origin is `v0.5.0` and Mindful's development version is `0.6.0.dev0`
- **WHEN** a maintainer previews a patch release
- **THEN** the workflow identifies the release version as `0.5.1` and the tag as `v0.5.1`

#### Scenario: Select a minor or major release
- **GIVEN** the latest stable tag on origin is `v0.5.0`
- **WHEN** a maintainer selects minor or major
- **THEN** the workflow identifies the release version as `0.6.0` or `1.0.0`, respectively

#### Scenario: Reject a stable input version
- **GIVEN** Mindful's version is `0.1.0`
- **WHEN** a maintainer starts a release
- **THEN** the workflow reports that a development version is required and makes no release changes

#### Scenario: No trustworthy release baseline
- **GIVEN** origin cannot be queried or has no stable `vX.Y.Z` tags
- **WHEN** a maintainer starts or previews a release
- **THEN** the workflow reports the missing or unavailable baseline and makes no release changes

#### Scenario: Release selection is provided as an option
- **WHEN** a maintainer specifies `--bump patch`, `--bump minor`, or `--bump major`
- **THEN** the workflow uses that release type without prompting for a release type

#### Scenario: Reject the obsolete option
- **WHEN** a maintainer supplies `--next-bump`
- **THEN** the workflow stops before release changes and directs the maintainer to `--bump`

### Requirement: Release preview requires confirmation

The workflow SHALL display the versions, tag, repository, branch, and both assets to be published before requesting explicit confirmation.

#### Scenario: Preview without publishing
- **WHEN** a maintainer runs the release preview without selecting a bump
- **THEN** it displays the patch, minor, and major release options and their next development versions without modifying project files or Git refs, pushing, publishing, or cleaning up worktrees

#### Scenario: Preview a selected release
- **WHEN** a maintainer runs the release preview with a valid `--bump`
- **THEN** it displays the selected release and next development versions, tag, and assets without making release changes

#### Scenario: Decline confirmation
- **WHEN** a maintainer declines or does not provide confirmation
- **THEN** the workflow stops without creating release commits, tags, or publications

### Requirement: Start the next development version

After GitHub publication, the workflow SHALL commit and push the next patch development version automatically while keeping project and lockfile versions consistent.

#### Scenario: Start the next patch development cycle
- **GIVEN** release `0.1.0` has been published
- **WHEN** the workflow completes the development transition
- **THEN** the remote branch contains a subsequent commit with version `0.1.1.dev0` and a matching lockfile, without requesting the type of the next release

## ADDED Requirements

### Requirement: Confirm the release baseline before publication

The workflow SHALL recheck the selected release baseline and target tag before publication and stop if a new stable tag changes the baseline or the target tag becomes occupied.

#### Scenario: A competing release changes the baseline
- **GIVEN** the maintainer confirmed a release based on `v0.5.0`
- **WHEN** origin gains a higher stable release tag during preparation
- **THEN** the workflow stops before pushing its branch or tag and reports that the release must be reconsidered

### Requirement: Synchronize the caller's checkout after publication

After pushing the next development commit, the workflow SHALL fast-forward the caller's `main` only if its branch, HEAD, and working tree still permit a safe update. It SHALL verify local HEAD and origin `main` both equal the pushed commit and report whether synchronization succeeded.

#### Scenario: Unchanged checkout
- **GIVEN** publication and the development push succeeded and the caller's clean checkout is still on the original `main` commit
- **WHEN** the workflow finishes
- **THEN** local `main` and origin `main` both point to the next development commit

#### Scenario: Checkout changed during release
- **GIVEN** the caller's branch, HEAD, or working tree changed during release preparation
- **WHEN** the published release reaches the synchronization step
- **THEN** the workflow preserves the caller's changes, reports that publication succeeded but local synchronization did not, and provides safe recovery guidance

#### Scenario: Remote moved or synchronization failed
- **GIVEN** the remote moved after the development push or the local fast-forward cannot be verified
- **WHEN** the workflow attempts to synchronize
- **THEN** it does not overwrite local or remote history and reports the published release and unresolved synchronization separately

### Requirement: Safely clean retained release worktrees

The workflow SHALL identify retained Mindful release worktrees and offer cleanup only after showing their locations and explicitly warning that retained recovery data may be removed. It SHALL remove only individually confirmed, safely identified, inactive worktrees and their associated release areas.

#### Scenario: Confirm cleanup of a retained release area
- **GIVEN** a retained release worktree is safely identified as inactive
- **WHEN** the maintainer explicitly confirms cleanup of that worktree and its release area
- **THEN** the workflow removes only that confirmed worktree and its associated release area

#### Scenario: Decline or cannot establish safe cleanup
- **GIVEN** a worktree is active, cannot be safely identified, or is not confirmed for cleanup
- **WHEN** cleanup is considered
- **THEN** the workflow leaves it and its release area intact and reports any unsafe or skipped cleanup

#### Scenario: Preview with retained worktrees
- **GIVEN** retained release worktrees exist
- **WHEN** a maintainer runs a dry run
- **THEN** the workflow makes no cleanup changes
