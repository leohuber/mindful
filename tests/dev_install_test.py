import importlib
import stat
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile, ZipInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    dev_install = importlib.import_module("scripts.dev_install")
finally:
    sys.path.pop(0)


def test_build_installs_archive_in_new_base_without_touching_normal_installation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    normal = tmp_path / "normal" / "addons21" / "mindful"
    normal.mkdir(parents=True)
    (normal / "config.json").write_text("normal")
    base = tmp_path / "sandbox"
    base.mkdir()
    archive_path = tmp_path / "build.ankiaddon"
    calls = []

    def build(path: str, *, run_name: str) -> None:
        calls.append((path, run_name))
        with ZipFile(archive_path, "w") as archive:
            archive.writestr("__init__.py", "packaged")
            archive.writestr("core/module.py", "packaged module")

    monkeypatch.setattr(dev_install, "ARCHIVE", archive_path)
    monkeypatch.setattr(dev_install.runpy, "run_path", build)
    dev_install.build_and_install(base)

    assert calls == [(str(dev_install.BUILDER), "__main__")]
    assert (base / "addons21/mindful/__init__.py").read_text() == "packaged"
    assert (base / "addons21/mindful/core/module.py").read_text() == "packaged module"
    assert (normal / "config.json").read_text() == "normal"
    assert sorted(path.name for path in base.iterdir()) == ["addons21"]


@pytest.mark.parametrize("name", ["../outside", "/absolute", "core/../outside", r"core\outside", "core//outside"])
def test_unsafe_archive_paths_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    archive_path = tmp_path / "build.ankiaddon"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(name, "unsafe")
    monkeypatch.setattr(dev_install, "ARCHIVE", archive_path)
    monkeypatch.setattr(dev_install.runpy, "run_path", lambda *args, **kwargs: None)

    with pytest.raises(ValueError, match="Unsafe"):
        dev_install.build_and_install(tmp_path / "sandbox")
    assert not (tmp_path / "outside").exists()


def test_archive_symlinks_are_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    archive_path = tmp_path / "build.ankiaddon"
    info = ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(archive_path, "w") as archive:
        archive.writestr(info, "outside")
    monkeypatch.setattr(dev_install, "ARCHIVE", archive_path)
    monkeypatch.setattr(dev_install.runpy, "run_path", lambda *args, **kwargs: None)

    with pytest.raises(ValueError, match="Unsafe"):
        dev_install.build_and_install(tmp_path / "sandbox")


@pytest.mark.parametrize(("listing", "running"), [("/bin/other\n/Applications/Anki.app/Contents/MacOS/Anki\n", True), ("/bin/other\n", False)])
def test_anki_process_detection(monkeypatch: pytest.MonkeyPatch, listing: str, running: bool) -> None:
    monkeypatch.setattr(dev_install.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=listing))
    assert dev_install.anki_is_running() is running


@pytest.mark.parametrize("listing", ["", "  \n"])
def test_empty_process_listing_is_indeterminate(monkeypatch: pytest.MonkeyPatch, listing: str) -> None:
    monkeypatch.setattr(dev_install.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(stdout=listing))
    with pytest.raises(RuntimeError, match="determine"):
        dev_install.anki_is_running()


@pytest.fixture
def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    base = tmp_path / "sandbox"
    base.mkdir()
    anki = tmp_path / "Anki"
    anki.write_text("")
    anki.chmod(0o700)
    events: list[object] = []
    process = SimpleNamespace(pid=1234, status=0)
    monkeypatch.setattr(dev_install.sys, "platform", "darwin")
    monkeypatch.setattr(dev_install, "ANKI", anki)
    monkeypatch.setattr(dev_install, "anki_is_running", lambda: False)
    monkeypatch.setattr(dev_install.tempfile, "mkdtemp", lambda **kwargs: str(base))
    monkeypatch.setattr(dev_install, "build_and_install", lambda path: events.append(("build", path)))
    monkeypatch.setattr(dev_install.dev_profile, "initialize_preferences", lambda path: None)
    monkeypatch.setattr(dev_install.dev_snapshot, "seed_snapshot", lambda path: False)
    monkeypatch.setattr(dev_install, "process_group_exists", lambda pid: False)

    def launch(path: str, args: list[str], env: dict[str, str], *, setsid: bool) -> int:
        events.append(("launch", path, args, env, setsid))
        return process.pid

    def wait(pid: int, options: int) -> tuple[int, int]:
        events.append("wait")
        return pid, process.status

    monkeypatch.setattr(dev_install.os, "posix_spawn", launch)
    monkeypatch.setattr(dev_install.os, "waitpid", wait)
    return SimpleNamespace(base=base, anki=anki, events=events, process=process)


def test_successful_session_launches_with_isolated_base_and_cleans_up(session: SimpleNamespace, capsys: pytest.CaptureFixture[str]) -> None:
    assert dev_install.run() == 0
    assert session.events[0] == ("build", session.base)
    _, path, args, env, isolated = session.events[1]
    assert path == str(session.anki)
    assert args == [str(session.anki), "--base", str(session.base), "--profile", "Mindful Dev", "--lang", "en"]
    assert env["ANKI_SINGLE_INSTANCE_KEY"].startswith("mindful-dev-")
    assert isolated is True
    assert session.events[2] == "wait"
    assert not session.base.exists()
    assert "discarded" in capsys.readouterr().out


