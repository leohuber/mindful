# anki-addon-releases Specification

## Purpose

Provide a safe, repeatable release process for distributing Mindful's Anki add-on through GitHub.

## Requirements

### Requirement: Releases start from a development version

The release workflow SHALL accept only a project version of the form `X.Y.Z.devN` and derive the stable release version `X.Y.Z`.

#### Scenario: Preview a development version
- **GIVEN** Mindful's version is `0.1.0.dev0`
- **WHEN** a maintainer previews a release
- **THEN** the workflow identifies the release version as `0.1.0` and the tag as `v0.1.0`

#### Scenario: Reject a stable input version
- **GIVEN** Mindful's version is `0.1.0`
- **WHEN** a maintainer starts a release
- **THEN** the workflow reports that a development version is required and makes no release changes

### Requirement: Release preview requires confirmation

The workflow SHALL display the versions, tag, repository, branch, and both assets to be published before requesting explicit confirmation.

#### Scenario: Preview without publishing
- **WHEN** a maintainer runs the release preview
- **THEN** it displays the proposed release and next development versions without modifying project files or Git refs, pushing, or publishing

#### Scenario: Decline confirmation
- **WHEN** a maintainer declines or does not provide confirmation
- **THEN** the workflow stops without creating release commits, tags, or publications

### Requirement: Release preflight rejects unsafe state

The workflow SHALL stop before release changes if the checkout, remote, authentication, required tools, version files, or target release tag are not ready.

#### Scenario: Dirty checkout or wrong branch
- **GIVEN** the checkout contains staged, unstaged, or untracked changes, or is not on `main`
- **WHEN** a maintainer starts a release
- **THEN** the workflow reports the problem and creates no release commit or tag

#### Scenario: Existing tag or divergent remote
- **GIVEN** the intended tag already exists locally or remotely, or local `main` differs from the remote branch
- **WHEN** a maintainer starts a release
- **THEN** the workflow stops rather than replacing the tag or changing the remote branch

### Requirement: Quality checks gate publication

The workflow SHALL run the project's required quality checks and validate both the add-on archive and installer ZIP before publishing.

#### Scenario: A quality check fails
- **WHEN** a required check or archive validation fails
- **THEN** no release tag is pushed and no GitHub Release is published

### Requirement: Publish the tagged add-on and installer assets

The workflow SHALL publish the `.ankiaddon` archive and a ZIP containing that archive and `install.sh`, both built from the stable release commit, as assets of the matching GitHub Release.

#### Scenario: Publish a successful release
- **GIVEN** the stable release version is `0.1.0` and validation succeeds
- **WHEN** the maintainer completes the release
- **THEN** the remote has an annotated `v0.1.0` tag for the stable release commit and a GitHub Release with generated notes, `mindful-0.1.0.ankiaddon`, and `mindful-0.1.0.zip`

#### Scenario: Atomic publication of branch and tag is rejected
- **WHEN** the remote rejects the atomic branch-and-tag push
- **THEN** the workflow does not create the GitHub Release or fall back to separate pushes

### Requirement: Installer ZIP contains the verified add-on

The release ZIP SHALL contain one versioned directory with executable `install.sh` and the byte-identical standalone `.ankiaddon` asset, without a wheel, dependency environment, development files, or user data. The `.ankiaddon` SHALL retain the existing direct-install archive layout.

#### Scenario: Inspect an installer bundle
- **WHEN** a user extracts `mindful-0.1.0.zip`
- **THEN** `mindful-0.1.0/install.sh` is executable and its sibling `mindful-0.1.0.ankiaddon` matches the standalone release asset byte for byte

#### Scenario: Bundle validation fails
- **GIVEN** the nested archive differs from the standalone asset or the installer is missing or not executable
- **WHEN** the workflow validates the release assets
- **THEN** publication stops before the branch and tag push

### Requirement: macOS installer selects Anki's add-on directory

The bundled installer SHALL support macOS, detect `~/Library/Application Support/Anki2/addons21` by default, accept `--addons-dir` to override it, and install into its `mindful` child. It SHALL require an existing writable add-on directory and Anki to be closed, and SHALL reject detected running Anki or unsupported platforms without installation changes.

#### Scenario: Install into the default Anki data folder
- **GIVEN** Anki is closed and the default add-on directory exists
- **WHEN** a macOS user runs the extracted `install.sh`
- **THEN** Mindful's files are installed under `addons21/mindful`, not inside an individual profile, and the user receives restart instructions

#### Scenario: Install into a custom Anki data folder
- **GIVEN** Anki is closed and a custom data folder has an existing writable `addons21` directory
- **WHEN** the user runs `install.sh --addons-dir "/custom path/addons21"`
- **THEN** only that directory's `mindful` installation is targeted

#### Scenario: Reject an unavailable destination or running Anki
- **GIVEN** the selected directory is missing or unwritable, or Anki is detected running
- **WHEN** the user runs the installer
- **THEN** the installer stops with corrective guidance without copying add-on files

