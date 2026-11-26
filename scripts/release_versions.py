"""Calculate release candidates from an origin tag listing."""

import re
import sys
from dataclasses import dataclass

STABLE_TAG = re.compile(r"refs/tags/v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")


@dataclass(frozen=True)
class ReleaseVersions:
    """Release baseline and candidates."""

    baseline: tuple[int, int, int]
    patch: tuple[int, int, int]
    minor: tuple[int, int, int]
    major: tuple[int, int, int]


def release_versions(remote_refs: str) -> ReleaseVersions:
    """Return version candidates from the highest stable tag in a remote listing.

    Returns:
        The baseline and its three possible successors.

    Raises:
        ValueError: If no stable release tag is available.
    """
    versions: list[tuple[int, int, int]] = []
    for line in remote_refs.splitlines():
        try:
            _, ref = line.split()
        except ValueError:
            continue
        match = STABLE_TAG.fullmatch(ref)
        if match:
            major, minor, patch = map(int, match.groups())
            versions.append((major, minor, patch))
    if not versions:
        msg = "origin has no stable vX.Y.Z release tags"
        raise ValueError(msg)

    major, minor, patch = max(versions)
    return ReleaseVersions(
        baseline=(major, minor, patch),
        patch=(major, minor, patch + 1),
        minor=(major, minor + 1, 0),
        major=(major + 1, 0, 0),
    )


def format_version(version: tuple[int, int, int]) -> str:
    """Format a stable version.

    Returns:
        The dotted version string.
    """
    return ".".join(map(str, version))


def main() -> int:
    """Print the baseline and release candidates from stdin.

    Returns:
        Zero on success, otherwise one.
    """
    try:
        versions = release_versions(sys.stdin.read())
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}.\n")
        return 1
    sys.stdout.write(f"baseline {format_version(versions.baseline)}\n")
    for name in ("patch", "minor", "major"):
        version = getattr(versions, name)
        major, minor, patch = version
        sys.stdout.write(f"{name} {format_version(version)} {major}.{minor}.{patch + 1}.dev0\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
