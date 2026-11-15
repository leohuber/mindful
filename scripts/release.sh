#!/usr/bin/env zsh

set -euo pipefail

readonly REPOSITORY="leohuber/mindful"
readonly BRANCH="main"
readonly -a REQUIRED_FILES=(
    pyproject.toml uv.lock scripts/release.sh scripts/build_addon.py
    scripts/install.sh src/mindful/manifest.json
)

die() {
    print -u2 -- "Error: $*"
    exit 1
}

usage() {
    print -- "Usage: scripts/release.sh [--dry-run] [--next-bump patch|minor|major]"
}

directory_identity() {
    local identity
    if identity="$(stat -f '%d:%i' "$1" 2>/dev/null)"; then
        print -r -- "$identity"
    else
        stat -c '%d:%i' "$1"
    fi
}

check_origin() {
    local fetch_url_text push_url_text url
    local -a urls
    fetch_url_text="$(git remote get-url --all origin)" || die "origin has no fetch URL."
    push_url_text="$(git remote get-url --push --all origin)" || die "origin has no push URL."
    urls=("${(@f)fetch_url_text}" "${(@f)push_url_text}")
    for url in "${urls[@]}"; do
        case "${url:l}" in
            https://github.com/leohuber/mindful(|.git)|git@github.com:leohuber/mindful(|.git)|ssh://git@github.com/leohuber/mindful(|.git)) ;;
            *) die "origin must fetch and push the expected GitHub repository $REPOSITORY." ;;
        esac
    done
}

check_tag_absent() {
    local remote_tag
    if git show-ref --verify --quiet "refs/tags/$tag"; then
        die "Tag $tag already exists locally."
    fi
    remote_tag="$(git ls-remote --tags origin "refs/tags/$tag")" || die "Cannot query remote tags."
    [[ -z "$remote_tag" ]] || die "Tag $tag already exists on origin."
}

check_release_absent() {
    local release_response
    if release_response="$(gh api --include "repos/$repository/releases/tags/$tag" 2>&1)"; then
        die "A GitHub Release for $tag already exists."
    else
        [[ "$release_response" == *" 404 "* || "$release_response" == *" 404" ]] \
            || die "Cannot verify whether a GitHub Release for $tag exists: $release_response"
    fi
}

