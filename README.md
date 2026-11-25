# Mindful
An Anki Add-On to Enable Learning Card Management in Anki

## Editing a note

1. Open the Anki Browser and select exactly one note. In card mode, select one
   or more cards that belong to the same note.
2. Choose **Notes > Mindful: Edit Note...**, right-click the table and choose
   **Mindful: Edit Note...**, or press `Ctrl+Shift+O` (`Cmd+Shift+O` on macOS).
   The action is disabled when no note or several notes are selected.
3. Edit the fields and click **Save**.

The editor shows every field of the note, in the note type's order. Each field is
labeled **Markdown** or **HTML**:

- **Markdown**: the field uses only bold, italic, inline code, links, images,
  lists and line breaks, and converts back to the same content. Saving writes
  standard Anki HTML.
- **HTML**: the field contains other markup, such as colors, tables or code
  blocks. It is shown and saved as raw HTML, exactly as typed. Hover over the
  badge for the reason.

Cloze deletions (`{{c1::answer::hint}}`), sound tags (`[sound:file.mp3]`),
MathJax (`\(...\)` and `\[...\]`) and image file names stay unchanged as editable
text. Notes are never stored as Markdown.

Saving writes only the fields you changed, as one step you can reverse with
**Edit > Undo** in Anki. If the note was changed elsewhere or deleted after you
opened it, nothing is saved and your edits stay in the editor. Closing the editor,
opening another note, or closing the Browser with unsaved edits asks before
discarding them.

To change the shortcut, open **Tools > Add-ons**, select Mindful and click
**Config**. Set `edit_note_shortcut` to another shortcut, such as `Ctrl+Alt+E`,
or to `""` to remove it. Invalid values fall back to `Ctrl+Shift+O`. The change
applies to Browser windows opened afterwards.

## Development setup

