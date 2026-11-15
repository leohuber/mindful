#!/bin/bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: install.sh [--addons-dir PATH] [--upgrade]

Install Mindful into Anki's add-ons directory on macOS. Quit Anki first.
The default is ~/Library/Application Support/Anki2/addons21.
Use --addons-dir with an absolute path for a custom Anki data folder.
Use --upgrade to replace an existing Mindful installation and retain a backup.
EOF
}

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

upgrade=0
addons_dir="${HOME:-}/Library/Application Support/Anki2/addons21"
while (( $# )); do
    case "$1" in
        --help) usage; exit 0 ;;
        --upgrade) upgrade=1; shift ;;
        --addons-dir)
            (( $# >= 2 )) || die "--addons-dir requires an absolute path."
            addons_dir="$2"
            shift 2
            ;;
        *) die "Unknown argument: $1" ;;
    esac
done

[[ "$(uname -s)" == Darwin ]] \
    || die "The shell installer supports macOS only. Install the standalone .ankiaddon through Anki instead."
for tool in unzip zipinfo plutil ps awk find diff stat mktemp cp mkdir mv rm tr; do
    command -v "$tool" >/dev/null 2>&1 || die "$tool is required."
done

check_path() {
    local path="$1" rest component current="/"
    [[ "$path" == /* && "$path" != "/" ]] || die "The add-on directory must be an absolute path."
    rest="${path#/}"
    while [[ -n "$rest" ]]; do
        component="${rest%%/*}"
        [[ -n "$component" && "$component" != "." && "$component" != ".." ]] \
            || die "The destination path must not contain empty, . or .. components."
        current="${current%/}/$component"
        [[ ! -L "$current" ]] || die "The destination path contains a symbolic link: $current"
        if [[ "$rest" == */* ]]; then
            rest="${rest#*/}"
        else
            rest=""
        fi
    done
}

check_anki_closed() {
    local processes running
    processes="$(ps -axo comm=)" || die "Could not inspect running processes. Quit Anki and try again."
    running="$(printf '%s\n' "$processes" | awk '{line = tolower($0); sub(/^[[:space:]]+/, "", line); if (line ~ /[^[:space:]]/) seen = 1; if (line ~ /(^|\/)anki$/) found = 1} END {if (!seen) exit 2; print found ? 1 : 0}')" \
        || die "Could not inspect running processes. Quit Anki and try again."
    [[ "$running" == 0 || "$running" == 1 ]] || die "Could not inspect running processes. Quit Anki and try again."
    if [[ "$running" == 1 ]]; then
        die "Anki is running. Quit Anki before installing or upgrading Mindful."
    fi
}

check_tree() {
    local path="$1" unsafe
    unsafe="$(find "$path" ! -type d ! -type f -print)" || die "Could not inspect $path."
    [[ -z "$unsafe" ]] || die "Symbolic links and special files are not supported in $path."
}

compare_trees() {
    local source="$1" destination="$2" item relative source_metadata destination_metadata
    diff -qr "$source" "$destination" >/dev/null || return 1
    find "$source" -print0 > "$work/tree-entries" || return 1
    while IFS= read -r -d '' item; do
        relative="${item#"$source"}"
        source_metadata="$(stat -f '%p:%m:%u:%g' "$item")" || return 1
        destination_metadata="$(stat -f '%p:%m:%u:%g' "$destination$relative")" || return 1
        [[ "$source_metadata" == "$destination_metadata" ]] || return 1
    done < "$work/tree-entries"
}

addons_dir="${addons_dir%/}"
check_path "$addons_dir"
[[ -d "$addons_dir" && -w "$addons_dir" ]] \
    || die "Anki's add-on directory must already exist and be writable: $addons_dir"
resolved_addons_dir="$(cd "$addons_dir" && pwd -P)" || die "Could not resolve the add-on directory."
[[ "$resolved_addons_dir" == "$addons_dir" ]] || die "The destination path changed or contains a symbolic link."
addons_dir="$resolved_addons_dir"
parent_dir="${addons_dir%/*}"
target="$addons_dir/mindful"
existing=0
[[ ! -L "$target" ]] || die "Mindful is a symbolic link. Remove the development link manually first."
if [[ -e "$target" ]]; then
    [[ -d "$target" ]] || die "The Mindful destination is not a directory: $target"
    (( upgrade )) || die "Mindful already exists. Use --upgrade to replace it with a retained backup."
    check_tree "$target"
    existing=1
fi

bundle_dir="$(cd "$(dirname "$0")" && pwd -P)" || die "Could not resolve the installer directory."
shopt -s nullglob
archives=("$bundle_dir"/*.ankiaddon)
shopt -u nullglob
(( ${#archives[@]} == 1 )) || die "Expected exactly one sibling Mindful .ankiaddon archive."
archive="${archives[0]}"
archive_name="${archive##*/}"
[[ "$archive_name" =~ ^mindful-[0-9]+\.[0-9]+\.[0-9]+\.ankiaddon$ && -f "$archive" && ! -L "$archive" ]] \
    || die "The sibling archive must be a regular mindful-X.Y.Z.ankiaddon file."

validate_archive() {
    local entries types total count entry lowered seen=$'\n' kind package name has_init=0 has_manifest=0
    unzip -tqq "$archive" >/dev/null 2>&1 || die "The add-on archive is corrupt or unreadable."
    entries="$(zipinfo -1 "$archive")" || die "Could not list archive entries."
    total="$(zipinfo -t "$archive" | awk 'NR == 1 && $1 ~ /^[0-9]+$/ {print $1}')" \
        || die "Could not inspect the archive."
    [[ "$total" =~ ^[0-9]+$ && "$total" -gt 0 ]] || die "The archive has no valid entries."
    count="$(printf '%s\n' "$entries" | awk 'END {print NR}')"
    [[ "$count" -eq "$total" ]] || die "The archive has ambiguous entry names."
    types="$(zipinfo -l "$archive" | awk 'NR > 2 && $1 ~ /^[-dlcbps?]/ {print substr($1, 1, 1)}')" \
        || die "Could not inspect archive entry types."
    count="$(printf '%s\n' "$types" | awk 'END {print NR}')"
    [[ "$count" -eq "$total" ]] || die "Could not verify every archive entry type."
    exec 3< <(printf '%s\n' "$types")
    while IFS= read -r entry; do
        IFS= read -r kind <&3 || die "Could not verify an archive entry type."
        [[ "$entry" =~ ^[A-Za-z0-9_./-]+$ && "$entry" != /* ]] \
            || die "Unsafe archive entry: $entry"
        case "/${entry%/}/" in
            *"/../"*|*"/./"*|*"//"*) die "Unsafe archive entry: $entry" ;;
        esac
        case "$entry" in
            */) [[ "$kind" == d ]] || die "Invalid archive directory entry: $entry" ;;
            *) [[ "$kind" == - ]] || die "Archive entries must be regular files or directories: $entry" ;;
        esac
        lowered="$(printf '%s' "${entry%/}" | tr '[:upper:]' '[:lower:]')"
        case "$lowered" in
            meta.json|config.json|user_files|user_files/*) die "The archive contains reserved user data: $entry" ;;
        esac
        case "$seen" in
            *$'\n'"$lowered"$'\n'*) die "The archive contains duplicate or ambiguous entries: $entry" ;;
        esac
        seen="$seen$lowered"$'\n'
        [[ "$entry" != "__init__.py" ]] || has_init=1
        [[ "$entry" != "manifest.json" ]] || has_manifest=1
    done <<< "$entries"
    exec 3<&-
    (( has_init && has_manifest )) || die "The archive lacks the add-on entry point or manifest."
    package="$(unzip -p "$archive" manifest.json | plutil -extract package raw -o - -- -)" \
        || die "Could not read the add-on manifest."
    name="$(unzip -p "$archive" manifest.json | plutil -extract name raw -o - -- -)" \
        || die "Could not read the add-on manifest."
    [[ "$package" == mindful && "$name" == Mindful ]] || die "The archive is not the Mindful add-on."
}

validate_archive
check_anki_closed

for candidate in "$addons_dir"/*; do
    [[ -e "$candidate" || -L "$candidate" ]] || continue
    [[ "$candidate" != "$target" ]] || continue
    if [[ -L "$candidate" ]]; then
        case "${candidate##*/}" in
            *[Mm]indful*) die "Another Mindful development link needs manual resolution: $candidate" ;;
        esac
    fi
    [[ -d "$candidate" && -f "$candidate/manifest.json" && ! -L "$candidate/manifest.json" ]] || continue
    package="$(plutil -extract package raw -o - -- "$candidate/manifest.json" 2>/dev/null || true)"
    [[ "$package" != mindful ]] || die "Another Mindful installation needs manual resolution: $candidate"
