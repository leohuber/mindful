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

### Requirement: Disposable local development installation

The project SHALL provide a documented macOS development command that builds the current add-on archive, installs it in a fresh temporary Anki base directory, and launches Anki using that base.

#### Scenario: Start a development session
- **GIVEN** a supported Anki Desktop installation and the documented build prerequisites
- **WHEN** a developer runs the development command with Anki closed
- **THEN** the command builds the archive and installs its contents in the temporary base's `addons21/mindful` directory before launching Anki with that base
- **AND** the temporary base starts without copying existing profiles, add-ons, configuration, or collections

#### Scenario: Preserve the normal installation
- **WHEN** the developer runs the command
- **THEN** the command does not install into, replace, or delete anything in the normal Anki base directory

#### Scenario: Anki is already running
- **WHEN** the command detects a running Anki instance or cannot safely determine whether one is running
- **THEN** it refuses to launch and reports that Anki must be closed before retrying

### Requirement: Development session lifecycle

The development command SHALL manage only its own temporary directory and SHALL NOT remove it while the launched Anki instance may still be using it.

#### Scenario: Normal session ends
- **WHEN** the launched Anki process exits successfully
- **THEN** the command removes its temporary base and informs the developer that its test data was discarded

#### Scenario: Build, installation, or launch fails
- **WHEN** a build, archive installation, or launch step fails
- **THEN** the command reports the failure and does not report a successful session
- **AND** it does not launch Anki after an earlier failed step

#### Scenario: An interrupted or uncertain session
- **WHEN** the command cannot establish that the launched Anki process has exited
- **THEN** it leaves the temporary base intact and reports its location for manual inspection

### Requirement: Development workflow instructions

The project SHALL document the development command's prerequisites, isolation, lifecycle, and data-loss implications.

#### Scenario: Developer prepares a session
- **WHEN** a developer reads the development instructions
- **THEN** they can identify how to launch the command, that Anki must be closed, and that the temporary base begins empty
- **AND** they are warned that sandbox data is disposable and that enabling sync can affect remote data
