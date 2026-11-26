# Spec Delta

## ADDED Requirements

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
