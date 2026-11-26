"""Capture a selected Anki profile for disposable development sessions."""

import argparse
import contextlib
import fcntl
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path

from scripts import dev_common

DEFAULT_BASE = Path.home() / "Library/Application Support/Anki2"
SNAPSHOT = Path.home() / "Library/Application Support/Mindful/dev-snapshot"
MANIFEST = {"format": "mindful-dev-snapshot", "version": 1}
DATABASE = "collection.anki2"
MEDIA = "collection.media"


def source_profile(base: Path, name: str) -> Path:
    """Resolve a direct-child profile without accepting symbolic links.

    Returns:
        The selected profile directory.

    Raises:
        ValueError: The profile name or source path is unsafe.
    """
    if not name or name in {".", ".."} or "/" in name or "\\" in name or "\x00" in name:
        msg = "Profile must be a single directory name."
        raise ValueError(msg)
    safe_directory_tree(base)
    profile = base / name
    require_directory(profile)
    require_regular(profile / DATABASE)
    return profile


def safe_directory_tree(path: Path, *, create: bool = False) -> None:
    """Check all directory components and optionally create missing ones."""
    path = path.absolute()
    for component in (*reversed(path.parents), path):
        if create:
            with contextlib.suppress(FileExistsError):
                component.mkdir(mode=0o700)
        require_directory(component)


def require_directory(path: Path) -> None:
    """Reject missing directories and symbolic links.

    Raises:
        ValueError: The path is not a real directory.
    """
    if not stat.S_ISDIR(path.lstat().st_mode):
        msg = f"Not a safe directory: {path}"
        raise ValueError(msg)


def require_regular(path: Path) -> None:
    """Reject symbolic links and special filesystem entries.

    Raises:
        ValueError: The path is not a regular file.
    """
    if not stat.S_ISREG(path.lstat().st_mode):
        msg = f"Not a safe regular file: {path}"
        raise ValueError(msg)


def fingerprint(path: Path) -> tuple[int, int, int, int, int]:
    """Record identity and metadata for change detection.

    Returns:
        Device, inode, mode, size, and modification time.
    """
    info = path.lstat()
    return info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns


def _raise_walk_error(error: OSError) -> None:
    raise error


def source_inventory(profile: Path) -> dict[Path, tuple[int, int, int, int, int]]:
    """Enumerate the collection, SQLite companions, and media without links.

    Returns:
        Source paths and their identity and modification metadata.

    """
    entries = {profile: fingerprint(profile)}
    for suffix in ("", "-wal", "-shm", "-journal"):
        path = profile / f"{DATABASE}{suffix}"
        if suffix and not os.path.lexists(path):
            continue
        require_regular(path)
        entries[path] = fingerprint(path)
    media = profile / MEDIA
    if os.path.lexists(media):
        require_directory(media)
        for root, dirs, files in os.walk(media, followlinks=False, onerror=_raise_walk_error):
            directory = Path(root)
            require_directory(directory)
            entries[directory] = fingerprint(directory)
            for name in dirs:
                require_directory(directory / name)
            for name in files:
                path = directory / name
                require_regular(path)
                entries[path] = fingerprint(path)
    return entries


def copy_regular(source: Path, destination: Path) -> None:
    """Copy a regular file without following its final path component.

    Raises:
        ValueError: The source is not a regular file.
    """
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            msg = f"Not a safe regular file: {source}"
            raise ValueError(msg)
        with os.fdopen(descriptor, "rb", closefd=False) as src, destination.open("xb") as dst:
            os.fchmod(dst.fileno(), 0o600)
            shutil.copyfileobj(src, dst)
    finally:
        os.close(descriptor)


def copy_media(source: Path, destination: Path) -> None:
    """Copy media into a private, independently writable directory."""
    destination.mkdir(mode=0o700)
    if not os.path.lexists(source):
        return
    require_directory(source)
    for root, dirs, files in os.walk(source, followlinks=False, onerror=_raise_walk_error):
        src = Path(root)
        require_directory(src)
        dst = destination / src.relative_to(source)
        for name in dirs:
            require_directory(src / name)
            (dst / name).mkdir(mode=0o700)
        for name in files:
            require_regular(src / name)
            copy_regular(src / name, dst / name)


