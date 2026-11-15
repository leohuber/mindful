---
applyTo: "tests/**/*.py"
---

# Testing

Mindful's test suite uses `pytest`. Test categories describe the scope and execution boundary of a
test; package paths beneath each category identify the production area under test.

## Categories

| Category                | Purpose                                                                                                                                                                                                           | Typical boundary                                                                                                      |
|-------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| `tests/unit/`           | Verify a small unit of logic in isolation, such as a function, class, mapper, validator, or configuration rule. Replace collaborators with fakes or mocks where appropriate.                                      | One module or class; no real database, filesystem state, or complete application workflow.                            |
| `tests/integration/`    | Verify that production modules work together across a meaningful boundary, such as service-to-database, service-to-file, configuration-to-container, or migration behavior.                                       | Real collaborating Mindful components with temporary or otherwise isolated external resources.                           |

Use the narrowest category that captures the behavior being verified. A test that happens to use a
fixture or Textual app is not automatically an integration or user-flow test: classify it by the
boundary it asserts.

## Package layout

Under each category, mirror the production package path below `mindful/`. Do not add `mindful` as
a directory in the test path.

The same module may have tests in multiple categories when each checks a distinct boundary; the
category directory distinguishes them. Keep repository-wide checks (for example, package-boundary
or test-structure contracts) in a clearly named cross-cutting area such as `tests/architecture/`
when they do not have a single production package as their subject.

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