Install [uv](https://docs.astral.sh/uv/) and Python 3.13, then run from the
repository root:

```sh
uv sync
uv run mindful
```

The command prints `Hello from mindful!`. The development dependencies include
matching Anki and aqt packages; the add-on uses Anki's own runtime when installed.

## Version policy

Releases start from a development version, `X.Y.Z.devN`, and use `X.Y.Z` for
the stable release and `vX.Y.Z` for its tag. After publication, the next patch,
minor, or major development cycle starts at `X.Y.Z.dev0`. Before the first
release, the project and lockfile must both contain `0.1.0.dev0`, rather than
the stable `0.1.0`.

Check the current project version and lockfile consistency from the repository
root:

```sh
uv version --short
uv lock --check
```

## Releasing

Releases must be run on macOS, where the script verifies the extracted
installer with disposable Anki directories. Start from a clean `main` that
matches `origin/main`, with a development version, no existing release tag,
and an authenticated GitHub CLI. Git, uv, gh, zip, and unzip are required.

Preview the release, then select the next `patch`, `minor`, or `major`
development cycle and confirm interactively:

```sh
scripts/release.sh --dry-run --next-bump patch
scripts/release.sh --next-bump patch
```

The script runs the quality gates in an isolated worktree, publishes an
annotated tag and two verified GitHub assets, then pushes the next development
commit. The `.ankiaddon` is for direct installation and manual
[AnkiWeb upload](https://ankiweb.net/shared/addons); the ZIP is the macOS
installer bundle. It leaves the original checkout untouched. Verify that it is
clean and still on `main`, then fast-forward it explicitly:

```sh
git status --short --branch
git fetch origin main
git merge --ff-only FETCH_HEAD
```

### Recovering an interrupted release

Keep the reported release area and worktree. A failed network operation may
have succeeded remotely, so inspect the branch, peeled tag, release, and both
asset identities before taking action. Replace the example tag and retained
area below with the values printed by the script. Skip the download and
comparison for any asset the release reports missing:

```sh
tag=v0.1.0
version="${tag#v}"
area="/absolute/path/to/retained-release-area"
git ls-remote origin refs/heads/main "refs/tags/$tag" "refs/tags/$tag^{}"
gh release view "$tag" --repo leohuber/mindful --json tagName,isDraft,assets,url
inspection="$(mktemp -d)"
gh release download "$tag" --repo leohuber/mindful --pattern "mindful-$version.ankiaddon" --dir "$inspection"
gh release download "$tag" --repo leohuber/mindful --pattern "mindful-$version.zip" --dir "$inspection"
cmp "$area/mindful-$version.ankiaddon" "$inspection/mindful-$version.ankiaddon"
cmp "$area/mindful-$version.zip" "$inspection/mindful-$version.zip"
```

If the release reports a missing asset, run only the download and comparison
commands for assets that are present. After confirming the tag and release are
correct, choose the missing name and upload only that retained file:

```sh
missing="mindful-$version.zip"  # Replace with the confirmed missing asset.
gh release upload "$tag" "$area/$missing" --repo leohuber/mindful
```

Never use `--clobber`, overwrite a mismatched asset, force push, delete a
published tag, or blindly repeat an uncertain operation.

If inspection confirms that the validated atomic push did not update either
remote ref, the remote branch still equals the original commit, the remote tag
and release are absent, and the local annotated tag points to the reported
stable commit, the same refs can be pushed together without force:

```sh
stable_commit="<reported-stable-commit>"
git cat-file -t "refs/tags/$tag"
git rev-parse "refs/tags/${tag}^{}"
git push --atomic origin "${stable_commit}:refs/heads/main" "refs/tags/${tag}:refs/tags/$tag"
```

If the branch and tag were published but the GitHub Release is confirmed
absent, verify the retained assets and create the release from those files:

```sh
gh release create "$tag" "$area/mindful-$version.ankiaddon" "$area/mindful-$version.zip" \
  --repo leohuber/mindful --verify-tag --title "Mindful $version" --generate-notes \
  --notes "Install the standalone .ankiaddon through Anki on any supported platform. On macOS, extract the ZIP, quit Anki, and run install.sh; use --upgrade for an existing installation. Upload only the standalone archive to AnkiWeb: https://ankiweb.net/shared/addons"
```

If both assets are published and match but the next-development push failed,
verify that `origin/main` still points at the reported stable commit, then use
the exact non-force push command printed for the retained development commit.
If no development commit was created, inspect the retained worktree first; its
HEAD must be the stable commit and its files must be clean. After confirming
the published state, set the selected version there and inspect the resulting
diff before committing and pushing:

```sh
cd "$area/worktree"
git status --short --branch
next_version=0.1.1.dev0  # Replace with the selected next version.
uv version "$next_version" --no-sync
uv lock --check
git diff -- pyproject.toml uv.lock
git add -- pyproject.toml uv.lock
git commit -m "Start v$next_version" -- pyproject.toml uv.lock
git ls-remote origin refs/heads/main
git push origin HEAD:refs/heads/main
```

Only push after confirming the remote branch still equals the stable commit.
Return to the original checkout for the fast-forward handoff.

## Build and install the add-on

From the repository root, build the direct-install archive:

```sh
uv run python scripts/build_addon.py
```

On any supported desktop platform, install the standalone `.ankiaddon` in Anki
Desktop 26.09.4 or newer: open **Tools > Add-ons > Install from file**, select
the archive, and restart Anki. For a local build, the archive is
`dist/mindful.ankiaddon`. The standalone archive is also the file to upload
manually to [AnkiWeb](https://ankiweb.net/shared/addons).

### macOS installer bundle

The release ZIP contains `install.sh` and the same standalone `.ankiaddon`.
Extract it, quit Anki, and run the installer from the extracted directory:

```sh
unzip mindful-X.Y.Z.zip
cd mindful-X.Y.Z
./install.sh
```

The installer uses macOS system shell and archive tools; it does not download
dependencies. By default it installs into
`~/Library/Application Support/Anki2/addons21/mindful`. Anki's `addons21`
directory must already exist and be writable. It is shared by all profiles
in that Anki data folder, not installed inside an individual profile. Its
parent data folder must also be writable for staging and backups.
For a custom data folder, use its existing absolute `addons21` path:

```sh
./install.sh --addons-dir "/absolute/path/to/Anki2/addons21"
```

An existing Mindful installation is never replaced implicitly. Quit Anki and
request an upgrade explicitly:

```sh
./install.sh --upgrade
./install.sh --upgrade --addons-dir "/absolute/path/to/Anki2/addons21"
```

The installer preserves `meta.json`, `config.json`, and `user_files/`, removes
obsolete packaged code, and reports a complete backup under the data folder's
`mindful-backups/`, outside `addons21`. Keep Anki closed and do not change the
installation until the installer finishes. Restart Anki afterward.

To restore a backup, quit Anki, inspect the reported backup and current
`addons21/mindful`, and move the current installation to a new, unique
location outside `addons21`. Then copy the backup's `mindful` directory into
`addons21`. If the installer reports a retained staging area after an error,
inspect its previous installation as well; it may contain newer changes than
the backup. Never overwrite an installation whose contents you have not checked.

For local development, copy `src/mindful` into Anki's `addons21/mindful`
directory, or symlink that directory to the absolute path of `src/mindful`.
Restart Anki after changing code. Do not mix this development copy with an
installed archive at the same path.

## Disposable-profile smoke test

Quit Anki and launch the desired Desktop release with `-b` followed by an
absolute path to a new, empty temporary directory. On macOS, for example:

```sh
/Applications/Anki.app/Contents/MacOS/Anki -b /absolute/path/to/disposable-anki
```

Create two disposable profiles with sample notes and cards. Close Anki and
record the contents of each profile's `notes` and `cards` tables, including
scheduling fields, from its `collection.anki2` database. Extract the release
ZIP and run its installer with `--addons-dir` pointing to the disposable base's
`addons21`. Restart Anki with the same base; open and switch between profiles
and confirm Mindful is enabled without errors.

Close Anki, place a sample file in `addons21/mindful/user_files/`, and run the
installer again with `--upgrade` and the same `--addons-dir`. Check that the
sample file and any `meta.json` or `config.json` are unchanged and that the
reported backup is outside `addons21`. Restart and check enablement in both
profiles again. Close Anki and compare the same collection tables with the
baseline. Repeat with each supported Desktop release being verified. Never use
a real profile or sync these disposable profiles.