def normalize_database(raw: Path, destination: Path) -> None:
    """Recover a staged SQLite database and write a checked standalone copy."""
    with contextlib.closing(sqlite3.connect(raw)) as source, contextlib.closing(sqlite3.connect(destination)) as target:
        source.backup(target)
    destination.chmod(0o600)
    check_collection(destination)


def check_collection(path: Path) -> None:
    """Validate a disposable database copy using Anki's SQLite collations.

    Raises:
        ValueError: Anki cannot open the collection or its integrity check fails.
    """
    try:
        with tempfile.TemporaryDirectory(prefix="mindful-collection-check-") as directory:
            copy = Path(directory) / DATABASE
            copy_regular(path, copy)
            collection = import_module("anki.collection").Collection(str(copy))
            try:
                if collection.db.all("PRAGMA integrity_check") != [["ok"]]:
                    msg = "The copied collection failed its integrity check."
                    raise ValueError(msg)
            finally:
                collection.close()
    except Exception as exc:
        msg = "Anki could not validate the copied collection."
        raise ValueError(msg) from exc


def validate_snapshot(snapshot: Path) -> None:
    """Validate the snapshot marker, contents, and SQLite integrity.

    Raises:
        ValueError: The snapshot is incomplete or invalid.
    """
    require_directory(snapshot)
    if {entry.name for entry in snapshot.iterdir()} != {"manifest.json", DATABASE, MEDIA}:
        msg = f"Unexpected or missing snapshot entries: {snapshot}"
        raise ValueError(msg)
    manifest = snapshot / "manifest.json"
    require_regular(manifest)
    if json.loads(manifest.read_text(encoding="utf-8")) != MANIFEST:
        msg = f"Unrecognized snapshot format: {snapshot}"
        raise ValueError(msg)
    require_regular(snapshot / DATABASE)
    require_directory(snapshot / MEDIA)
    source_inventory(snapshot)
    check_collection(snapshot / DATABASE)


