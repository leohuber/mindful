"""Build and run Mindful in a disposable macOS Anki base."""

import argparse
import os
import runpy
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from secrets import token_hex
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_addon.py"
ARCHIVE = ROOT / "dist" / "mindful.ankiaddon"
ANKI = Path("/Applications/Anki.app/Contents/MacOS/Anki")


def anki_is_running() -> bool:
    """Inspect macOS processes, failing closed if the listing is unavailable.

    Returns:
        Whether an Anki process is visible.

    Raises:
        RuntimeError: The process listing is empty.
    """
    result = subprocess.run(
        ["/bin/ps", "-axo", "comm="],
        capture_output=True,
        check=True,
        text=True,
    )
    commands = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not commands:
        msg = "Could not determine whether Anki is running."
        raise RuntimeError(msg)
    return any(command.strip().rsplit("/", 1)[-1].casefold() == "anki" for command in commands)


def require_anki_closed() -> None:
    """Refuse to start when an Anki process is visible.

    Raises:
        RuntimeError: Anki is running.
    """
    if anki_is_running():
        msg = "Anki is running. Quit Anki before starting the development session."
        raise RuntimeError(msg)


def build_and_install(base: Path) -> None:
    """Build the archive and extract its safe entries into the temporary base.

    Raises:
        ValueError: The archive contains an unsafe entry.
    """
    runpy.run_path(str(BUILDER), run_name="__main__")
    target = base / "addons21" / "mindful"
    target.mkdir(parents=True)
    with ZipFile(ARCHIVE) as archive:
        seen: set[str] = set()
        for info in archive.infolist():
            name = info.filename
            parts = name.rstrip("/").split("/")
            mode = info.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if (
                not name
                or "\\" in name
                or PurePosixPath(name).is_absolute()
                or any(part in {"", ".", ".."} for part in parts)
                or kind not in {0, stat.S_IFREG, stat.S_IFDIR}
                or ((kind == stat.S_IFDIR) != info.is_dir() and kind != 0)
                or name.rstrip("/").casefold() in seen
            ):
                msg = f"Unsafe or duplicate archive entry: {name!r}"
                raise ValueError(msg)
            seen.add(name.rstrip("/").casefold())
        archive.extractall(target)


def process_group_exists(pid: int) -> bool:
    """Check whether any process remains in the launched session's group.

    Returns:
        Whether the process group still exists.
    """
    try:
        os.killpg(pid, 0)
    except ProcessLookupError:
        return False
    return True


def remove_owned_base(base: Path, identity: tuple[int, int]) -> None:
    """Remove only the temporary directory created for this invocation.

    Raises:
        RuntimeError: The directory was replaced.
    """
    current = base.lstat()
    if not stat.S_ISDIR(current.st_mode) or (current.st_dev, current.st_ino) != identity:
        msg = f"Temporary base changed; refusing cleanup: {base}"
        raise RuntimeError(msg)
    shutil.rmtree(base)


def check_prerequisites() -> None:
    """Check the platform, executable, and Anki process state.

    Raises:
        RuntimeError: The platform or executable is unsupported.
    """
    if sys.platform != "darwin":
        msg = "The development command supports macOS only."
        raise RuntimeError(msg)
    if not ANKI.is_file() or not os.access(ANKI, os.X_OK):
        msg = f"Anki executable not found or not executable: {ANKI}"
        raise RuntimeError(msg)
    require_anki_closed()


def launch_anki(base: Path) -> None:
    """Launch Anki and confirm its entire session has ended.

    Raises:
        RuntimeError: Anki fails or its session has not fully exited.
    """
    require_anki_closed()
    env = os.environ.copy()
    env["ANKI_SINGLE_INSTANCE_KEY"] = f"mindful-dev-{token_hex(16)}"
    pid = os.posix_spawn(str(ANKI), [str(ANKI), "--base", str(base)], env, setsid=True)
    _, status = os.waitpid(pid, 0)
    result = os.waitstatus_to_exitcode(status)
    if result != 0:
        msg = f"Anki exited with status {result}."
        raise RuntimeError(msg)
    if process_group_exists(pid) or anki_is_running():
        msg = "Cannot confirm that the Anki session has fully exited."
        raise RuntimeError(msg)


def run() -> int:
    """Build and launch an isolated Anki session.

    Returns:
        Zero on success, otherwise one.
    """
    base: Path | None = None
    try:
        check_prerequisites()
        base = Path(tempfile.mkdtemp(prefix="mindful-dev-")).resolve()
        created = base.stat()
        identity = (created.st_dev, created.st_ino)
        sys.stdout.write(f"Temporary Anki base: {base}\n")
        sys.stdout.write("This base is disposable. Do not enable sync; it can affect remote data.\n")
        sys.stdout.flush()
        build_and_install(base)
        sys.stdout.flush()
        launch_anki(base)
        remove_owned_base(base, identity)
        sys.stdout.write("Temporary Anki base removed; its test data was discarded.\n")
    except (BadZipFile, KeyboardInterrupt, OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
        sys.stderr.write(f"Development session failed: {exc or 'interrupted'}\n")
        if base is not None:
            sys.stderr.write(f"Temporary base retained for inspection: {base}\n")
        return 1
    return 0


def main() -> None:
    """Parse command-line arguments and run the development session."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    sys.exit(run())


if __name__ == "__main__":
    main()
