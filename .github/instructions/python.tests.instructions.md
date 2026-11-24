---
applyTo: "tests/**/*.py"
---

# Testing

Mindful's test suite uses `pytest`. Test categories describe the scope and execution boundary of a
test; package paths beneath each category identify the production area under test.

## Categories

Only add unit tests, not integration tests or tests that depend on the anki api. Add unit tests directly to `tests/` in the project root, followed by the package structure of the element to be tested.

## Package layout

Under each category, mirror the production package path below `mindful/`. Do not add `mindful` as
a directory in the test path.

## Naming

### Modules

Mirror the production package path beneath the category, then name a test module for its production
module:

- One file: `<module>_test.py`.
- Separate files for distinct concerns: `<module>_<behavior>_test.py`.
- No single production-module subject: `<responsibility>_test.py` in the narrowest relevant
  cross-cutting directory, such as `tests/architecture/`.

### Classes and functions

Prefer standalone pytest functions named `test_<observable_behavior>[_when_<condition>]`.
Use `Test<Subject>` classes only to group several closely related tests; methods still begin with
`test_`. Avoid names that merely repeat the module name or describe implementation steps. Use
descriptive behavior names such as `test_invalid_duration_warns_and_uses_default_once`.

Non-test classes (harnesses, test data, and doubles) use `CapWords` names that state their role,
such as `ValidationHarness` or `IsolatedProjectConfig`. Use `Fake`, `Stub`, or `Spy` suffixes only
when that distinction is useful.
