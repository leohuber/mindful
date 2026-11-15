# Proposal

## Why

Mindful currently contains a placeholder command-line entry point but no Anki add-on lifecycle or distribution format. A small, testable foundation is needed before implementing card-management features.

## What Changes

- Make `src/mindful` an Anki-loadable add-on with lightweight initialization and separate domain, application, Anki integration, and UI responsibilities.
- Support Anki Desktop 26.09.4 and newer, retaining the explicit `anki` project dependency and adding compatible `aqt` development tooling while relying on the host's runtime modules.
- Provide a repeatable `.ankiaddon` build and installation path, without bundling Anki or user-specific data.
- Add focused lifecycle, packaging, and architecture checks and document a practical development workflow.
- Add simple, concise architecture guidelines to `.github/instructions/python.instructions.md`, preserving the existing quality gates and correcting paths where needed.
- Preserve the existing placeholder `mindful` command. Card-management features, new UI, and persistent user data are out of scope.

## Capabilities

### New Capabilities

- `anki-addon-lifecycle`: Load Mindful safely in supported Anki Desktop versions and across profile lifecycle changes.
- `anki-addon-distribution`: Build and install Mindful as a correctly structured Anki add-on.

### Modified Capabilities

None.

## Impact

- Affects `src/mindful`, `pyproject.toml`, the lockfile, tests, packaging tooling, and development documentation.
- Uses Anki's `anki` and `aqt` APIs; the installed add-on uses the modules supplied by Anki rather than shipping copies.
- Updates the Python instructions and, where required to keep the existing checks runnable, the associated quality-gate configuration.
