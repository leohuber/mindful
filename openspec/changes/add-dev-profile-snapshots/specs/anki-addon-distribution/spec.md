# Spec Delta

## MODIFIED Requirements

### Requirement: Disposable local development installation

The project SHALL provide a documented macOS development command that builds the current add-on archive, installs it in a fresh temporary Anki base directory, and launches Anki using that base. It SHALL seed the development profile from the saved snapshot when available, unless empty mode is requested, without reading production data during launch.

#### Scenario: Start a development session
- **GIVEN** a supported Anki Desktop installation and the documented build prerequisites
- **WHEN** a developer runs the development command with Anki closed
- **THEN** the command builds the archive and installs its contents in the temporary base's `addons21/mindful` directory before launching Anki with that base
- **AND** it creates fresh development preferences without copying production preferences or installed add-ons

#### Scenario: Use a saved snapshot
- **GIVEN** a valid saved development snapshot exists
- **WHEN** the developer starts a development session without empty mode
- **THEN** its collection and media are copied into the temporary development profile
- **AND** the command identifies snapshot mode without refreshing the snapshot or accessing the production profile

#### Scenario: Start without a snapshot
- **GIVEN** no saved development snapshot exists
- **WHEN** the developer starts a development session
- **THEN** the command identifies empty mode and starts without copied collection data or media

#### Scenario: Explicitly request empty data
- **GIVEN** a saved development snapshot exists
- **WHEN** the developer runs the development command with `--empty`
- **THEN** the command starts without copying or modifying the saved snapshot

#### Scenario: Reject an invalid saved snapshot
- **GIVEN** a saved snapshot is incomplete, corrupt, or unsafe
- **WHEN** the developer starts a development session without empty mode
- **THEN** the command reports the problem and does not launch Anki or silently fall back to empty data

#### Scenario: Preserve the normal installation
- **WHEN** the developer runs the command
- **THEN** the command does not install into, replace, or delete anything in the normal Anki base directory

#### Scenario: Anki is already running
- **WHEN** the command detects a running Anki instance or cannot safely determine whether one is running
- **THEN** it refuses to launch and reports that Anki must be closed before retrying

### Requirement: Development workflow instructions

The project SHALL document the development commands' prerequisites, snapshot selection and refresh, non-interactive initialization, isolation, lifecycle, and data-loss implications.

#### Scenario: Developer prepares a session
- **WHEN** a developer reads the development instructions
- **THEN** they can identify how to launch the command, that Anki must be closed, how snapshot and empty modes are selected, and that language selection requires no interaction
- **AND** they are warned that sandbox data is disposable and that enabling sync can affect remote data

#### Scenario: Developer manages snapshot data
- **WHEN** a developer reads the snapshot instructions
- **THEN** they can identify how to select a production profile, override its base directory, explicitly create or replace the snapshot, and locate the stored copy
- **AND** they understand that it contains private collection and media content, must remain outside source control and releases, and is never refreshed by starting or closing a development session

## ADDED Requirements

### Requirement: Explicit development snapshot capture

The project SHALL provide a separate macOS command to create or replace one reusable local snapshot of a named production profile's collection and media. Capture SHALL require Anki to be closed and SHALL NOT modify production files or launch Anki.

#### Scenario: Capture a selected profile
- **GIVEN** Anki is closed and the named production profile has a valid collection
- **WHEN** the developer invokes the snapshot command with that profile
- **THEN** the command saves a consistent collection and its media outside the repository and reports the snapshot location
- **AND** it excludes production preferences, authentication, installed add-ons, and backups

#### Scenario: Select a custom production base
- **WHEN** the developer supplies a custom Anki base and a profile name
- **THEN** the command captures only that profile within the selected base

#### Scenario: Require unambiguous source selection
- **WHEN** the profile name is missing, does not identify a valid profile within the selected base, or contains path traversal
- **THEN** the command fails without changing production or an existing snapshot
- **AND** it does not display an interactive profile picker

#### Scenario: Refuse capture while Anki may be active
- **WHEN** Anki is detected running before or during capture, source changes are detected, or its process state cannot be determined
- **THEN** the command fails without publishing the new snapshot
- **AND** any previous valid snapshot remains available

#### Scenario: Preserve a previous snapshot on failure
- **GIVEN** a valid snapshot already exists
- **WHEN** a replacement fails during copying, validation, or publication
- **THEN** the previous snapshot remains usable or recoverable at a reported location
- **AND** the command does not report successful refresh

#### Scenario: Refresh only on explicit capture
- **GIVEN** a valid snapshot already exists and production data has changed
- **WHEN** the developer explicitly invokes the snapshot command again
- **THEN** the command replaces the snapshot with the selected profile's current data after successful capture

### Requirement: Isolated snapshot working copies

Development sessions SHALL use independently writable copies of snapshot data. Neither development writes nor session cleanup SHALL alter the saved snapshot or production data. Snapshot capture and consumption SHALL reject symbolic links and unsafe filesystem entries rather than follow them outside their intended roots.

#### Scenario: Edit and discard development data
- **GIVEN** a development session was seeded from a snapshot
- **WHEN** data is edited and the session exits successfully
- **THEN** only the temporary working copy is changed and removed
- **AND** a later development session starts from the unchanged saved snapshot

#### Scenario: Reject linked data
- **WHEN** snapshot capture or consumption encounters symbolic links or unsupported special filesystem entries
- **THEN** it fails without writing through those entries or launching a development session

#### Scenario: Snapshot operations overlap
- **WHEN** snapshot refresh overlaps another refresh or snapshot consumption
- **THEN** operations serialize or fail clearly without exposing a partial or mixed snapshot

### Requirement: Unattended development profile initialization

Before launching Anki, the development command SHALL prepare valid preferences selecting English and a dedicated development profile. Both empty and snapshot-seeded sessions SHALL bypass the first-run language dialog and profile picker, omit production sync credentials, and disable automatic collection and media sync.

#### Scenario: Launch an empty development profile
- **WHEN** the developer starts empty mode in a fresh temporary base
- **THEN** Anki opens the dedicated development profile without requesting a language choice or profile selection
- **AND** automatic collection and media sync are disabled and no production sync credentials are present

#### Scenario: Launch a snapshot-seeded development profile
- **WHEN** the developer starts a session from a valid snapshot
- **THEN** Anki opens the copied collection in the dedicated development profile without requesting a language choice or profile selection
- **AND** automatic collection and media sync are disabled and no production sync credentials are present

#### Scenario: Preference initialization fails
- **WHEN** the command cannot prepare valid development preferences
- **THEN** it reports the failure and does not launch Anki into interactive first-run setup