#### Scenario: Use another platform
- **WHEN** a user runs `install.sh` outside macOS
- **THEN** it makes no installation changes and directs the user to install the standalone `.ankiaddon` through Anki

### Requirement: Installer validates input before changing an installation

The installer SHALL validate its sibling archive and destination before installation changes, reject unsafe archive paths, symbolic links, and unexpected add-on identity, and extract only the packaged add-on files. It SHALL work independently of the caller's working directory without downloading software or requiring a separate Python environment.

#### Scenario: Run from a different directory
- **GIVEN** the extracted bundle path contains spaces and the caller is in another directory
- **WHEN** the user invokes the bundle's `install.sh`
- **THEN** it uses the sibling archive and selected destination without accessing another archive or requiring network access

#### Scenario: Reject unsafe input
- **GIVEN** the archive is missing, corrupt, has traversal paths or symlink entries, lacks the expected entry point or manifest identity, or the destination uses symbolic links
- **WHEN** the installer validates input
- **THEN** it stops without changing an existing installation or writing outside the selected destination and its owned staging or backup area

### Requirement: Explicit upgrades preserve user data and recovery state

The installer SHALL refuse an existing Mindful installation unless `--upgrade` is supplied. An explicit upgrade SHALL retain a complete backup outside `addons21`, preserve existing `meta.json` (which holds the user's configuration changes) and `user_files/`, and replace packaged code, including the default `config.json`, without retaining stale modules. It SHALL not modify other add-ons or profile collections.

#### Scenario: Refuse an implicit overwrite
- **GIVEN** the destination already contains Mindful
- **WHEN** the user runs the installer without `--upgrade`
- **THEN** the installer stops without modifying that installation and explains how to request an explicit upgrade

#### Scenario: Complete an explicit upgrade
- **GIVEN** Mindful contains user metadata, configuration, user files, and obsolete packaged modules
- **WHEN** the user runs `install.sh --upgrade` with Anki closed
- **THEN** the new code replaces the old code, the user-owned files retain their contents, obsolete packaged modules are absent, and the complete backup location is reported

#### Scenario: Upgrade fails
- **WHEN** backup, staging, or replacement fails during an explicit upgrade
- **THEN** the prior installation remains intact or recoverable from the retained backup, preserved user data is not discarded, and the installer reports the state and recovery path rather than success

### Requirement: Start the next development version

After GitHub publication, the workflow SHALL commit and push the maintainer-selected patch, minor, or major next development version while keeping project and lockfile versions consistent.

#### Scenario: Start the next patch development cycle
- **GIVEN** release `0.1.0` has been published and the maintainer selected a patch bump
- **WHEN** the workflow completes
- **THEN** the remote branch contains a subsequent commit with version `0.1.1.dev0` and a matching lockfile

### Requirement: Failures preserve changes and support recovery

The workflow SHALL preserve unrelated local changes and published history, and provide recovery information when a release stops after creating release state.

#### Scenario: Another process changes the checkout
- **WHEN** unrelated changes appear during a release or before cleanup
- **THEN** the workflow does not overwrite or discard those changes

#### Scenario: Publication outcome is uncertain
- **GIVEN** a network failure leaves the remote push or GitHub publication outcome uncertain
- **WHEN** the workflow stops
- **THEN** it retains both release assets, identifies the last known state, and directs the maintainer to inspect the remote and both asset identities before retrying

#### Scenario: Only one release asset was uploaded
- **GIVEN** GitHub publication stopped after uploading only the add-on archive or only the ZIP
- **WHEN** the workflow reports recovery information
- **THEN** it identifies the incomplete asset set and requires inspection before completing publication without blindly overwriting an existing asset

#### Scenario: Next development push fails after publication
- **GIVEN** the GitHub Release has been published
- **WHEN** the next development commit or push fails
- **THEN** the published release and tag remain unchanged and the maintainer receives steps to finish the development transition

### Requirement: AnkiWeb publication is a manual handoff

The workflow SHALL identify the released archive and provide instructions for manually uploading it to AnkiWeb.

#### Scenario: GitHub release completes
- **WHEN** the workflow publishes the GitHub Release
- **THEN** it reports where to obtain the `.ankiaddon` asset and links to the manual AnkiWeb upload process

### Requirement: Document both installation paths

The release documentation SHALL explain macOS ZIP extraction and installer usage, destination overrides, explicit upgrades, retained backups, and the requirement to close Anki. It SHALL identify standalone `.ankiaddon` installation as available on all supported Anki Desktop platforms and as the artifact for manual AnkiWeb upload.

#### Scenario: Choose an installation method
- **WHEN** a user reads the GitHub release installation guidance
- **THEN** they can distinguish the macOS installer ZIP from the standalone Anki archive and find the instructions appropriate to their platform
