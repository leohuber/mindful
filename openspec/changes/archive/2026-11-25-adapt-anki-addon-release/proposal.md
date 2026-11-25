# Proposal

## Why

The copied release script targets Luna's package, installer, and configuration rather than Mindful's Anki add-on. Mindful needs a safe, repeatable release process with a directly installable archive and a convenient macOS installer bundle.

## What Changes

- Adapt the release script to use Mindful's `.ankiaddon` builder and publish both `mindful-X.Y.Z.ankiaddon` and `mindful-X.Y.Z.zip` as GitHub Release assets.
- Package an executable `install.sh` alongside the identical `.ankiaddon` archive in the ZIP. The macOS-only script detects Anki's default `addons21` directory, permits an explicit override, and copies the add-on there with Anki closed.
- Support explicit upgrades with a retained backup and preservation of Anki-managed metadata, configuration, and user files; other platforms use the standalone `.ankiaddon` asset.
- Set the initial project version to `0.1.0.dev0` and retain the development-to-stable-to-next-development version cycle; stable versions are not valid release inputs.
- Preserve annotated release tags, generated GitHub release notes, and the maintainer's choice of the next patch, minor, or major development version.
- Add a safe preview and confirmation, release preflight and quality checks, and recovery guidance that does not overwrite unrelated changes or rewrite history.
- Document that AnkiWeb publication is a separate manual upload of the released archive. Automatic AnkiWeb publication is out of scope.

## Capabilities

### New Capabilities

- `anki-addon-releases`: Version, validate, and publish Mindful's add-on releases and macOS installer bundles to GitHub with recoverable publication and installation handling.

### Modified Capabilities

None.

## Impact

- Affects `scripts/release.sh`, new `scripts/install.sh`, `pyproject.toml`, `uv.lock`, release and installation documentation, and focused release-workflow and installer tests.
- Reuses the existing `scripts/build_addon.py` builder and the distribution contract established by archived `establish-anki-addon-architecture`. The ZIP wraps its archive rather than introducing a second add-on build or changing the direct-install archive format.
- Installer consumers on macOS require system shell and archive tools, not a separate Python environment or bundled Anki/Qt runtime.
- Requires maintainer access to the GitHub repository for publication; tests must use isolated local repositories and a simulated GitHub client rather than publishing a real release.
