# Tasks

## 1. Development baseline

- [x] 1.1 Set the project and `.python-version` baseline to Python 3.13, fix the Hatch wheel source path, and verify a built wheel contains the `mindful` package.
- [x] 1.2 Retain the explicit `anki>=26.9.4` dependency, add compatible `aqt` development tooling, update the lockfile, and verify `uv sync` and `uv pip check` succeed on Python 3.13 with matching Anki packages.
- [x] 1.3 Document the Python 3.13 development setup in `README.md` and verify its setup and existing `mindful` command work as written.

## 2. Add-on lifecycle and boundaries

- [x] 2.1 Create the minimal `core`, `application`, `integration`, and `ui` package boundaries and host wiring without adding placeholder features; verify the packages import outside a running Anki GUI.
- [x] 2.2 Make the add-on entry point initialize only in an actual Anki host, without accessing a collection at startup; add focused tests for host and standalone imports.
- [x] 2.3 Use relative internal imports and add a test that loads the add-on from a numeric package directory, as used by AnkiWeb.
- [x] 2.4 Preserve the existing standalone `mindful` command and add a subprocess test confirming its output without an active Anki window.
- [x] 2.5 Implement the design's layer, host-independence, and acyclic-sibling contracts in `.importlinter`; verify `uv run lint-imports` passes and isolated allowed/forbidden fixtures cover indirect and type-only imports, peer dependencies, and sibling cycles.
- [x] 2.6 Add concise architecture and Anki integration guidelines to `.github/instructions/python.instructions.md`, preserve its quality gates, and align source paths in those instructions and the quality skill; verify the documented checks target existing paths.

## 3. Add-on distribution

- [x] 3.1 Add direct-install manifest metadata and an allowlisted builder producing `dist/mindful.ankiaddon`; add tests for the root entry point, required modules, and manifest.
- [x] 3.2 Add archive tests proving caches, tests, environments, Anki-managed metadata, user files, and bundled `anki`/`aqt`/Qt packages are excluded, including when those files exist in the checkout.
- [x] 3.3 Document the archive build command, direct installation, local development copy or symlink, and disposable-profile smoke procedure in `README.md`; run the documented build command and inspect its output.

## 4. Integration verification

- [x] 4.1 Run the project's complete pytest, Ruff, Pyrefly, and import-linter quality gates and resolve any failures caused by this change.
- [x] 4.2 Test the finished add-on in actual Anki Desktop 26.09.4 using an isolated, disposable Anki base and profile: install, restart, open and switch profiles, and verify there are no errors or collection changes.
- [x] 4.3 Exercise the same installation and lifecycle checks on a later available supported Anki Desktop release and a numeric add-on directory; report any unavailable host separately rather than treating mocked tests as a substitute.