dry_run=0
bump=""
while (( $# )); do
    case "$1" in
        --help) usage; exit 0 ;;
        --dry-run) dry_run=1; shift ;;
        --next-bump)
            (( $# >= 2 )) || die "--next-bump requires patch, minor, or major."
            bump="$2"
            shift 2
            ;;
        *) die "Unknown argument: $1" ;;
    esac
done
[[ -z "$bump" || "$bump" == patch || "$bump" == minor || "$bump" == major ]] \
    || die "--next-bump must be patch, minor, or major."

for tool in git uv gh zip unzip zipinfo cmp; do
    command -v "$tool" >/dev/null 2>&1 || die "$tool is required."
done

root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "Run from the Mindful repository root."
[[ "${PWD:A}" == "${root:A}" && -f pyproject.toml && -d src/mindful ]] \
    || die "Run from the Mindful repository root."
[[ "$(git branch --show-current)" == "$BRANCH" ]] || die "The current branch must be $BRANCH."
[[ -z "$(git status --porcelain --untracked-files=normal)" ]] \
    || die "The working tree is dirty; commit or stash all changes first."
git ls-files --error-unmatch -- "${REQUIRED_FILES[@]}" >/dev/null 2>&1 \
    || die "The release files, builder, installer, and manifest must be tracked by Git."
[[ -f scripts/build_addon.py && -f scripts/install.sh && -x scripts/install.sh ]] \
    || die "The add-on builder and executable installer are required."

check_origin

original_head="$(git rev-parse HEAD)"
remote_head="$(git ls-remote --exit-code origin "refs/heads/$BRANCH")" \
    || die "Cannot query origin/$BRANCH."
[[ "${remote_head%%[[:space:]]*}" == "$original_head" ]] \
    || die "$BRANCH must match origin/$BRANCH."
gh auth status >/dev/null 2>&1 || die "GitHub CLI authentication is required."
repository="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" \
    || die "Cannot identify the GitHub repository."
[[ "${repository:l}" == "$REPOSITORY" ]] || die "Expected GitHub repository $REPOSITORY, got $repository."
uv lock --check >/dev/null || die "The lockfile is inconsistent."
current_version="$(uv version --short)" || die "Could not read the project version."
[[ "$current_version" =~ '^[0-9]+\.[0-9]+\.[0-9]+\.dev[0-9]+$' ]] \
    || die "The current version must be an X.Y.Z.devN development version."
stable_version="$(uv version --bump stable --dry-run --short)" \
    || die "Could not preview the stable version."
[[ "$stable_version" =~ '^[0-9]+\.[0-9]+\.[0-9]+$' ]] || die "Invalid stable version."
tag="v$stable_version"
check_tag_absent
check_release_absent

if [[ -z "$bump" ]]; then
    if (( dry_run )); then
        bump=patch
    else
        [[ -t 0 ]] || die "An interactive terminal is required."
        print -u2 -- "Choose the next development version: patch, minor, or major."
        read -r "bump?Choice: " || die "No version bump was selected."
        [[ "$bump" == patch || "$bump" == minor || "$bump" == major ]] \
            || die "Choose patch, minor, or major."
    fi
fi
next_version="$(uv version --bump "$bump" --bump dev=0 --dry-run --short)" \
    || die "Could not preview the next development version."
[[ -z "$(git status --porcelain --untracked-files=normal)" && "$(git rev-parse HEAD)" == "$original_head" ]] \
    || die "The working tree or HEAD changed during preflight."

print -- "Repository: $repository"
print -- "Branch: $BRANCH"
print -- "Development version: $current_version"
print -- "Release version: $stable_version"
print -- "Next development version: $next_version ($bump)"
print -- "Tag: $tag"
print -- "Assets: mindful-$stable_version.ankiaddon, mindful-$stable_version.zip"

if (( dry_run )); then
    exit 0
fi
[[ -t 0 ]] || die "An interactive terminal is required for confirmation."
read -r "answer?Type 'release' to confirm: " || die "Confirmation was not provided."
[[ "$answer" == release ]] || die "Release cancelled."

original_root="$root"
work_dir=""
worktree=""
work_identity=""
addon_path=""
zip_path=""
addon_name="mindful-$stable_version.ankiaddon"
zip_name="mindful-$stable_version.zip"
stable_commit=""
dev_commit=""
release_state="confirmed"
release_completed=0

report_asset_status() {
    local assets asset name present
    if ! assets="$(gh release view "$tag" --repo "$repository" --json assets --jq '.assets[].name' 2>/dev/null)"; then
        print -u2 -- "GitHub Release and asset state could not be inspected; verify it manually."
        return
    fi
    for name in "$addon_name" "$zip_name"; do
        present=0
        for asset in "${(@f)assets}"; do
            if [[ "$asset" == "$name" ]]; then
                present=1
                break
            fi
        done
        if (( ! present )); then
            print -u2 -- "GitHub asset $name: missing from the inspected release."
        elif [[ -f "$work_dir/published/$name" && -f "$work_dir/$name" ]]; then
            if cmp -s "$work_dir/$name" "$work_dir/published/$name"; then
                print -u2 -- "GitHub asset $name: downloaded and matches the retained asset."
            else
                print -u2 -- "GitHub asset $name: downloaded but DOES NOT MATCH the retained asset."
            fi
        else
            print -u2 -- "GitHub asset $name: present; identity not yet verified."
        fi
    done
}

report_recovery() {
    print -u2 -- "Release stopped. Last confirmed state: $release_state."
    [[ -z "$work_dir" ]] || print -u2 -- "Retained release area: $work_dir"
    [[ -z "$worktree" ]] || print -u2 -- "Retained worktree: $worktree"
    [[ -z "$stable_commit" ]] || print -u2 -- "Stable commit: $stable_commit"
    [[ -z "$dev_commit" ]] || print -u2 -- "Next-development commit: $dev_commit"
    [[ -z "$addon_path" || ! -f "$addon_path" ]] || print -u2 -- "Standalone asset: $addon_path"
    [[ -z "$zip_path" || ! -f "$zip_path" ]] || print -u2 -- "Installer asset: $zip_path"
    if [[ -n "$addon_path" && -f "$addon_path" && -n "$zip_path" && -f "$zip_path" ]]; then
        report_asset_status
    fi
    print -u2 -- "Before retrying, inspect the remote branch, annotated tag, GitHub Release, and both asset identities:"
    print -u2 -- "  git ls-remote origin refs/heads/$BRANCH refs/tags/$tag 'refs/tags/$tag^{}'"
    print -u2 -- "  gh release view $tag --repo $repository --json tagName,isDraft,assets,url"
    print -u2 -- "Download existing assets to an empty inspection directory and compare their SHA-256 hashes with the retained assets."
    print -u2 -- "Upload only an asset confirmed missing; do not overwrite mismatched assets or blindly retry an uncertain push."
    print -u2 -- "If publication succeeded but the development push failed, verify origin/$BRANCH is still the stable commit before pushing the retained next-development commit."
    if [[ -n "$stable_commit" && -n "$dev_commit" ]]; then
        print -u2 -- "After verifying both assets and that origin/$BRANCH is $stable_commit, run:"
        print -u2 -- "  git push origin ${dev_commit}:refs/heads/$BRANCH"
    fi
}

cleanup_release() {
    local exit_status=$?
    trap - EXIT
    if (( release_completed && exit_status == 0 )); then
        if [[ -n "$worktree" ]] && ! git -C "$original_root" worktree remove "$worktree"; then
            print -u2 -- "Could not remove the release worktree; retained $work_dir."
        elif [[ -n "$work_dir" && -d "$work_dir" && ! -L "$work_dir" && "$(directory_identity "$work_dir")" == "$work_identity" ]]; then
            rm -rf -- "$work_dir"
        else
            print -u2 -- "Could not verify the release area for cleanup; retained $work_dir."
        fi
    else
        report_recovery
    fi
    exit "$exit_status"
}
trap cleanup_release EXIT

validate_version_change() {
    uv run python - "$1" "$2" <<'PY'
import subprocess
import sys
from pathlib import Path

old, new = (value.encode() for value in sys.argv[1:])
for filename, prefix in (("pyproject.toml", b"\nversion = "), ("uv.lock", b'name = "mindful"\nversion = ')):
    before = subprocess.check_output(["git", "show", f"HEAD:{filename}"])
    after = Path(filename).read_bytes()
    previous = prefix + b'"' + old + b'"\n'
    replacement = prefix + b'"' + new + b'"\n'
    if before.count(previous) != 1 or after != before.replace(previous, replacement, 1):
        sys.exit(f"Unexpected changes in {filename}; only the project version may change.")
PY
}

commit_version() {
    local old_version="$1" new_version="$2" message="$3" changes
    uv version "$new_version" --no-sync || die "Could not set version $new_version."
    [[ "$(uv version --short)" == "$new_version" ]] || die "The version does not match the preview."
    uv lock --check >/dev/null || die "The lockfile is inconsistent."
    validate_version_change "$old_version" "$new_version" || die "Version changes include unrelated edits."
    changes="$(git status --porcelain --untracked-files=all)" || die "Cannot inspect the release worktree."
    [[ "$changes" == $' M pyproject.toml\n M uv.lock' ]] || die "Unexpected changes in the release worktree: $changes"
    git add -- pyproject.toml uv.lock
    git commit -m "$message" -- pyproject.toml uv.lock
    [[ -z "$(git status --porcelain --untracked-files=all)" ]] || die "The release worktree changed during the commit."
}

validate_addon() {
    uv run python - "$addon_path" "$stable_version" "$tag" <<'PY'
import json
import stat
import sys
import tomllib
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from scripts.build_addon import ADDON_FILES

archive_path, version, tag = sys.argv[1:]
source = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
if source["project"]["version"] != version or tag != f"v{version}":
    sys.exit("The stable source version and release tag do not match.")
forbidden = {".git", ".venv", "__pycache__", "tests", "user_files", "anki", "aqt", "PyQt5", "PyQt6", "PySide2", "PySide6"}
with ZipFile(archive_path) as archive:
    entries = archive.infolist()
    names = [entry.filename for entry in entries]
    if len(names) != len(set(names)) or set(names) != set(ADDON_FILES) or archive.testzip() is not None:
        sys.exit("The add-on archive does not match the builder's distribution contract.")
    for entry in entries:
        path = PurePosixPath(entry.filename)
        if path.is_absolute() or ".." in path.parts or forbidden.intersection(path.parts):
            sys.exit(f"Unsafe or excluded add-on entry: {entry.filename}")
        if path.name in {"config.json", "meta.json", ".env"} or path.suffix in {".pyc", ".pyo"}:
            sys.exit(f"Excluded add-on entry: {entry.filename}")
        if not stat.S_ISREG(entry.external_attr >> 16):
            sys.exit(f"The add-on entry is not a regular file: {entry.filename}")
    manifest = json.loads(archive.read("manifest.json"))
    if manifest.get("package") != "mindful" or manifest.get("name") != "Mindful" or "__init__.py" not in names:
        sys.exit("The add-on entry point or manifest identity is invalid.")
PY
}

validate_bundle() {
    uv run python - "$addon_path" "$zip_path" "$package_name" <<'PY'
import stat
import sys
from pathlib import Path
from zipfile import ZipFile

addon, bundle, package = sys.argv[1:]
with ZipFile(bundle) as archive:
    expected = {f"{package}/", f"{package}/install.sh", f"{package}/{Path(addon).name}"}
    names = archive.namelist()
    if len(names) != len(expected) or set(names) != expected or archive.testzip() is not None:
        sys.exit("The installer ZIP has an invalid layout.")
    if not (archive.getinfo(f"{package}/install.sh").external_attr >> 16) & stat.S_IXUSR:
        sys.exit("The bundled installer is not executable.")
    if archive.read(f"{package}/{Path(addon).name}") != Path(addon).read_bytes():
        sys.exit("The bundled and standalone add-on archives differ.")
PY
}

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/mindful-release.XXXXXXXX")" || die "Could not create a release area."
work_dir="$(cd "$work_dir" && pwd -P)" || die "Could not resolve the release area."
work_identity="$(directory_identity "$work_dir")" || die "Could not identify the release area."
worktree="$work_dir/worktree"
git -C "$original_root" worktree add --detach "$worktree" "$original_head" \
    || die "Could not create the isolated release worktree."
release_state="isolated worktree created"
cd "$worktree"

commit_version "$current_version" "$stable_version" "Release $tag"
stable_commit="$(git rev-parse HEAD)"
[[ "$(git rev-parse HEAD^)" == "$original_head" ]] || die "The stable commit has an unexpected parent."
release_state="stable commit created"

uv run pytest tests || die "The test suite failed."
uv run ruff check src/mindful tests scripts || die "Ruff lint failed."
uv run ruff format --check src/mindful tests scripts || die "Ruff formatting failed."
uv run pyrefly check || die "Pyrefly failed."
uv run lint-imports || die "Import architecture checks failed."
uv run python scripts/build_addon.py || die "The add-on build failed."
[[ -z "$(git status --porcelain --untracked-files=all)" ]] || die "The release worktree changed during validation."
package_name="mindful-$stable_version"
addon_path="$work_dir/$addon_name"
zip_path="$work_dir/$zip_name"
[[ -f dist/mindful.ankiaddon ]] || die "The add-on builder did not produce its archive."
cp dist/mindful.ankiaddon "$addon_path"
validate_addon || die "The add-on archive failed validation."

mkdir "$work_dir/$package_name"
cp -p scripts/install.sh "$work_dir/$package_name/install.sh"
cp "$addon_path" "$work_dir/$package_name/$addon_name"
(cd "$work_dir" && zip -qr "$zip_path" "$package_name") || die "Could not build the installer ZIP."
validate_bundle || die "The installer ZIP failed validation."
mkdir -p "$work_dir/verify" "$work_dir/trial Anki/addons21" "$work_dir/trial-home" "$work_dir/trial-cwd"
unzip -q "$zip_path" -d "$work_dir/verify" || die "Could not extract the installer ZIP."
[[ -x "$work_dir/verify/$package_name/install.sh" ]] || die "The extracted installer is not executable."
cmp -s "$addon_path" "$work_dir/verify/$package_name/$addon_name" || die "The extracted archive does not match."
[[ "$(uname -s)" == Darwin ]] || die "Actual macOS installer verification is required before publication."
(
    cd "$work_dir/trial-cwd"
    HOME="$work_dir/trial-home" "$work_dir/verify/$package_name/install.sh" \
        --addons-dir "$work_dir/trial Anki/addons21"
) || die "The extracted installer failed its disposable macOS installation."
unzip -p "$addon_path" __init__.py > "$work_dir/expected-entry.py"
cmp -s "$work_dir/expected-entry.py" "$work_dir/trial Anki/addons21/mindful/__init__.py" \
    || die "The trial installation does not match the add-on archive."
release_state="both assets validated"

[[ "$(git -C "$original_root" rev-parse HEAD)" == "$original_head" && "$(git -C "$original_root" branch --show-current)" == "$BRANCH" ]] \
    || die "The caller's branch or HEAD changed during release preparation."
check_origin
remote_head="$(git ls-remote --exit-code origin "refs/heads/$BRANCH")" || die "Cannot recheck origin/$BRANCH."
[[ "${remote_head%%[[:space:]]*}" == "$original_head" ]] || die "origin/$BRANCH changed during release preparation."
check_tag_absent
check_release_absent
git tag -a "$tag" "$stable_commit" -m "Release $tag" || die "Could not create the annotated release tag."
release_state="annotated tag created locally"
git push --atomic origin "${stable_commit}:refs/heads/$BRANCH" "refs/tags/${tag}:refs/tags/$tag" \
    || die "The atomic branch-and-tag push failed or its outcome is uncertain."
release_state="stable commit and annotated tag pushed"

notes="Install the standalone .ankiaddon through Anki on any supported platform. On macOS, extract the ZIP, quit Anki, and run install.sh; use --upgrade for an existing installation. Upload only the standalone archive to AnkiWeb: https://ankiweb.net/shared/addons"
gh release create "$tag" "$addon_path" "$zip_path" --repo "$repository" \
    --verify-tag --title "Mindful $stable_version" --generate-notes --notes "$notes" \
    || die "GitHub Release creation or asset upload failed; its outcome may be uncertain."
release_state="GitHub Release creation returned success"
published="$(gh release view "$tag" --repo "$repository" --json tagName,isDraft --jq '.tagName + " " + (.isDraft | tostring)')" \
    || die "Could not confirm the GitHub Release."
[[ "$published" == "$tag false" ]] || die "The GitHub Release is not confirmed as published for $tag."
mkdir "$work_dir/published"
gh release download "$tag" --repo "$repository" --pattern "$addon_name" --dir "$work_dir/published" \
    || die "Could not confirm the published standalone asset."
gh release download "$tag" --repo "$repository" --pattern "$zip_name" --dir "$work_dir/published" \
    || die "Could not confirm the published installer asset."
cmp -s "$addon_path" "$work_dir/published/$addon_name" || die "The published standalone asset differs."
cmp -s "$zip_path" "$work_dir/published/$zip_name" || die "The published installer asset differs."
release_state="GitHub Release and both asset identities confirmed"

commit_version "$stable_version" "$next_version" "Start v$next_version"
dev_commit="$(git rev-parse HEAD)"
[[ "$(git rev-parse HEAD^)" == "$stable_commit" ]] || die "The development commit has an unexpected parent."
release_state="next-development commit created"
remote_head="$(git ls-remote --exit-code origin "refs/heads/$BRANCH")" || die "Cannot recheck origin/$BRANCH."
[[ "${remote_head%%[[:space:]]*}" == "$stable_commit" ]] || die "origin/$BRANCH moved after publication."
git push origin "${dev_commit}:refs/heads/$BRANCH" || die "The next-development push failed or its outcome is uncertain."
release_state="next-development commit pushed"
release_completed=1

print -- "Released $tag and started $next_version."
print -- "Standalone archive: https://github.com/$repository/releases/download/$tag/$addon_name"
print -- "macOS installer ZIP: https://github.com/$repository/releases/download/$tag/$zip_name"
print -- "Upload only the standalone archive manually at https://ankiweb.net/shared/addons."
print -- "The caller's checkout was not changed. Verify it is clean and still on $BRANCH, then fast-forward explicitly:"
print -- "  git status --short --branch"
print -- "  git fetch origin $BRANCH"
print -- "  git merge --ff-only FETCH_HEAD"
