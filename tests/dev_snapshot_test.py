import contextlib
import importlib
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    snapshot = importlib.import_module("scripts.dev_snapshot")
finally:
    sys.path.pop(0)


@pytest.fixture
def paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    base = tmp_path / "Anki2"
    profile = base / "Study"
    profile.mkdir(parents=True)
    with sqlite3.connect(profile / snapshot.DATABASE) as db:
        db.execute("create table notes (text text)")
        db.execute("insert into notes values ('original')")
    media = profile / snapshot.MEDIA
    media.mkdir()
    (media / "image.png").write_bytes(b"image")
    store = tmp_path / "Mindful" / "dev-snapshot"
    monkeypatch.setattr(snapshot.dev_common, "require_macos", lambda: None)
    monkeypatch.setattr(snapshot.dev_common, "require_anki_closed", lambda: None)

    def check_database(path: Path) -> None:
        with contextlib.closing(sqlite3.connect(path)) as db:
            assert db.execute("pragma integrity_check").fetchone() == ("ok",)

    monkeypatch.setattr(snapshot, "check_collection", check_database)
    return base, profile, store


def test_capture_and_refresh_are_explicit_and_independent(paths: tuple[Path, Path, Path], tmp_path: Path) -> None:
    base, profile, store = paths
    (profile / "prefs21.db").write_bytes(b"credentials")
    (profile / "backups").mkdir()
    original = (profile / snapshot.DATABASE).read_bytes()
    snapshot.capture(base, "Study", store)
    assert (profile / snapshot.DATABASE).read_bytes() == original
    assert (store / snapshot.MEDIA / "image.png").read_bytes() == b"image"
    assert {p.name for p in store.iterdir()} == {snapshot.DATABASE, snapshot.MEDIA, "manifest.json"}
    assert store.stat().st_mode & 0o777 == 0o700
    assert (store / snapshot.DATABASE).stat().st_mode & 0o777 == 0o600

    working = tmp_path / "working"
    assert snapshot.seed_snapshot(working, store)
    (working / snapshot.MEDIA / "image.png").write_bytes(b"changed")
    assert (store / snapshot.MEDIA / "image.png").read_bytes() == b"image"

    (profile / snapshot.MEDIA / "image.png").write_bytes(b"refreshed")
    snapshot.capture(base, "Study", store)
    assert (store / snapshot.MEDIA / "image.png").read_bytes() == b"refreshed"


@pytest.mark.parametrize("name", ["", ".", "..", "../Study", "/Study", r"Study\other"])
def test_unsafe_profile_names_are_rejected(paths: tuple[Path, Path, Path], name: str) -> None:
    base, _, store = paths
    with pytest.raises(ValueError, match="Profile"):
        snapshot.capture(base, name, store)
    assert not store.exists()


def test_missing_profile_does_not_replace_snapshot(paths: tuple[Path, Path, Path]) -> None:
    base, _, store = paths
    snapshot.capture(base, "Study", store)
    before = (store / snapshot.DATABASE).read_bytes()
    with pytest.raises(FileNotFoundError):
        snapshot.capture(base, "missing", store)
    assert (store / snapshot.DATABASE).read_bytes() == before


def test_snapshot_store_cannot_overlap_the_source_base(paths: tuple[Path, Path, Path]) -> None:
    base, profile, _ = paths
    before = (profile / snapshot.DATABASE).read_bytes()
    with pytest.raises(ValueError, match="must not overlap"):
        snapshot.capture(base, "Study", base / "dev-snapshot")
    assert sorted(path.name for path in base.iterdir()) == ["Study"]
    assert (profile / snapshot.DATABASE).read_bytes() == before


@pytest.mark.parametrize("error", [RuntimeError("running"), subprocess.CalledProcessError(1, "ps")])
def test_uncertain_process_state_prevents_capture(paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch, error: Exception) -> None:
    base, _, store = paths

    def fail() -> None:
        raise error

    monkeypatch.setattr(snapshot.dev_common, "require_anki_closed", fail)
    with pytest.raises(type(error)):
        snapshot.capture(base, "Study", store)
    assert not store.exists()