done

work=""
backup=""
backup_verified=0
phase="unchanged"
work_identity=""
cleanup() {
    local exit_status=$?
    trap - EXIT
    if [[ -n "$work" && -d "$work" && ! -L "$work" ]]; then
        if (( exit_status == 0 )) && [[ "$phase" == complete && "$(stat -f '%d:%i' "$work")" == "$work_identity" ]]; then
            rm -rf -- "$work"
        else
            printf 'Installer stopped; retained staging area: %s\n' "$work" >&2
        fi
    fi
    if (( exit_status != 0 )); then
        if [[ -n "$backup" ]]; then
            if (( backup_verified )); then
                printf 'Verified backup: %s/mindful\n' "$backup" >&2
            else
                printf 'Incomplete backup (do not restore): %s\n' "$backup" >&2
            fi
        fi
        if [[ "$phase" == moving-old || "$phase" == old-moved || "$phase" == creating-target || "$phase" == target-created ]]; then
            printf 'Do not overwrite a changed target. With Anki closed, inspect %s before recovering.\n' "$target" >&2
            if [[ -e "$work/previous/mindful" || -L "$work/previous/mindful" ]]; then
                printf 'Previous installation, possibly containing newer changes: %s/previous/mindful\n' "$work" >&2
            fi
            if (( backup_verified )); then
                printf 'Restore from the verified backup only after inspecting both locations.\n' >&2
            fi
        fi
    fi
    exit "$exit_status"
}
trap cleanup EXIT

