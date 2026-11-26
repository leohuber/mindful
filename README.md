# Mindful
An Anki Add-On to Enable Learning Card Management in Anki

## Editing a note

1. Open the Anki Browser and select exactly one note. In card mode, select one
   or more cards that belong to the same note.
2. Choose **Notes > Mindful: Edit Note...**, right-click the table and choose
   **Mindful: Edit Note...**, or press `Ctrl+Shift+O` (`Cmd+Shift+O` on macOS).
   The action is disabled when no note or several notes are selected.
3. Edit the fields and click **Save**.

The editor shows every field of the note, in the note type's order, as HTML in a
monospace font with syntax highlighting for tags, attributes, comments, entities,
cloze deletions and MathJax delimiters.

To make HTML easier to read, the editor puts block elements such as `<div>`,
`<p>`, list items and table rows on their own lines, indents nested blocks, and
starts a new line after `<br>`. This formatting is for display only: saving
removes the added line breaks and indentation again, so the stored HTML and the
rendered card stay the same. Inline markup, `<pre>`, `<code>`, `<script>`,
`<style>` and `<textarea>` are never reformatted. A field whose HTML cannot be
formatted and restored exactly, for example because it already contains line
breaks between blocks, is shown and saved exactly as stored. In a formatted
field, a line break you type between two blocks or after `<br>` is also removed
when saving; this only matters for cards whose styling shows line breaks
(`white-space: pre`).

Cloze deletions (`{{c1::answer::hint}}`), sound tags (`[sound:file.mp3]`),
MathJax (`\(...\)` and `\[...\]`) and image file names stay unchanged as editable
text.

The card preview on the right updates as you edit, before saving. The fields and
the preview start with equal widths; drag the divider to resize them. The preview
shows the back of the card by default. Choose a card from the **Card** list, and
use **Front** and **Back** to switch sides. Entries labeled **preview only** are templates or clozes without
a saved card; the label does not guarantee that saving will create one. Images
and MathJax render in the preview, and sound can be played with its play button.
Editing does not automatically restart audio.

The preview never saves edits or creates cards. Card-specific context and add-on
rendering can differ from review, and legacy LaTeX (`[latex]`, `[$]`, `[$$]`)
is not rendered in the live preview. If a preview is unavailable, the fields and
your unsaved edits remain available.

Saving writes only the fields you changed, as one step you can reverse with
**Edit > Undo** in Anki. If the note was changed elsewhere or deleted after you
opened it, nothing is saved and your edits stay in the editor. Closing the editor,
opening another note, or closing the Browser with unsaved edits asks before
discarding them.

Use **< Previous** and **Next >** at the bottom of the editor, or press
`Ctrl+Alt+Left` and `Ctrl+Alt+Right` (`Cmd+Option+Left` and `Cmd+Option+Right` on
macOS), to open the note before or after the Browser's current row. The Browser
selects that note's row, and in card mode further cards of the same note are
skipped. The shortcuts also work while typing in a field; plain arrow keys still
move the text cursor. A button is disabled when the Browser has no row in that
direction. Moving asks before discarding unsaved edits and never saves them.

To change the shortcut, open **Tools > Add-ons**, select Mindful and click
**Config**. Set `edit_note_shortcut` to another shortcut, such as `Ctrl+Alt+E`,
or to `""` to remove it. Invalid values fall back to `Ctrl+Shift+O`. The change
applies to Browser windows opened afterwards.

Set `previous_note_shortcut` and `next_note_shortcut` in the same configuration
to change the editor's navigation shortcuts, or to `""` to remove them. Invalid
values fall back to `Ctrl+Alt+Left` and `Ctrl+Alt+Right`. The change applies to
editor windows opened afterwards.

Set `field_font_size` in the same configuration to change the font size of the
field editors, from `8` to `48` points (default `14`). Invalid values fall back
to `14`. The change applies to editor windows opened afterwards.

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

Releases start from a development version, `X.Y.Z.devN`. At release time,
choose patch, minor, or major relative to the highest stable `vX.Y.Z` tag on
origin. The next development version is automatically the released version
with its patch incremented and `.dev0` appended. For example, after `v0.5.0`,
choosing patch releases `v0.5.1` and starts `0.5.2.dev0`, even if the current
development version is `0.6.0.dev0`. A stable origin tag is required.

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

Preview the available release versions, then choose `patch`, `minor`, or
`major` and confirm interactively:

```sh
scripts/release.sh --dry-run
scripts/release.sh --bump patch
```

Omit `--bump` to select the release type interactively. Use
`--dry-run --bump patch` to preview one candidate without releasing.