@contextlib.contextmanager
def snapshot_lock(parent: Path, *, create: bool) -> Iterator[None]:
    """Hold an exclusive lock while publishing or copying a snapshot.

    Raises:
        RuntimeError: Another snapshot operation is in progress.
        ValueError: The lock path is not a regular file.
    """
    safe_directory_tree(parent, create=create)
    descriptor = os.open(parent / ".dev-snapshot.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            msg = "Snapshot lock is not a regular file."
            raise ValueError(msg)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            msg = "Another snapshot operation is in progress."
            raise RuntimeError(msg) from exc
        yield
    finally:
        os.close(descriptor)


def recovery_path(snapshot: Path) -> Path:
    """Return the fixed recovery path for an interrupted replacement.

    Returns:
        Path to the previous snapshot generation.
    """
    return snapshot.with_name(snapshot.name + ".recovery")


def check_recovery(snapshot: Path) -> None:
    """Refuse to proceed when a replacement requires manual recovery.

    Raises:
        RuntimeError: A prior replacement left recovery state.
    """
    recovery = recovery_path(snapshot)
    if os.path.lexists(recovery):
        msg = f"Snapshot recovery is required; inspect {recovery} and {snapshot}."
        raise RuntimeError(msg)


def remove_owned(path: Path, identity: tuple[int, int]) -> None:
    """Remove a directory only if its identity still matches.

    Raises:
        RuntimeError: The directory was replaced.
    """
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != identity:
        msg = f"Snapshot directory changed; refusing cleanup: {path}"
        raise RuntimeError(msg)
    shutil.rmtree(path)


def directory_identity(path: Path) -> tuple[int, int]:
    """Record the identity of a real directory.

    Returns:
        The device and inode.
    """
    require_directory(path)
    info = path.stat()
    return info.st_dev, info.st_ino


def publish(stage: Path, snapshot: Path) -> None:
    """Replace a snapshot while preserving the previous generation on failure.

    Raises:
        RuntimeError: Rollback failed and the previous generation was retained.
    """
    recovery = recovery_path(snapshot)
    previous_identity = None
    if os.path.lexists(snapshot):
        validate_snapshot(snapshot)
        previous_identity = directory_identity(snapshot)
        snapshot.rename(recovery)
    try:
        stage.rename(snapshot)
    except OSError:
        if previous_identity is not None:
            try:
                recovery.rename(snapshot)
            except OSError as rollback_error:
                msg = f"Snapshot publication failed; previous snapshot retained at {recovery}."
                raise RuntimeError(msg) from rollback_error
        raise
    if previous_identity is not None:
        remove_owned(recovery, previous_identity)


def capture(base: Path, name: str, snapshot: Path = SNAPSHOT) -> None:
    """Capture and safely publish a snapshot of one profile.

    Raises:
        RuntimeError: The source profile changed during capture.
        ValueError: The source and snapshot storage paths overlap.
    """
    dev_common.require_macos()
    dev_common.require_anki_closed()
    profile = source_profile(base, name)
    source_base = base.resolve()
    store_parent = snapshot.parent.resolve()
    if source_base.is_relative_to(store_parent) or store_parent.is_relative_to(source_base):
        msg = "The snapshot store and source Anki base must not overlap."
        raise ValueError(msg)
    with snapshot_lock(snapshot.parent, create=True):
        check_recovery(snapshot)
        if os.path.lexists(snapshot):
            validate_snapshot(snapshot)
        before = source_inventory(profile)
        stage = Path(tempfile.mkdtemp(prefix=".dev-snapshot-stage-", dir=snapshot.parent))
        identity = directory_identity(stage)
        try:
            raw_dir = stage / "raw"
            raw_dir.mkdir(mode=0o700)
            for suffix in ("", "-wal", "-shm", "-journal"):
                source = profile / f"{DATABASE}{suffix}"
                if source in before:
                    copy_regular(source, raw_dir / source.name)
            copy_media(profile / MEDIA, stage / MEDIA)
            normalize_database(raw_dir / DATABASE, stage / DATABASE)
            shutil.rmtree(raw_dir)
            (stage / "manifest.json").write_text(json.dumps(MANIFEST), encoding="utf-8")
            (stage / "manifest.json").chmod(0o600)
            validate_snapshot(stage)
            dev_common.require_anki_closed()
            if before != source_inventory(profile):
                msg = "The source profile changed during capture; snapshot not published."
                raise RuntimeError(msg)
            publish(stage, snapshot)
        finally:
            if os.path.lexists(stage):
                remove_owned(stage, identity)


def seed_snapshot(profile: Path, snapshot: Path = SNAPSHOT) -> bool:
    """Copy a saved snapshot into an owned development profile.

    Returns:
        Whether a snapshot was present and copied.
    """
    if not os.path.lexists(snapshot.parent):
        return False
    with snapshot_lock(snapshot.parent, create=False):
        check_recovery(snapshot)
        if not os.path.lexists(snapshot):
            return False
        validate_snapshot(snapshot)
        profile.mkdir(mode=0o700, parents=True, exist_ok=True)
        require_directory(profile)
        copy_regular(snapshot / DATABASE, profile / DATABASE)
        copy_media(snapshot / MEDIA, profile / MEDIA)
        return True


def main() -> None:
    """Capture the requested profile without launching Anki."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, help="name of the production Anki profile")
    parser.add_argument("--anki-base", type=Path, default=DEFAULT_BASE, help="production Anki base directory")
    args = parser.parse_args()
    try:
        capture(args.anki_base, args.profile)
    except (OSError, RuntimeError, ValueError, sqlite3.Error, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Snapshot failed: {exc}\n")
    sys.stdout.write(f"Development snapshot saved at {SNAPSHOT}\n")


if __name__ == "__main__":
    main()
