# anki-addon-lifecycle Specification

## Purpose

Enable Mindful to load safely within supported Anki Desktop releases without disrupting profiles or existing command-line use.

## Requirements

### Requirement: Supported Anki releases load the add-on

Mindful SHALL load as an add-on in Anki Desktop 26.09.4 and newer using the Python runtime supplied by Anki.

#### Scenario: Baseline release starts the add-on
- **GIVEN** Mindful is installed and enabled in Anki Desktop 26.09.4
- **WHEN** Anki starts with its bundled Python 3.13 runtime
- **THEN** Mindful loads without an import or initialization error

#### Scenario: A later supported release starts the add-on
- **GIVEN** Mindful is installed and enabled in a later supported Anki Desktop release
- **WHEN** Anki starts
- **THEN** Mindful loads without an import or initialization error

### Requirement: Add-on folder names are independent of imports

Mindful SHALL load regardless of whether its installed add-on directory has a descriptive name or an AnkiWeb numeric identifier.

#### Scenario: AnkiWeb assigns a numeric directory
- **GIVEN** Mindful is installed in an add-on directory named with its numeric AnkiWeb identifier
- **WHEN** Anki loads the add-on
- **THEN** its internal modules load successfully without relying on the directory being named `mindful`

### Requirement: Startup does not require an open profile

Mindful SHALL initialize without accessing a collection before a profile is available.

#### Scenario: Anki starts before a profile is open
- **WHEN** Anki loads Mindful before opening a profile
- **THEN** initialization completes without reading or writing a collection

### Requirement: Foundation leaves collections unchanged

Loading Mindful and opening, closing, or switching profiles SHALL NOT modify collection data in this foundation.

#### Scenario: A user switches profiles
- **GIVEN** Mindful is enabled
- **WHEN** the user opens, closes, or switches Anki profiles
- **THEN** Mindful does not change any profile's notes, cards, or scheduling data

### Requirement: Existing command remains usable

The existing `mindful` command SHALL remain usable outside a running Anki Desktop session.

#### Scenario: Run the placeholder command
- **WHEN** a user runs `mindful` outside Anki
- **THEN** it prints `Hello from mindful!` without requiring an active Anki window