def test_snapshot_mode_seeds_owned_profile(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    seeded = []

    def seed(path: Path) -> bool:
        seeded.append(path)
        return True

    monkeypatch.setattr(dev_install.dev_snapshot, "seed_snapshot", seed)
    assert dev_install.run() == 0
    assert seeded == [session.base / "Mindful Dev"]
    assert "Development data: snapshot" in capsys.readouterr().out


def test_empty_mode_never_accesses_snapshot(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fail(_path: Path) -> bool:
        msg = "snapshot must not be accessed"
        raise AssertionError(msg)

    monkeypatch.setattr(dev_install.dev_snapshot, "seed_snapshot", fail)
    assert dev_install.run(empty=True) == 0
    assert "Development data: empty" in capsys.readouterr().out


def test_invalid_snapshot_stops_before_launch(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_path: Path) -> bool:
        msg = "invalid snapshot"
        raise ValueError(msg)

    monkeypatch.setattr(dev_install.dev_snapshot, "seed_snapshot", fail)
    assert dev_install.run() == 1
    assert session.events == [("build", session.base)]
    assert session.base.exists()


def test_preferences_failure_stops_before_launch(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_path: Path) -> None:
        msg = "invalid preferences"
        raise RuntimeError(msg)

    monkeypatch.setattr(dev_install.dev_profile, "initialize_preferences", fail)
    assert dev_install.run() == 1
    assert session.events == [("build", session.base)]
    assert session.base.exists()


def test_running_anki_prevents_build_or_launch(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dev_install, "anki_is_running", lambda: True)
    assert dev_install.run() == 1
    assert session.events == []


def test_unavailable_process_listing_prevents_build_or_launch(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable() -> bool:
        raise subprocess.CalledProcessError(1, "ps")

    monkeypatch.setattr(dev_install, "anki_is_running", unavailable)
    assert dev_install.run() == 1
    assert session.events == []


def test_anki_started_during_build_prevents_launch(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    checks = iter([False, True])
    monkeypatch.setattr(dev_install, "anki_is_running", lambda: next(checks))
    assert dev_install.run() == 1
    assert session.events == [("build", session.base)]
    assert session.base.exists()


def test_missing_anki_prevents_build(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dev_install, "ANKI", session.anki.parent / "missing")
    assert dev_install.run() == 1
    assert session.events == []


def test_build_failure_prevents_launch_and_retains_base(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(_base: Path) -> None:
        raise subprocess.CalledProcessError(1, "build")

    monkeypatch.setattr(dev_install, "build_and_install", fail)
    assert dev_install.run() == 1
    assert session.events == []
    assert session.base.exists()


def test_launch_failure_retains_base(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fail(*args: object, **kwargs: object) -> None:
        message = "launch failed"
        raise OSError(message)

    monkeypatch.setattr(dev_install.os, "posix_spawn", fail)
    assert dev_install.run() == 1
    assert session.base.exists()
    assert "launch failed" in capsys.readouterr().err


def test_interrupted_session_retains_base(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def interrupted(_pid: int, _options: int) -> tuple[int, int]:
        raise KeyboardInterrupt

    monkeypatch.setattr(dev_install.os, "waitpid", interrupted)
    assert dev_install.run() == 1
    assert session.base.exists()
    assert str(session.base) in capsys.readouterr().err


@pytest.mark.parametrize("result", [1, -15])
def test_failed_anki_exit_retains_base(session: SimpleNamespace, result: int) -> None:
    session.process.status = result << 8 if result > 0 else -result
    assert dev_install.run() == 1
    assert session.base.exists()


@pytest.mark.parametrize("seeded", [False, True])
def test_uncertain_session_retains_base(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch, seeded: bool) -> None:
    monkeypatch.setattr(dev_install.dev_snapshot, "seed_snapshot", lambda path: seeded)
    monkeypatch.setattr(dev_install, "process_group_exists", lambda pid: True)
    assert dev_install.run() == 1
    assert session.base.exists()


def test_anki_remaining_after_launcher_exit_retains_base(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    checks = iter([False, False, True])
    monkeypatch.setattr(dev_install, "anki_is_running", lambda: next(checks))
    assert dev_install.run() == 1
    assert session.base.exists()


def test_failed_exit_check_retains_base(session: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(_pid: int) -> bool:
        raise PermissionError

    monkeypatch.setattr(dev_install, "process_group_exists", unavailable)
    assert dev_install.run() == 1
    assert session.base.exists()


def test_cleanup_rejects_replaced_directory(tmp_path: Path) -> None:
    base = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    base.mkdir()
    outside.mkdir()
    identity = base.stat().st_dev, base.stat().st_ino
    base.rmdir()
    base.symlink_to(outside, target_is_directory=True)

    with pytest.raises(RuntimeError, match="refusing cleanup"):
        dev_install.remove_owned_base(base, identity)
    assert outside.is_dir()
    assert base.is_symlink()
