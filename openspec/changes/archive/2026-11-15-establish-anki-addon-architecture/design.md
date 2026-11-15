# Design

## Context

See `proposal.md` for motivation. The repository has an `src` layout, an `anki` dependency, Python 3.14 as its development baseline, and a placeholder `mindful` command. There are no existing domain features or tests. The wheel configuration and documented Ruff paths currently point to `mindful` rather than `src/mindful`.

Anki loads an add-on by importing its directory's `__init__.py`; AnkiWeb can name that directory with a numeric ID. Anki 26.09.4's [source Python version](https://github.com/ankitects/anki/blob/26.09.4/.python-version) is 3.13.18, and its [Linux installer](https://github.com/ankitects/anki/blob/26.09.4/qt/installer/app/pyproject.toml) uses that runtime. The current Python 3.14 minimum therefore cannot be the add-on's compatibility baseline.

## Goals / Non-Goals

**Goals:**

- Make Anki-specific behavior a narrow boundary while keeping future card-management rules independently testable.
- Preserve the existing standalone command without requiring a running Anki window.
- Make the baseline host, development environment, and installable artifact independently verifiable.

**Non-Goals:**

- Implement card management, a user-facing action, configuration, or data storage.
- Introduce a database, service, dependency-injection framework, or placeholder business logic.
- Promise compatibility with unreleased Anki API changes without testing them.

## Decisions

### Organize code around host-independent rules

Use the existing `src/mindful` directory as both the Python package and the installed add-on root:

```text
src/mindful/
  __init__.py       Anki entry point and existing CLI entry point
  bootstrap.py      minimal host wiring
  core/             host-independent domain rules
  application/      use cases and narrowly scoped ports
  integration/      Anki hooks, collection adapters, operations
  ui/               Qt presentation
  manifest.json     direct-install metadata
tests/
scripts/            add-on archive builder
```

Create only structural packages and the modules needed by this foundation; add models, adapters, protocols, dialogs, and actions when a real feature requires them. Core imports neither `anki`, `aqt`, nor Qt, and does not depend on the other layers. Application code depends on core and small interfaces rather than the Anki integration or UI. The integration and UI layers may import Anki and are composed at the boundary. Configure import-linter contracts for these invariants.

This keeps domain decisions testable without running Anki while allowing direct use of Anki APIs where they belong. A single Anki-coupled module would be simpler initially but would make later rules harder to test; a full hexagonal framework would add unnecessary abstractions.

### Enforce import boundaries

Configure `.importlinter` with these contracts:

```ini
[importlinter]
root_package = mindful
include_external_packages = True
exclude_type_checking_imports = False

[importlinter:contract:layers]
name = Dependencies point inward
type = layers
layers =
    mindful.bootstrap
    mindful.ui | mindful.integration
    mindful.application
    mindful.core

[importlinter:contract:host-independence]
name = Core and application are independent of Anki and Qt
type = forbidden
source_modules =
    mindful.core
    mindful.application
forbidden_modules =
    anki
    aqt
    PyQt5
    PyQt6
    PySide2
    PySide6
allow_indirect_imports = False

[importlinter:contract:acyclic-siblings]
name = Sibling modules and packages are acyclic
type = acyclic_siblings
ancestors =
    mindful
```

Higher layers may import lower layers. The `|` makes UI and integration independent peers; bootstrap composes them without either importing the other. The host-independence contract also checks type-only and indirect imports. Do not add blanket import ignores.

These are static import checks, not guarantees about dynamic imports, thread safety, or collection writes. Continue to verify those behaviors with tests and review.

### Keep startup safe in both Anki and the existing CLI

Anki's 26.09.4 startup sets `aqt.mw` before loading add-ons. At package import, initialize host wiring only when an actual Anki host is present; do not treat the mere availability of the `aqt` package as a running application. Avoid requiring `aqt` when the existing CLI is run outside Anki, and preserve its current output. Use relative intra-package imports so numeric AnkiWeb directory names work.

Initialization must not access the collection before a profile opens or install dummy hooks. When future features need lifecycle hooks, use Anki's supported hooks and obtain the active collection only at the appropriate time. Any future long-running work should use Anki's operation facilities; UI work stays on the main thread, and collection mutations must use supported undo-aware operations rather than direct database writes.

An unconditional bootstrap would break standalone imports or accidentally register UI behavior outside the host. A separate duplicate package solely to avoid this problem would complicate distribution.

### Align development with the host without bundling it

Set the project and baseline development Python to 3.13, retaining the explicit `anki>=26.9.4` dependency. Add `aqt` to the development dependencies with a compatible 26.09.4 minimum. The 26.09.4 `aqt` distribution requires the matching `anki` version, so resolve and test them as a pair; keep the lockfile consistent.

Test against the 26.09.4 baseline and a later available supported release using matching `anki`/`aqt` versions. Compatibility is determined by the host's bundled Python and APIs, not by the developer's interpreter alone. Fix the Hatch wheel source path so editable and wheel installs include `src/mindful`.

The `.ankiaddon` archive must not contain `anki`, `aqt`, or Qt: Anki supplies them. The project metadata and development lockfile are not an installer for end users. Bundling a second Anki or Qt runtime risks incompatible native libraries and conflicting module versions.

### Build a minimal distributable

Use a small cross-platform archive builder with an explicit allowlist of add-on code and required assets. Put `__init__.py`, the internal modules, and `manifest.json` directly at the archive root. The manifest supplies at least the package and display names for installation outside AnkiWeb. Exclude caches, tests, environments, repository metadata, Anki-managed `meta.json`, and user-specific files.

Document direct archive installation and a local development copy or symlink. Do not add a configuration file or `user_files` until a feature needs one. If later needed, simple preferences belong in Anki's configuration API; preserved user files are not automatically profile-isolated or synchronized.

A standard wheel is useful for development, but its layout is not a valid substitute for Anki's `.ankiaddon` layout. Zipping the repository wholesale risks shipping development or user data.

### Validate boundaries and actual integration

Use focused tests for package startup with and without a host, numeric package names, the existing CLI, and archive contents. Core tests must not require a running Anki GUI. Keep the existing pytest, Ruff, Pyrefly, and import-linter gates, updating the Python instructions and quality skill to target `src/mindful`, `tests`, and the builder where appropriate.

Test doubles cannot prove Anki's loader and lifecycle behavior. Include a documented smoke test using an actual supported Anki Desktop installation and a disposable profile: install the archive, restart, open and switch profiles, and verify no errors or collection changes. Run it at the baseline and a later available release where possible, and report any unavailable host separately rather than presenting a mock as equivalent.

## Risks / Trade-offs

- **Future Anki releases may change APIs or their bundled Python.** Recheck the supported version range and run compatibility smoke tests when updating dependencies.
- **Detecting the host incorrectly could skip initialization or break the CLI.** Test both host and standalone imports, and verify startup in actual Anki.
- **Archive assembly can accidentally include user data or omit required files.** Use an allowlist and test archive entries and installation.
- **Empty architecture layers can encourage premature abstraction.** Keep the initial scaffolding minimal and introduce ports or UI only for actual features.

## Migration Plan

Update the development Python and lockfile, add the host-safe entry point and architecture boundaries, then build and test an archive. Existing CLI behavior remains unchanged; there is no collection or user-data migration. Roll back by removing or disabling the add-on in Anki and restoring the previous source/dependency state; no persistent Mindful data is introduced.