check_path "$addons_dir"
work="$(mktemp -d "$parent_dir/.mindful-install.XXXXXXXX")" \
    || die "Could not create a staging directory beside addons21."
work_identity="$(stat -f '%d:%i' "$work")" || die "Could not identify the staging directory."
stage="$work/new/mindful"
mkdir -p "$stage"
unzip -q "$archive" -d "$stage" || die "Could not extract the add-on into staging."
check_tree "$stage"

if (( existing )); then
    [[ -d "$target" && ! -L "$target" ]] || die "The existing installation changed before backup."
    target_identity="$(stat -f '%d:%i' "$target")" || die "Could not identify the existing installation."
    backup_root="$parent_dir/mindful-backups"
    [[ ! -L "$backup_root" ]] || die "The backup directory is a symbolic link."
    if [[ ! -e "$backup_root" ]]; then
        mkdir "$backup_root" || die "Could not create the backup directory."
    fi
    [[ -d "$backup_root" && -w "$backup_root" ]] || die "The backup directory is not writable."
    backup="$(mktemp -d "$backup_root/mindful.XXXXXXXX")" || die "Could not create a backup."
    cp -pR "$target" "$backup/mindful" || die "Could not copy the existing installation to the backup."
    check_tree "$backup/mindful"
    compare_trees "$target" "$backup/mindful" || die "The backup does not match the existing installation."
    backup_verified=1
    for preserved in meta.json config.json user_files; do
        if [[ -e "$backup/mindful/$preserved" ]]; then
            cp -pR "$backup/mindful/$preserved" "$stage/$preserved" \
                || die "Could not preserve $preserved."
        fi
    done
    check_tree "$target"
    [[ "$(stat -f '%d:%i' "$target")" == "$target_identity" ]] \
        || die "The existing installation changed during backup."
    compare_trees "$target" "$backup/mindful" || die "The existing installation changed during backup."
    check_anki_closed
    mkdir "$work/previous"
    phase="moving-old"
    mv "$target" "$work/previous/" || die "Could not move the old installation into staging."
    phase="old-moved"
    [[ ! -L "$work/previous/mindful" && "$(stat -f '%d:%i' "$work/previous/mindful")" == "$target_identity" ]] \
        || die "The existing installation changed before replacement."
    compare_trees "$work/previous/mindful" "$backup/mindful" \
        || die "The existing installation changed before replacement."
else
    check_anki_closed
fi

phase="creating-target"
mkdir "$target" || die "The Mindful destination appeared or could not be created; it was not overwritten."
phase="target-created"
target_identity="$(stat -f '%d:%i' "$target")" || die "Could not identify the new installation directory."
if ! (
    cd "$target" &&
        [[ ! -L "$target" && "$(stat -f '%d:%i' .)" == "$target_identity" && "$(stat -f '%d:%i' "$target")" == "$target_identity" ]] &&
        cp -pRn "$stage/." "./"
); then
    die "Could not safely copy Mindful into the add-on directory."
fi
[[ ! -L "$target" && "$(stat -f '%d:%i' "$target")" == "$target_identity" ]] \
    || die "The Mindful destination changed during installation."
diff -qr "$stage" "$target" >/dev/null || die "The destination changed during installation."
phase="complete"
printf 'Installed Mindful in %s. Restart Anki to use it.\n' "$target"
[[ -z "$backup" ]] || printf 'Backup retained at %s/mindful\n' "$backup"
