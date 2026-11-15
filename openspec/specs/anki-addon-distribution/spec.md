# anki-addon-distribution Specification

## Purpose

Provide a repeatable way to develop, package, and install Mindful as an Anki Desktop add-on.

## Requirements

### Requirement: Build an installable add-on archive

The project SHALL provide a repeatable build that produces a `.ankiaddon` archive with the add-on's `__init__.py` and required files at the archive root.

#### Scenario: Build from a source checkout
- **WHEN** a developer runs the documented packaging command
- **THEN** it produces an archive with `__init__.py` at the root rather than inside an enclosing project directory

#### Scenario: Install an archive directly
- **GIVEN** an archive produced by the project
- **WHEN** a user installs it directly in a supported Anki Desktop release
- **THEN** Anki recognizes and can enable Mindful as an add-on

### Requirement: Archive excludes development and user data

The distribution archive SHALL contain only files required to install and run the add-on, not development artifacts or user-specific data.

#### Scenario: Build after local development
- **GIVEN** the checkout contains Python caches, test files, local environment files, or Anki-managed user data
- **WHEN** a developer builds the archive
- **THEN** those files are excluded from the archive

### Requirement: Use Anki-provided runtime modules

The installed add-on SHALL use the `anki` and `aqt` modules supplied by Anki rather than bundling copies or requiring users to install Python dependencies separately.

#### Scenario: Install on a supported Anki installation
- **GIVEN** a user has a supported Anki Desktop installation
- **WHEN** the user installs and enables the archive without a separate Python environment
- **THEN** Mindful loads using the host's Anki modules

### Requirement: Supported development environment

The project SHALL provide a documented development environment that can install the source package and resolve compatible Anki APIs on Python 3.13.

#### Scenario: Set up the baseline development environment
- **GIVEN** a developer has Python 3.13 and the documented package manager
- **WHEN** the developer installs the project and its development dependencies
- **THEN** the project package and compatible `anki` and `aqt` modules are available for development and tests

#### Scenario: Run the documented quality checks
- **GIVEN** the development environment is installed
- **WHEN** the developer follows the documented quality-gate commands from the repository root
- **THEN** the commands target the actual source and test paths and report actionable results
