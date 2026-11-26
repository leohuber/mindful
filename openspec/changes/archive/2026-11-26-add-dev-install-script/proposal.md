# Proposal

## Why

Testing a local build currently requires manual installation or a source-directory link, which risks affecting an existing Mindful installation and does not reliably exercise the packaged archive. A disposable Anki environment makes the build-install-test cycle repeatable without touching the developer's normal profile.

## What Changes

- Add a macOS development command that builds the existing `.ankiaddon`, installs its contents into a newly created temporary Anki base directory, and launches Anki against that base.
- Start with an empty isolated collection and remove the temporary environment after Anki exits, with safeguards for errors and interrupted runs.
- Document the command, prerequisites, isolation, and the disposable nature of any test data.
- Cover archive installation, isolation, launch, cleanup, and failure behavior with focused tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `anki-addon-distribution`: Add a disposable, archive-based local development workflow.

## Impact

- Development tooling under `scripts/`, associated unit tests, and the README.
- Requires a locally installed macOS Anki Desktop; does not change the release installer or shipped add-on.
- The default Anki data directory, existing add-ons, configuration, and collection are not copied or modified.