def test_second_process_check_prevents_publication(paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    base, _, store = paths
    snapshot.capture(base, "Study", store)
    before = (store / snapshot.DATABASE).read_bytes()
    checks = iter([False, True])

    def check() -> None:
        if next(checks):
            msg = "Anki started"
            raise RuntimeError(msg)

    monkeypatch.setattr(snapshot.dev_common, "require_anki_closed", check)
    with pytest.raises(RuntimeError, match="started"):
        snapshot.capture(base, "Study", store)
    assert (store / snapshot.DATABASE).read_bytes() == before


def test_wal_content_is_captured_without_modifying_source(paths: tuple[Path, Path, Path]) -> None:
    base, profile, store = paths
    with sqlite3.connect(profile / snapshot.DATABASE) as db:
        assert db.execute("pragma journal_mode=wal").fetchone() == ("wal",)
        db.execute("insert into notes values ('in wal')")
        db.commit()
        assert (profile / f"{snapshot.DATABASE}-wal").exists()
        source_before = {p.name: p.read_bytes() for p in profile.iterdir() if p.is_file()}
        snapshot.capture(base, "Study", store)
        assert {p.name: p.read_bytes() for p in profile.iterdir() if p.is_file()} == source_before
        with sqlite3.connect(store / snapshot.DATABASE) as copied:
            assert copied.execute("select text from notes order by rowid").fetchall() == [("original",), ("in wal",)]


def test_missing_media_is_treated_as_empty(paths: tuple[Path, Path, Path]) -> None:
    base, profile, store = paths
    (profile / snapshot.MEDIA / "image.png").unlink()
    (profile / snapshot.MEDIA).rmdir()
    snapshot.capture(base, "Study", store)
    assert list((store / snapshot.MEDIA).iterdir()) == []


def test_invalid_database_does_not_replace_existing_snapshot(paths: tuple[Path, Path, Path]) -> None:
    base, profile, store = paths
    snapshot.capture(base, "Study", store)
    before = (store / snapshot.DATABASE).read_bytes()
    (profile / snapshot.DATABASE).write_bytes(b"not sqlite")
    with pytest.raises(sqlite3.DatabaseError):
        snapshot.capture(base, "Study", store)
    assert (store / snapshot.DATABASE).read_bytes() == before


def test_unreadable_source_preserves_snapshot(paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    base, profile, store = paths
    snapshot.capture(base, "Study", store)
    before = (store / snapshot.DATABASE).read_bytes()
    original = (profile / snapshot.DATABASE).read_bytes()

    def unreadable(_source: Path, _destination: Path) -> None:
        msg = "cannot read"
        raise PermissionError(msg)

    monkeypatch.setattr(snapshot, "copy_regular", unreadable)
    with pytest.raises(PermissionError, match="cannot read"):
        snapshot.capture(base, "Study", store)
    assert (store / snapshot.DATABASE).read_bytes() == before
    assert (profile / snapshot.DATABASE).read_bytes() == original


def test_unreadable_media_is_not_silently_skipped(paths: tuple[Path, Path, Path]) -> None:
    base, profile, store = paths
    snapshot.capture(base, "Study", store)
    media = profile / snapshot.MEDIA
    media.chmod(0)
    try:
        with pytest.raises(PermissionError):
            snapshot.capture(base, "Study", store)
    finally:
        media.chmod(0o700)
    assert (store / snapshot.MEDIA / "image.png").read_bytes() == b"image"


@pytest.mark.parametrize("valid", [False, True])
def test_anki_integrity_check_uses_a_disposable_copy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, valid: bool) -> None:
    source = tmp_path / "source.anki2"
    source.write_bytes(b"synthetic database")
    seen = []
    collection = MagicMock()
    collection.db.all.return_value = [["ok" if valid else "corrupt"]]

    def open_collection(path: str) -> MagicMock:
        copy = Path(path)
        assert copy != source
        assert copy.read_bytes() == source.read_bytes()
        seen.append(copy)
        return collection

    monkeypatch.setattr(snapshot, "import_module", lambda module: SimpleNamespace(Collection=open_collection))
    if valid:
        snapshot.check_collection(source)
    else:
        with pytest.raises(ValueError, match="could not validate"):
            snapshot.check_collection(source)
    collection.db.all.assert_called_once_with("PRAGMA integrity_check")
    collection.close.assert_called_once_with()
    assert not seen[0].exists()
    assert source.read_bytes() == b"synthetic database"


@pytest.mark.parametrize("linked", ["profile", "media", "file"])
def test_symlinks_are_rejected(paths: tuple[Path, Path, Path], tmp_path: Path, linked: str) -> None:
    base, profile, store = paths
    if linked == "profile":
        (base / "link").symlink_to(profile, target_is_directory=True)
        name = "link"
    elif linked == "media":
        (profile / snapshot.MEDIA / "image.png").unlink()
        (profile / snapshot.MEDIA).rmdir()
        (profile / snapshot.MEDIA).symlink_to(tmp_path, target_is_directory=True)
        name = "Study"
    else:
        (profile / snapshot.MEDIA / "image.png").unlink()
        (profile / snapshot.MEDIA / "image.png").symlink_to(profile / snapshot.DATABASE)
        name = "Study"
    with pytest.raises(ValueError, match="safe"):
        snapshot.capture(base, name, store)
    assert not store.exists()


def test_source_change_during_capture_preserves_previous_snapshot(paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    base, profile, store = paths
    snapshot.capture(base, "Study", store)
    before = (store / snapshot.MEDIA / "image.png").read_bytes()
    original_copy = snapshot.copy_media

    def copy_and_change(source: Path, destination: Path) -> None:
        original_copy(source, destination)
        (profile / snapshot.MEDIA / "image.png").write_bytes(b"changed since copy")

    monkeypatch.setattr(snapshot, "copy_media", copy_and_change)
    with pytest.raises(RuntimeError, match="changed"):
        snapshot.capture(base, "Study", store)
    assert (store / snapshot.MEDIA / "image.png").read_bytes() == before


def test_overlapping_operations_fail_without_replacing_snapshot(paths: tuple[Path, Path, Path]) -> None:
    base, _, store = paths
    snapshot.capture(base, "Study", store)
    with snapshot.snapshot_lock(store.parent, create=False), pytest.raises(RuntimeError, match="progress"):
        snapshot.capture(base, "Study", store)
    snapshot.validate_snapshot(store)


def test_recovery_state_prevents_capture_and_consumption(paths: tuple[Path, Path, Path], tmp_path: Path) -> None:
    base, _, store = paths
    snapshot.capture(base, "Study", store)
    store.rename(snapshot.recovery_path(store))
    with pytest.raises(RuntimeError, match="recovery"):
        snapshot.capture(base, "Study", store)
    with pytest.raises(RuntimeError, match="recovery"):
        snapshot.seed_snapshot(tmp_path / "work", store)


def test_invalid_existing_directory_is_not_replaced(paths: tuple[Path, Path, Path]) -> None:
    base, _, store = paths
    store.mkdir(parents=True)
    (store / "important").write_text("preserve")
    with pytest.raises(ValueError, match="snapshot entries"):
        snapshot.capture(base, "Study", store)
    assert (store / "important").read_text() == "preserve"


def test_special_media_entry_is_rejected(paths: tuple[Path, Path, Path]) -> None:
    base, profile, store = paths
    os.mkfifo(profile / snapshot.MEDIA / "pipe")
    with pytest.raises(ValueError, match="safe"):
        snapshot.capture(base, "Study", store)
    assert not store.exists()


def test_symlinked_source_ancestor_is_rejected(paths: tuple[Path, Path, Path], tmp_path: Path) -> None:
    base, _, store = paths
    alias = tmp_path / "linked-base"
    alias.symlink_to(base, target_is_directory=True)
    with pytest.raises(ValueError, match="safe"):
        snapshot.capture(alias, "Study", store)


@pytest.mark.parametrize("rollback_fails", [False, True])
def test_failed_publication_preserves_previous_snapshot(
    paths: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch, rollback_fails: bool
) -> None:
    base, profile, store = paths
    snapshot.capture(base, "Study", store)
    (profile / snapshot.MEDIA / "image.png").write_bytes(b"new")
    rename = Path.rename
    recovery = snapshot.recovery_path(store)

    def fail_publish(path: Path, target: Path) -> Path:
        if path.name.startswith(".dev-snapshot-stage-") or (rollback_fails and path == recovery):
            msg = "rename failed"
            raise OSError(msg)
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", fail_publish)
    with pytest.raises(OSError if not rollback_fails else RuntimeError, match=r"rename failed|retained at"):
        snapshot.capture(base, "Study", store)
    preserved = recovery if rollback_fails else store
    assert (preserved / snapshot.MEDIA / "image.png").read_bytes() == b"image"


def test_empty_snapshot_and_unsafe_entries_are_rejected(paths: tuple[Path, Path, Path], tmp_path: Path) -> None:
    base, profile, store = paths
    assert not snapshot.seed_snapshot(tmp_path / "empty", store)
    snapshot.capture(base, "Study", store)
    (store / snapshot.MEDIA / "image.png").unlink()
    (store / snapshot.MEDIA / "image.png").symlink_to(profile / snapshot.DATABASE)
    with pytest.raises(ValueError, match="safe"):
        snapshot.seed_snapshot(tmp_path / "work", store)


def test_wrapper_is_executable_and_help_is_noninteractive(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "dev_snapshot.sh"
    assert os.access(script, os.X_OK)
    monkeypatch.setattr(sys, "argv", ["dev_snapshot", "--help"])
    with pytest.raises(SystemExit) as result:
        snapshot.main()
    assert result.value.code == 0
    assert "--profile" in capsys.readouterr().out