The script runs the quality gates in an isolated worktree, publishes an
annotated tag and two verified GitHub assets, then pushes the next development
commit and fast-forwards the original checkout if it is still clean and
unchanged. It verifies that local `main` and origin both point to the
development commit. If synchronization cannot be completed, the release
remains published and the script retains the release area and prints the
expected commit and recovery guidance.

The `.ankiaddon` is for direct installation and manual
[AnkiWeb upload](https://ankiweb.net/shared/addons); the ZIP is the macOS
installer bundle.

After inspecting any local changes and confirming that origin still points to
the reported development commit, synchronize a clean `main` manually:

```sh
git status --short --branch
git ls-remote origin refs/heads/main
git fetch origin main
git merge --ff-only "<reported-development-commit>"
```

### Retained release worktrees

At startup the script lists retained release worktrees. It offers to remove an
identified, inactive managed worktree and its release area only after a separate
confirmation for that area. This permanently deletes retained assets and may
discard unpushed commits; inspect and recover anything needed first. A dry run
lists candidates without removing them. Dirty worktrees are retained.

Older release areas have no ownership marker and are not automatically
removed. Inspect each reported worktree and its associated release area:

```sh
git worktree list
git -C "<reported-worktree>" status --short --branch
git -C "<reported-worktree>" log -1 --oneline
```

Confirm no release is using the area, inspect its assets and commits, and
recover anything needed. Once it is safe to discard, remove that exact
worktree with `git worktree remove "<reported-worktree>"`; inspect and remove
only its reported release area separately. Do not force-remove a dirty
worktree. If the script reports a release lock, first verify no release is
running and inspect the lock before manually clearing a stale lock.

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
the published state, set the next patch development version there and inspect
the resulting diff before committing and pushing:

```sh
cd "$area/worktree"
git status --short --branch
next_version=0.1.1.dev0  # Replace with the release's next patch development version.
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

### Create or refresh a development snapshot

With Anki closed, capture the desired production profile by name:

```sh
./scripts/dev_snapshot.sh --profile "User 1"
```

By default the source is `~/Library/Application Support/Anki2`. For a custom
Anki base, add `--anki-base "/path/to/Anki2"`. Keep Anki closed throughout
capture. The command copies the selected collection and media, not production
preferences, sync credentials, add-ons, or backups. Run it again explicitly
whenever you want to refresh the snapshot; development sessions never refresh
it automatically.

The reusable copy is stored at
`~/Library/Application Support/Mindful/dev-snapshot`, outside this checkout.
It contains private notes and media: protect it, keep it out of source control
and releases, and allow enough disk space for the snapshot and each working
copy. Source changes detected during capture abort the refresh; keep Anki
closed rather than relying on these checks as a filesystem lock.

If replacement is interrupted, the command may report a
`dev-snapshot.recovery` directory alongside `dev-snapshot`. With Anki closed
and no snapshot command running, inspect both paths before deciding which
generation to retain. If only the recovery directory exists, rename it to
`dev-snapshot`; if both exist, move the unwanted generation to a separate
safe location before restoring the desired one. Do not remove production
files or blindly overwrite either generation.

### Temporary macOS development session

With the development environment installed and Anki closed, run:

```sh
./scripts/dev_install.sh
```

The command requires Anki Desktop 26.09.4 or newer at
`/Applications/Anki.app`. It builds the archive and launches Anki in a fresh
temporary base with a dedicated English profile, without the first-run language
dialog or profile picker. When a snapshot exists, the command copies its
collection and media into that profile; otherwise it starts empty. It reports
the selected mode and never refreshes the snapshot. The normal Anki profile,
preferences, and installed add-ons are not changed. Keep other Anki instances
closed while starting the session.

To start empty even when a snapshot exists, for example in automation, use:

```sh
./scripts/dev_install.sh --empty
```

The command prints the temporary base path and deletes it after Anki exits
successfully. **All data created there is disposable**; the reusable snapshot
is retained unchanged. Automatic collection and media sync are disabled and
production credentials are not copied. Do not sign in or enable sync: it can
change remote data. This is not a network sandbox; collection content may
reference external resources. If a session fails or its exit cannot be
confirmed, the command retains the base and reports its path. Before manually
removing it, confirm that no Anki process is still using it.

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

The installer preserves `meta.json` (where Anki stores your configuration
changes) and `user_files/`, installs the new default `config.json`, removes
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
sample file and any `meta.json` are unchanged and that the
reported backup is outside `addons21`. Restart and check enablement in both
profiles again. Close Anki and compare the same collection tables with the
baseline. Repeat with each supported Desktop release being verified. Never use
a real profile or sync these disposable profiles.
