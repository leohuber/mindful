"""Shared safeguards for local Anki development commands."""

import subprocess
import sys


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
    return any(command.rsplit("/", 1)[-1].casefold() == "anki" for command in commands)


def require_macos() -> None:
    """Reject unsupported systems.

    Raises:
        RuntimeError: The current system is not macOS.
    """
    if sys.platform != "darwin":
        msg = "The development command supports macOS only."
        raise RuntimeError(msg)


def require_anki_closed() -> None:
    """Reject a running Anki instance.

    Raises:
        RuntimeError: Anki is running.
    """
    if anki_is_running():
        msg = "Anki is running. Quit Anki before starting the development session."
        raise RuntimeError(msg)
