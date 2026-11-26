# Proposal

## Why

The release script currently derives the stable version from the development version, so maintainers must choose whether to make a patch, minor, or major release one cycle too early. It also leaves the local checkout behind after publishing, requiring a manual fetch and fast-forward.

## What Changes

- Choose the patch, minor, or major release version when running the release, based on the latest release tag.
- Automatically prepare the next patch development version after publication, without asking for the next release type in advance.
- After pushing the next-development commit, fast-forward and verify the maintainer's local checkout when it is safe to do so; provide recovery guidance otherwise.
- Identify stale release worktrees and support safely cleaning them up without discarding active recovery data.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `anki-addon-releases`: Change release-time version selection and the post-release development transition; keep the local checkout synchronized with the upstream branch and provide safe stale-worktree cleanup.

## Impact

The release flow in `scripts/release.sh` and its `anki-addon-releases` specification. Release commits and tags continue to be published to GitHub; the change also updates the local Git checkout after a successful release.
