import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    release_versions = importlib.import_module("scripts.release_versions")
finally:
    sys.path.pop(0)


def test_release_candidates_use_numerically_highest_stable_tag() -> None:
    refs = "aaa refs/tags/v0.9.9\nbbb refs/tags/v0.10.2\nccc refs/tags/v0.99.0-rc1\nddd refs/tags/v1.0.0^{}\neee refs/tags/unrelated\n"

    versions = release_versions.release_versions(refs)

    assert versions.baseline == (0, 10, 2)
    assert versions.patch == (0, 10, 3)
    assert versions.minor == (0, 11, 0)
    assert versions.major == (1, 0, 0)


def test_patch_release_does_not_depend_on_current_development_version() -> None:
    versions = release_versions.release_versions("abc refs/tags/v0.5.0\n")

    assert versions.patch == (0, 5, 1)


@pytest.mark.parametrize("refs", ["", "aaa refs/tags/v0.5.0-rc1\n", "aaa refs/tags/v01.2.3\n"])
def test_missing_stable_tag_is_rejected(refs: str) -> None:
    with pytest.raises(ValueError, match="no stable"):
        release_versions.release_versions(refs)
